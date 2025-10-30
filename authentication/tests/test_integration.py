"""
Integration tests for authentication app.

Tests the complete authentication flow including:
- User registration and email verification
- Login and token management
- Password reset flow
- Session management
- Security features
"""

import pytest
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.core import mail
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, Mock
import json
from datetime import timedelta
from django.utils import timezone

from authentication.models import (
    UserSession, TokenBlacklist, EmailVerificationToken,
    PasswordResetToken, AuditLog
)
from authentication.services import (
    AuthenticationService, EmailVerificationService,
    PasswordService, SessionService, TokenService
)
from .factories import (
    UserFactory, UserSessionFactory, EmailVerificationTokenFactory,
    PasswordResetTokenFactory
)

User = get_user_model()


class AuthenticationFlowIntegrationTest(APITestCase):
    """Test complete authentication flows."""

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('authentication:register')
        self.login_url = reverse('authentication:login')
        self.logout_url = reverse('authentication:logout')
        self.refresh_url = reverse('authentication:refresh')

    def test_complete_registration_flow(self):
        """Test complete user registration and email verification flow."""
        # Step 1: Register user
        registration_data = {
            'email': 'testuser@example.com',
            'username': 'testuser',
            'password': 'SecurePassword123!',
            'first_name': 'Test',
            'last_name': 'User'
        }

        response = self.client.post(self.register_url, registration_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify user created but not verified
        user = User.objects.get(email='testuser@example.com')
        self.assertFalse(user.email_verified)

        # Verify email sent
        self.assertEqual(len(mail.outbox), 1)

        # Step 2: Verify email
        token = EmailVerificationToken.objects.get(user=user)
        verify_url = reverse('authentication:verify_email')

        verify_response = self.client.post(verify_url, {
            'token': token.token,
            'email': user.email
        })
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)

        # Verify user is now email verified
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_complete_login_logout_flow(self):
        """Test complete login and logout flow."""
        # Create verified user
        user = UserFactory(email_verified=True)

        # Step 1: Login
        login_data = {
            'email_or_username': user.email,
            'password': 'testpass123'
        }

        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify tokens returned
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # Verify session created
        self.assertTrue(UserSession.objects.filter(
            user=user, is_active=True).exists())

        # Step 2: Use access token for authenticated request
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Step 3: Logout
        logout_response = self.client.post(self.logout_url)
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        # Verify session terminated
        self.assertFalse(UserSession.objects.filter(
            user=user, is_active=True).exists())

    def test_password_reset_flow(self):
        """Test complete password reset flow."""
        user = UserFactory(email_verified=True)

        # Step 1: Request password reset
        reset_request_url = reverse('authentication:password_reset_request')
        response = self.client.post(reset_request_url, {
            'email': user.email
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify email sent
        self.assertEqual(len(mail.outbox), 1)

        # Step 2: Use reset token
        reset_token = PasswordResetToken.objects.get(user=user)
        reset_confirm_url = reverse('authentication:password_reset_confirm')

        new_password = 'NewSecurePassword123!'  # nosec - test password
        response = self.client.post(reset_confirm_url, {
            'token': reset_token.token,
            'password': new_password
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Step 3: Verify can login with new password
        login_data = {
            'email_or_username': user.email,
            'password': new_password
        }

        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SecurityIntegrationTest(APITestCase):
    """Test security features integration."""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory(email_verified=True)

    def test_account_lockout_flow(self):
        """Test account lockout after failed login attempts."""
        login_url = reverse('authentication:login')

        # Make multiple failed login attempts
        for i in range(6):  # Assuming 5 is the limit
            response = self.client.post(login_url, {
                'email_or_username': self.user.email,
                'password': 'wrongpassword'
            })

            if i < 5:
                self.assertEqual(response.status_code,
                                 status.HTTP_400_BAD_REQUEST)
            else:
                # Account should be locked
                self.assertEqual(response.status_code, status.HTTP_423_LOCKED)

        # Verify user account is locked
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_account_locked())

    def test_token_blacklisting_on_logout(self):
        """Test that tokens are properly blacklisted on logout."""
        # Login to get tokens
        login_url = reverse('authentication:login')
        response = self.client.post(login_url, {
            'email_or_username': self.user.email,
            'password': 'testpass123'
        })

        refresh_token = response.data['refresh']

        # Logout
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        logout_url = reverse('authentication:logout')
        self.client.post(logout_url)

        # Verify refresh token is blacklisted
        self.assertTrue(
            TokenBlacklist.objects.filter(
                user=self.user,
                token_type='refresh'
            ).exists()
        )

    def test_audit_logging(self):
        """Test that security events are properly logged."""
        login_url = reverse('authentication:login')

        # Successful login
        response = self.client.post(login_url, {
            'email_or_username': self.user.email,
            'password': 'testpass123'
        })

        # Verify audit log entry
        self.assertTrue(
            AuditLog.objects.filter(
                user=self.user,
                event_type='login_success'
            ).exists()
        )

        # Failed login
        response = self.client.post(login_url, {
            'email_or_username': self.user.email,
            'password': 'wrongpassword'
        })

        # Verify audit log entry
        self.assertTrue(
            AuditLog.objects.filter(
                user=self.user,
                event_type='login_failed'
            ).exists()
        )


class SessionManagementIntegrationTest(APITestCase):
    """Test session management integration."""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory(email_verified=True)

        # Login to get access token
        login_url = reverse('authentication:login')
        response = self.client.post(login_url, {
            'email_or_username': self.user.email,
            'password': 'testpass123'
        })

        self.access_token = response.data['access']
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_list_user_sessions(self):
        """Test listing user sessions."""
        # Create additional sessions
        UserSessionFactory(user=self.user, is_active=True)
        UserSessionFactory(user=self.user, is_active=True)

        sessions_url = reverse('authentication:user_sessions')
        response = self.client.get(sessions_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # At least current session
        self.assertGreaterEqual(len(response.data), 1)

    def test_terminate_specific_session(self):
        """Test terminating a specific session."""
        # Create another session
        session = UserSessionFactory(user=self.user, is_active=True)

        terminate_url = reverse(
            'authentication:terminate_session', args=[session.id])
        response = self.client.delete(terminate_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify session is terminated
        session.refresh_from_db()
        self.assertFalse(session.is_active)

    def test_terminate_all_sessions(self):
        """Test terminating all user sessions."""
        # Create additional sessions
        UserSessionFactory(user=self.user, is_active=True)
        UserSessionFactory(user=self.user, is_active=True)

        terminate_all_url = reverse('authentication:terminate_all_sessions')
        response = self.client.post(terminate_all_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify all sessions are terminated
        active_sessions = UserSession.objects.filter(
            user=self.user, is_active=True)
        self.assertEqual(active_sessions.count(), 0)


class EmailVerificationIntegrationTest(APITestCase):
    """Test email verification integration."""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory(email_verified=False)

    def test_resend_verification_email(self):
        """Test resending verification email."""
        resend_url = reverse('authentication:resend_verification')

        response = self.client.post(resend_url, {
            'email': self.user.email
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_change_flow(self):
        """Test complete email change flow."""
        # First verify the user
        self.user.email_verified = True
        self.user.save()

        # Login
        login_url = reverse('authentication:login')
        response = self.client.post(login_url, {
            'email_or_username': self.user.email,
            'password': 'testpass123'
        })

        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Request email change
        change_email_url = reverse('authentication:change_email_request')
        new_email = 'newemail@example.com'

        response = self.client.post(change_email_url, {
            'new_email': new_email
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        # Confirm email change
        token = EmailVerificationToken.objects.get(email=new_email)
        confirm_url = reverse('authentication:confirm_email_change')

        response = self.client.post(confirm_url, {
            'token': token.token
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify email changed
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, new_email)


@pytest.mark.django_db
class HealthCheckIntegrationTest(TestCase):
    """Test health check integration."""

    def setUp(self):
        self.client = APIClient()

    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        health_url = reverse('authentication:health_check')
        response = self.client.get(health_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertIn('timestamp', response.data)
        self.assertIn('checks', response.data)

    @patch('authentication.view_modules.health.connection')
    def test_health_check_database_failure(self, mock_connection):
        """Test health check when database is down."""
        mock_connection.cursor().execute.side_effect = Exception("Database error")

        health_url = reverse('authentication:health_check')
        response = self.client.get(health_url)

        self.assertEqual(response.status_code,
                         status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data['status'], 'unhealthy')


class PerformanceIntegrationTest(APITestCase):
    """Test performance aspects of authentication."""

    def setUp(self):
        self.client = APIClient()

    def test_concurrent_login_attempts(self):
        """Test handling of concurrent login attempts."""
        user = UserFactory(email_verified=True)
        login_url = reverse('authentication:login')

        # Simulate concurrent requests
        login_data = {
            'email_or_username': user.email,
            'password': 'testpass123'
        }

        responses = []
        for _ in range(5):
            response = self.client.post(login_url, login_data)
            responses.append(response)

        # All should succeed
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_token_refresh_performance(self):
        """Test token refresh performance."""
        user = UserFactory(email_verified=True)

        # Login to get tokens
        login_url = reverse('authentication:login')
        response = self.client.post(login_url, {
            'email_or_username': user.email,
            'password': 'testpass123'
        })

        refresh_token = response.data['refresh']

        # Multiple refresh attempts
        refresh_url = reverse('authentication:refresh')

        for _ in range(10):
            # Set refresh token in cookie
            self.client.cookies['refresh_token'] = refresh_token

            response = self.client.post(refresh_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Update refresh token for next iteration
            refresh_token = response.data['refresh']
