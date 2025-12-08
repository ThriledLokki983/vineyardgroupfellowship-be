"""
Tests for mobile authentication functionality.

This module tests the mobile client detection and dual-mode authentication
response behavior for web and mobile clients.
"""

import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from authentication.utils.mobile import (
    is_mobile_client,
    get_client_type,
    should_use_cookie_auth
)

User = get_user_model()


class MobileClientDetectionTests(TestCase):
    """Test mobile client detection utilities."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_mobile_client_with_header(self):
        """Test mobile client detection via X-Client-Type header."""
        request = self.factory.get('/', HTTP_X_CLIENT_TYPE='mobile')
        self.assertTrue(is_mobile_client(request))
        self.assertEqual(get_client_type(request), 'mobile')
        self.assertFalse(should_use_cookie_auth(request))

    def test_web_client_without_header(self):
        """Test web client detection when no mobile indicators present."""
        request = self.factory.get('/')
        self.assertFalse(is_mobile_client(request))
        self.assertEqual(get_client_type(request), 'web')
        self.assertTrue(should_use_cookie_auth(request))

    def test_mobile_client_with_user_agent(self):
        """Test mobile client detection via User-Agent."""
        request = self.factory.get('/', HTTP_USER_AGENT='VineyardGF/1.0.0 React-Native')
        self.assertTrue(is_mobile_client(request))

    def test_mobile_client_with_expo_user_agent(self):
        """Test mobile client detection with Expo framework."""
        request = self.factory.get('/', HTTP_USER_AGENT='Expo/1.0.0')
        self.assertTrue(is_mobile_client(request))


@pytest.mark.django_db
class MobileLoginTests(TestCase):
    """Test mobile login flow."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPassword123!',  # nosec - test credential
            email_verified=True,
            is_active=True
        )

    def test_mobile_login_returns_refresh_token_in_body(self):
        """Mobile clients should receive refresh token in response body."""
        response = self.client.post(
            '/api/v1/auth/login/',
            {
                'email_or_username': 'test@example.com',
                'password': 'TestPassword123!'  # nosec - test credential
            },
            HTTP_X_CLIENT_TYPE='mobile'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        # Mobile clients should NOT receive cookie
        self.assertNotIn('refresh_token', response.cookies)

    def test_web_login_sets_cookie(self):
        """Web clients should receive refresh token in httpOnly cookie."""
        response = self.client.post(
            '/api/v1/auth/login/',
            {
                'email_or_username': 'test@example.com',
                'password': 'TestPassword123!'  # nosec - test credential
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)
        # Web clients should NOT get refresh token in body
        self.assertNotIn('refresh_token', response.data)
        # Web clients should get refresh token in cookie
        self.assertIn('refresh_token', response.cookies)


@pytest.mark.django_db
class MobileTokenRefreshTests(TestCase):
    """Test mobile token refresh flow."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPassword123!',  # nosec - test credential
            email_verified=True,
            is_active=True
        )

        # Login to get tokens
        response = self.client.post(
            '/api/v1/auth/login/',
            {
                'email_or_username': 'test@example.com',
                'password': 'TestPassword123!'  # nosec - test credential
            },
            HTTP_X_CLIENT_TYPE='mobile'
        )
        self.access_token = response.data['access_token']
        self.refresh_token = response.data['refresh_token']

    def test_mobile_refresh_with_header(self):
        """Mobile clients can refresh using X-Refresh-Token header."""
        response = self.client.post(
            '/api/v1/auth/token/refresh/',
            HTTP_X_REFRESH_TOKEN=self.refresh_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        # Mobile should receive new refresh token (rotation)
        self.assertIn('refresh', response.data)

    def test_mobile_refresh_without_header_fails(self):
        """Mobile refresh should fail without X-Refresh-Token header."""
        response = self.client.post('/api/v1/auth/token/refresh/')

        self.assertEqual(response.status_code, 401)


@pytest.mark.django_db
class MobileLogoutTests(TestCase):
    """Test mobile logout flow."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPassword123!',  # nosec - test credential
            email_verified=True,
            is_active=True
        )

        # Login to get tokens
        response = self.client.post(
            '/api/v1/auth/login/',
            {
                'email_or_username': 'test@example.com',
                'password': 'TestPassword123!'  # nosec - test credential
            },
            HTTP_X_CLIENT_TYPE='mobile'
        )
        self.access_token = response.data['access_token']
        self.refresh_token = response.data['refresh_token']

    def test_mobile_logout_with_header(self):
        """Mobile clients can logout using X-Refresh-Token header."""
        response = self.client.post(
            '/api/v1/auth/logout/',
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}',
            HTTP_X_REFRESH_TOKEN=self.refresh_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)


class CSRFExemptionTests(TestCase):
    """Test CSRF exemption for mobile clients."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_mobile_client_skips_csrf(self):
        """Mobile clients should skip CSRF validation."""
        from core.middleware.csrf import EnhancedCSRFMiddleware
        
        middleware = EnhancedCSRFMiddleware(lambda r: None)
        request = self.factory.post('/', HTTP_X_CLIENT_TYPE='mobile')
        
        # Mobile requests should skip CSRF
        self.assertTrue(middleware._should_skip_csrf(request))

    def test_web_client_requires_csrf(self):
        """Web clients should require CSRF validation."""
        from core.middleware.csrf import EnhancedCSRFMiddleware
        
        middleware = EnhancedCSRFMiddleware(lambda r: None)
        request = self.factory.post('/')
        
        # Web requests should not skip CSRF (unless on exempt paths)
        result = middleware._should_skip_csrf(request)
        # Only skip if on exempt path, not because of client type
        self.assertFalse(result or request.path.startswith('/admin/'))
