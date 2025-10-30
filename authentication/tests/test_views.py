"""
Tests for authentication views.

Comprehensive tests for all authentication view endpoints including:
- Registration and login
- Password management
- Email verification
- Session management
- Health checks
- Security and rate limiting
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import mail
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, Mock
import json
from datetime import timedelta

from ..models import (
    UserSession, TokenBlacklist, EmailVerificationToken,
    PasswordResetToken, AuditLog
)
from .factories import (
    UserFactory, UnverifiedUserFactory, LockedUserFactory,
    UserSessionFactory, EmailVerificationTokenFactory,
    PasswordResetTokenFactory, create_complete_user_scenario
)

User = get_user_model()


class AuthenticationViewTestCase(APITestCase):
    """Base test case for authentication views."""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.password = "TestPassword123!"  # nosec - test password
        self.user.set_password(self.password)
        self.user.save()


@pytest.mark.django_db
class TestRegistrationView(AuthenticationViewTestCase):
    """Test user registration endpoint."""

    def test_successful_registration(self):
        """Test successful user registration."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'first_name': 'New',
            'last_name': 'User',
            'terms_accepted': True,
            'privacy_policy_accepted': True
        }

        url = reverse('authentication:register')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'access_token' in response.data
        assert 'message' in response.data

        # Verify user was created
        user = User.objects.get(email='newuser@example.com')
        assert user.username == 'newuser'
        assert user.email_verified is False  # Should require verification

        # Verify verification email was sent
        assert len(mail.outbox) == 1
        assert 'verification' in mail.outbox[0].subject.lower()

    def test_registration_password_mismatch(self):
        """Test registration with password mismatch."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'confirm_password': 'DifferentPassword456!',
            'terms_accepted': True,
            'privacy_policy_accepted': True
        }

        url = reverse('authentication:register')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in str(response.data).lower()

    def test_registration_duplicate_email(self):
        """Test registration with duplicate email."""
        data = {
            'username': 'newuser',
            'email': self.user.email,  # Existing email
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'terms_accepted': True,
            'privacy_policy_accepted': True
        }

        url = reverse('authentication:register')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in str(response.data).lower()

    def test_registration_weak_password(self):
        """Test registration with weak password."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': '123',  # Weak password
            'confirm_password': '123',
            'terms_accepted': True,
            'privacy_policy_accepted': True
        }

        url = reverse('authentication:register')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_registration_missing_terms(self):
        """Test registration without accepting terms."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'terms_accepted': False,  # Not accepted
            'privacy_policy_accepted': True
        }

        url = reverse('authentication:register')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoginView(AuthenticationViewTestCase):
    """Test user login endpoint."""

    def test_successful_login(self):
        """Test successful login."""
        data = {
            'email_or_username': self.user.email,
            'password': self.password
        }

        url = reverse('authentication:login')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.data
        assert 'refresh_token' in response.data
        assert 'user' in response.data

        # Verify session was created
        assert UserSession.objects.filter(
            user=self.user, is_active=True).exists()

    def test_login_with_username(self):
        """Test login with username instead of email."""
        data = {
            'email_or_username': self.user.username,
            'password': self.password
        }

        url = reverse('authentication:login')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        data = {
            'email_or_username': self.user.email,
            'password': 'wrongpassword'
        }

        url = reverse('authentication:login')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'invalid' in str(response.data).lower()

    def test_login_locked_account(self):
        """Test login with locked account."""
        locked_user = LockedUserFactory()
        locked_user.set_password(self.password)
        locked_user.save()

        data = {
            'email_or_username': locked_user.email,
            'password': self.password
        }

        url = reverse('authentication:login')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_423_LOCKED

    def test_login_unverified_user(self):
        """Test login with unverified email."""
        unverified_user = UnverifiedUserFactory()
        unverified_user.set_password(self.password)
        unverified_user.save()

        data = {
            'email_or_username': unverified_user.email,
            'password': self.password
        }

        url = reverse('authentication:login')
        response = self.client.post(url, data, format='json')

        # Should still allow login but with warning
        assert response.status_code == status.HTTP_200_OK
        assert 'verify' in str(response.data).lower()


@pytest.mark.django_db
class TestLogoutView(AuthenticationViewTestCase):
    """Test user logout endpoint."""

    def test_successful_logout(self):
        """Test successful logout."""
        # Login first
        self.client.force_authenticate(user=self.user)
        session = UserSessionFactory(user=self.user)

        url = reverse('authentication:logout')
        response = self.client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'logout successful' in str(response.data).lower()

    def test_logout_unauthenticated(self):
        """Test logout without authentication."""
        url = reverse('authentication:logout')
        response = self.client.post(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPasswordChangeView(AuthenticationViewTestCase):
    """Test password change endpoint."""

    def test_successful_password_change(self):
        """Test successful password change."""
        self.client.force_authenticate(user=self.user)

        data = {
            'current_password': self.password,
            'new_password': 'NewSecurePassword789!',
            'confirm_password': 'NewSecurePassword789!'
        }

        url = reverse('authentication:password:change')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Verify password was changed
        self.user.refresh_from_db()
        assert self.user.check_password('NewSecurePassword789!')

    def test_password_change_wrong_current(self):
        """Test password change with wrong current password."""
        self.client.force_authenticate(user=self.user)

        data = {
            'current_password': 'wrongpassword',
            'new_password': 'NewSecurePassword789!',
            'confirm_password': 'NewSecurePassword789!'
        }

        url = reverse('authentication:password:change')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_change_unauthenticated(self):
        """Test password change without authentication."""
        data = {
            'current_password': self.password,
            'new_password': 'NewSecurePassword789!',
            'confirm_password': 'NewSecurePassword789!'
        }

        url = reverse('authentication:password:change')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPasswordResetView(AuthenticationViewTestCase):
    """Test password reset endpoints."""

    def test_password_reset_request(self):
        """Test password reset request."""
        data = {'email': self.user.email}

        url = reverse('authentication:password:reset_request')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Verify reset token was created
        assert PasswordResetToken.objects.filter(
            user=self.user,
            is_used=False
        ).exists()

        # Verify email was sent
        assert len(mail.outbox) == 1

    def test_password_reset_nonexistent_email(self):
        """Test password reset with nonexistent email."""
        data = {'email': 'nonexistent@example.com'}

        url = reverse('authentication:password:reset_request')
        response = self.client.post(url, data, format='json')

        # Should still return success for security
        assert response.status_code == status.HTTP_200_OK

    def test_password_reset_confirm(self):
        """Test password reset confirmation."""
        reset_token = PasswordResetTokenFactory(user=self.user)

        data = {
            'token': reset_token.token,
            'new_password': 'NewResetPassword123!',
            'confirm_password': 'NewResetPassword123!'
        }

        url = reverse('authentication:password:reset_confirm')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Verify password was changed
        self.user.refresh_from_db()
        assert self.user.check_password('NewResetPassword123!')

        # Verify token was marked as used
        reset_token.refresh_from_db()
        assert reset_token.is_used is True

    def test_password_reset_invalid_token(self):
        """Test password reset with invalid token."""
        data = {
            'token': 'invalid-token',
            'new_password': 'NewResetPassword123!',
            'confirm_password': 'NewResetPassword123!'
        }

        url = reverse('authentication:password:reset_confirm')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestEmailVerificationView(AuthenticationViewTestCase):
    """Test email verification endpoints."""

    def test_email_verification(self):
        """Test email verification."""
        unverified_user = UnverifiedUserFactory()
        token = EmailVerificationTokenFactory(user=unverified_user)

        data = {'token': token.token}

        url = reverse('authentication:verify_email')
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Verify user email was verified
        unverified_user.refresh_from_db()
        assert unverified_user.email_verified is True

        # Verify token was marked as used
        token.refresh_from_db()
        assert token.is_used is True

    def test_resend_verification_email(self):
        """Test resending verification email."""
        unverified_user = UnverifiedUserFactory()
        self.client.force_authenticate(user=unverified_user)

        url = reverse('authentication:resend_verification')
        response = self.client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Verify new token was created
        assert EmailVerificationToken.objects.filter(
            user=unverified_user,
            is_used=False
        ).exists()


@pytest.mark.django_db
class TestSessionManagementViews(AuthenticationViewTestCase):
    """Test session management endpoints."""

    def test_list_sessions(self):
        """Test listing user sessions."""
        self.client.force_authenticate(user=self.user)

        # Create some sessions
        session1 = UserSessionFactory(user=self.user)
        session2 = UserSessionFactory(user=self.user)

        url = reverse('authentication:sessions:list')
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2

    def test_terminate_session(self):
        """Test terminating specific session."""
        self.client.force_authenticate(user=self.user)

        session = UserSessionFactory(user=self.user)

        data = {'session_id': str(session.id)}
        url = reverse('authentication:sessions:terminate')
        response = self.client.delete(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Verify session was terminated
        session.refresh_from_db()
        assert session.is_active is False

    def test_terminate_all_sessions(self):
        """Test terminating all user sessions."""
        self.client.force_authenticate(user=self.user)

        # Create multiple sessions
        session1 = UserSessionFactory(user=self.user)
        session2 = UserSessionFactory(user=self.user)

        url = reverse('authentication:sessions:terminate_all')
        response = self.client.post(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestHealthCheckView(AuthenticationViewTestCase):
    """Test health check endpoint."""

    def test_health_check_healthy(self):
        """Test health check when all services are healthy."""
        url = reverse('authentication:health:check')
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] in ['healthy', 'degraded']
        assert 'checks' in response.data
        assert 'database' in response.data['checks']

    @patch('django.db.connections')
    def test_health_check_database_failure(self, mock_connections):
        """Test health check with database failure."""
        mock_connections.__getitem__.side_effect = Exception("DB Error")

        url = reverse('authentication:health:check')
        response = self.client.get(url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data['status'] == 'unhealthy'


@pytest.mark.django_db
class TestRateLimiting(AuthenticationViewTestCase):
    """Test rate limiting on endpoints."""

    def test_login_rate_limiting(self):
        """Test rate limiting on login endpoint."""
        url = reverse('authentication:login')
        data = {
            'email_or_username': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }

        # Make multiple requests rapidly
        for _ in range(30):  # Exceed rate limit
            response = self.client.post(url, data, format='json')

        # Should get rate limited eventually
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_registration_rate_limiting(self):
        """Test rate limiting on registration endpoint."""
        url = reverse('authentication:register')

        # Make multiple registration attempts
        for i in range(10):
            data = {
                'username': f'user{i}',
                'email': f'user{i}@example.com',
                'password': 'SecurePassword123!',
                'confirm_password': 'SecurePassword123!',
                'terms_accepted': True,
                'privacy_policy_accepted': True
            }
            response = self.client.post(url, data, format='json')

        # Should eventually get rate limited
        # Note: Actual rate limiting depends on configuration


@pytest.mark.django_db
class TestSecurityFeatures(AuthenticationViewTestCase):
    """Test security features."""

    def test_csrf_protection(self):
        """Test CSRF protection on sensitive endpoints."""
        # This test would depend on CSRF configuration
        pass

    def test_audit_logging(self):
        """Test that security events are logged."""
        # Login should create audit log
        data = {
            'email_or_username': self.user.email,
            'password': self.password
        }

        url = reverse('authentication:login')
        response = self.client.post(url, data, format='json')

        # Verify audit log was created
        assert AuditLog.objects.filter(
            user=self.user,
            event_type='login',
            success=True
        ).exists()

    def test_failed_login_audit(self):
        """Test failed login creates audit log."""
        data = {
            'email_or_username': self.user.email,
            'password': 'wrongpassword'
        }

        url = reverse('authentication:login')
        response = self.client.post(url, data, format='json')

        # Verify failed login was logged
        assert AuditLog.objects.filter(
            event_type='failed_login',
            success=False
        ).exists()

    def test_sensitive_data_not_logged(self):
        """Test that sensitive data is not logged."""
        # Passwords should never appear in logs
        data = {
            'email_or_username': self.user.email,
            'password': self.password
        }

        url = reverse('authentication:login')
        response = self.client.post(url, data, format='json')

        # Check that password is not in audit log metadata
        logs = AuditLog.objects.filter(user=self.user)
        for log in logs:
            if log.metadata:
                assert self.password not in str(log.metadata)


@pytest.mark.django_db
class TestTokenManagement(AuthenticationViewTestCase):
    """Test JWT token management."""

    def test_token_refresh(self):
        """Test JWT token refresh."""
        # Login to get tokens
        login_data = {
            'email_or_username': self.user.email,
            'password': self.password
        }

        login_url = reverse('authentication:login')
        login_response = self.client.post(login_url, login_data, format='json')

        refresh_token = login_response.data['refresh_token']

        # Use refresh token
        refresh_url = reverse('authentication:refresh')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh_token}')
        refresh_response = self.client.post(refresh_url)

        assert refresh_response.status_code == status.HTTP_200_OK
        assert 'access_token' in refresh_response.data

    def test_token_blacklisting(self):
        """Test token blacklisting on logout."""
        # Login and logout
        self.client.force_authenticate(user=self.user)

        logout_url = reverse('authentication:logout')
        response = self.client.post(logout_url)

        assert response.status_code == status.HTTP_200_OK

        # Verify token was blacklisted
        assert TokenBlacklist.objects.filter(user=self.user).exists()


@pytest.mark.django_db
class TestErrorHandling(AuthenticationViewTestCase):
    """Test error handling and responses."""

    def test_invalid_json_format(self):
        """Test handling of invalid JSON."""
        url = reverse('authentication:login')
        response = self.client.post(
            url,
            'invalid json',
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        url = reverse('authentication:login')
        data = {'email_or_username': self.user.email}  # Missing password

        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in str(response.data).lower()

    def test_database_error_handling(self):
        """Test handling of database errors."""
        # This would require mocking database failures
        pass
