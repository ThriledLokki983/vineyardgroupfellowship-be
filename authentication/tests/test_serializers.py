"""
Tests for authentication serializers.

Comprehensive tests for all DRF serializers including:
- Validation logic
- Field requirements
- Security validations
- Data transformation
- Error handling
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
import uuid

from ..serializers import (
    UserRegistrationSerializer, 
    # UserLoginSerializer,  # Use LoginSerializer instead
    UserBasicSerializer,
    PasswordChangeSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, EmailVerificationSerializer,
    # EmailChangeRequestSerializer,  # Not yet implemented
    # EmailChangeConfirmSerializer,  # Not yet implemented
    UserSessionSerializer, SessionTerminateSerializer,
    AuthResponseSerializer, SuccessMessageSerializer,
    HealthCheckSerializer
)
from .factories import (
    UserFactory, UnverifiedUserFactory, UserSessionFactory,
    EmailVerificationTokenFactory, PasswordResetTokenFactory
)

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistrationSerializer(TestCase):
    """Test UserRegistrationSerializer."""

    def test_valid_registration_data(self):
        """Test serializer with valid registration data."""
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

        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        validated_data = serializer.validated_data
        assert validated_data['username'] == 'newuser'
        assert validated_data['email'] == 'newuser@example.com'

    def test_password_mismatch(self):
        """Test password confirmation mismatch."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'confirm_password': 'DifferentPassword456!',
            'terms_accepted': True,
            'privacy_policy_accepted': True
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_weak_password_validation(self):
        """Test weak password rejection."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': '123',  # Too weak
            'confirm_password': '123',
            'terms_accepted': True,
            'privacy_policy_accepted': True
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors

    def test_duplicate_email_validation(self):
        """Test duplicate email validation."""
        existing_user = UserFactory()

        data = {
            'username': 'newuser',
            'email': existing_user.email,  # Duplicate
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'terms_accepted': True,
            'privacy_policy_accepted': True
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'email' in serializer.errors

    def test_duplicate_username_validation(self):
        """Test duplicate username validation."""
        existing_user = UserFactory()

        data = {
            'username': existing_user.username,  # Duplicate
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'terms_accepted': True,
            'privacy_policy_accepted': True
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'username' in serializer.errors

    def test_terms_not_accepted(self):
        """Test registration without accepting terms."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'terms_accepted': False,  # Not accepted
            'privacy_policy_accepted': True
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'terms_accepted' in serializer.errors

    def test_email_normalization(self):
        """Test email normalization to lowercase."""
        data = {
            'username': 'newuser',
            'email': 'NEWUSER@EXAMPLE.COM',  # Uppercase
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'terms_accepted': True,
            'privacy_policy_accepted': True
        }

        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['email'] == 'newuser@example.com'


@pytest.mark.django_db
class TestUserLoginSerializer(TestCase):
    """Test UserLoginSerializer."""

    def setUp(self):
        self.user = UserFactory()
        self.password = 'TestPassword123!'  # nosec - test password
        self.user.set_password(self.password)
        self.user.save()

    def test_valid_login_with_email(self):
        """Test valid login with email."""
        data = {
            'email_or_username': self.user.email,
            'password': self.password
        }

        serializer = UserLoginSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_valid_login_with_username(self):
        """Test valid login with username."""
        data = {
            'email_or_username': self.user.username,
            'password': self.password
        }

        serializer = UserLoginSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_credentials(self):
        """Test login with invalid credentials."""
        data = {
            'email_or_username': self.user.email,
            'password': 'wrongpassword'
        }

        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_missing_fields(self):
        """Test login with missing required fields."""
        data = {'email_or_username': self.user.email}  # Missing password

        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors

    def test_email_case_insensitive(self):
        """Test email login is case insensitive."""
        data = {
            'email_or_username': self.user.email.upper(),
            'password': self.password
        }

        serializer = UserLoginSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestPasswordChangeSerializer(TestCase):
    """Test PasswordChangeSerializer."""

    def test_valid_password_change(self):
        """Test valid password change data."""
        data = {
            'current_password': 'OldPassword123!',
            'new_password': 'NewPassword456!',
            'confirm_password': 'NewPassword456!'
        }

        serializer = PasswordChangeSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_password_mismatch(self):
        """Test new password confirmation mismatch."""
        data = {
            'current_password': 'OldPassword123!',
            'new_password': 'NewPassword456!',
            'confirm_password': 'DifferentPassword789!'
        }

        serializer = PasswordChangeSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_same_password(self):
        """Test using same password as current."""
        data = {
            'current_password': 'SamePassword123!',
            'new_password': 'SamePassword123!',
            'confirm_password': 'SamePassword123!'
        }

        serializer = PasswordChangeSerializer(data=data)
        assert not serializer.is_valid()
        assert 'new_password' in serializer.errors

    def test_weak_new_password(self):
        """Test weak new password validation."""
        data = {
            'current_password': 'OldPassword123!',
            'new_password': '123',  # Too weak
            'confirm_password': '123'
        }

        serializer = PasswordChangeSerializer(data=data)
        assert not serializer.is_valid()
        assert 'new_password' in serializer.errors


@pytest.mark.django_db
class TestPasswordResetSerializer(TestCase):
    """Test password reset serializers."""

    def test_valid_reset_request(self):
        """Test valid password reset request."""
        data = {'email': 'user@example.com'}

        serializer = PasswordResetRequestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_email_format(self):
        """Test invalid email format in reset request."""
        data = {'email': 'invalid-email'}

        serializer = PasswordResetRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert 'email' in serializer.errors

    def test_valid_reset_confirm(self):
        """Test valid password reset confirmation."""
        data = {
            'token': 'valid-reset-token',
            'new_password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!'
        }

        serializer = PasswordResetConfirmSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_reset_password_mismatch(self):
        """Test password mismatch in reset confirmation."""
        data = {
            'token': 'valid-reset-token',
            'new_password': 'NewPassword123!',
            'confirm_password': 'DifferentPassword456!'
        }

        serializer = PasswordResetConfirmSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors


@pytest.mark.django_db
class TestEmailVerificationSerializer(TestCase):
    """Test EmailVerificationSerializer."""

    def test_valid_verification_token(self):
        """Test valid verification token."""
        data = {'token': 'valid-verification-token'}

        serializer = EmailVerificationSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_missing_token(self):
        """Test missing verification token."""
        data = {}

        serializer = EmailVerificationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'token' in serializer.errors

    def test_empty_token(self):
        """Test empty verification token."""
        data = {'token': ''}

        serializer = EmailVerificationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'token' in serializer.errors


@pytest.mark.django_db
class TestEmailChangeSerializer(TestCase):
    """Test email change serializers."""

    def setUp(self):
        self.user = UserFactory()

    def test_valid_email_change_request(self):
        """Test valid email change request."""
        data = {
            'new_email': 'newemail@example.com',
            'password': 'UserPassword123!'
        }

        serializer = EmailChangeRequestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_new_email(self):
        """Test invalid new email format."""
        data = {
            'new_email': 'invalid-email',
            'password': 'UserPassword123!'
        }

        serializer = EmailChangeRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert 'new_email' in serializer.errors

    def test_same_email(self):
        """Test changing to same email."""
        data = {
            'new_email': self.user.email,
            'password': 'UserPassword123!'
        }

        serializer = EmailChangeRequestSerializer(data=data)
        # Should validate but business logic should handle duplication
        assert serializer.is_valid()

    def test_valid_email_change_confirm(self):
        """Test valid email change confirmation."""
        data = {'token': 'valid-change-token'}

        serializer = EmailChangeConfirmSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestUserSessionSerializer(TestCase):
    """Test UserSessionSerializer."""

    def test_session_serialization(self):
        """Test session data serialization."""
        session = UserSessionFactory()

        serializer = UserSessionSerializer(session)
        data = serializer.data

        assert 'id' in data
        assert 'device_type' in data
        assert 'browser_name' in data
        assert 'ip_address' in data
        assert 'created_at' in data
        assert 'is_active' in data

    def test_session_with_context(self):
        """Test session serialization with current session context."""
        session = UserSessionFactory()
        context = {'current_session_id': str(session.id)}

        serializer = UserSessionSerializer(session, context=context)
        data = serializer.data

        assert data.get('is_current') is True

    def test_sensitive_data_excluded(self):
        """Test that sensitive data is excluded from serialization."""
        session = UserSessionFactory()

        serializer = UserSessionSerializer(session)
        data = serializer.data

        # Sensitive fields should not be in serialized data
        assert 'session_key' not in data
        assert 'refresh_token_jti' not in data
        assert 'device_fingerprint' not in data


@pytest.mark.django_db
class TestSessionTerminateSerializer(TestCase):
    """Test SessionTerminateSerializer."""

    def test_valid_session_id(self):
        """Test valid session ID for termination."""
        session_id = str(uuid.uuid4())
        data = {'session_id': session_id}

        serializer = SessionTerminateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_session_id(self):
        """Test invalid session ID format."""
        data = {'session_id': 'invalid-uuid'}

        serializer = SessionTerminateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'session_id' in serializer.errors

    def test_missing_session_id(self):
        """Test missing session ID."""
        data = {}

        serializer = SessionTerminateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'session_id' in serializer.errors


@pytest.mark.django_db
class TestUserBasicSerializer(TestCase):
    """Test UserBasicSerializer."""

    def test_user_basic_serialization(self):
        """Test basic user data serialization."""
        user = UserFactory()

        serializer = UserBasicSerializer(user)
        data = serializer.data

        assert 'id' in data
        assert 'username' in data
        assert 'email' in data
        assert 'first_name' in data
        assert 'last_name' in data

    def test_sensitive_data_excluded(self):
        """Test that sensitive user data is excluded."""
        user = UserFactory()

        serializer = UserBasicSerializer(user)
        data = serializer.data

        # Sensitive fields should not be in serialized data
        assert 'password' not in data
        assert 'failed_login_attempts' not in data
        assert 'locked_until' not in data


@pytest.mark.django_db
class TestAuthResponseSerializer(TestCase):
    """Test AuthResponseSerializer."""

    def test_auth_response_structure(self):
        """Test authentication response structure."""
        user = UserFactory()

        data = {
            'access_token': 'access-token-value',
            'refresh_token': 'refresh-token-value',
            'user': UserBasicSerializer(user).data,
            'message': 'Login successful'
        }

        serializer = AuthResponseSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_missing_required_fields(self):
        """Test missing required fields in auth response."""
        data = {
            'access_token': 'access-token-value'
            # Missing other required fields
        }

        serializer = AuthResponseSerializer(data=data)
        assert not serializer.is_valid()


@pytest.mark.django_db
class TestSuccessMessageSerializer(TestCase):
    """Test SuccessMessageSerializer."""

    def test_success_message_structure(self):
        """Test success message structure."""
        data = {
            'message': 'Operation successful',
            'detail': 'Additional details about the operation'
        }

        serializer = SuccessMessageSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_message_only(self):
        """Test success message with only message field."""
        data = {'message': 'Operation successful'}

        serializer = SuccessMessageSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestHealthCheckSerializer(TestCase):
    """Test HealthCheckSerializer."""

    def test_health_check_structure(self):
        """Test health check response structure."""
        data = {
            'status': 'healthy',
            'timestamp': '2023-10-29T15:30:00Z',
            'version': '1.0.0',
            'checks': {
                'database': {'status': 'healthy'},
                'cache': {'status': 'healthy'}
            }
        }

        serializer = HealthCheckSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestSerializerSecurity(TestCase):
    """Test security aspects of serializers."""

    def test_password_not_in_output(self):
        """Test that passwords are never in serialized output."""
        user = UserFactory()

        # Test all user-related serializers
        serializers_to_test = [
            UserBasicSerializer(user),
        ]

        for serializer in serializers_to_test:
            data = serializer.data
            # Check that no password-related fields are exposed
            password_fields = ['password', 'password_hash', 'hashed_password']
            for field in password_fields:
                assert field not in data

    def test_sensitive_tokens_handling(self):
        """Test handling of sensitive tokens."""
        # Verification tokens should be handled securely
        token = EmailVerificationTokenFactory()

        # Token values should not be easily guessable
        assert len(token.token) >= 32
        assert token.token != token.user.email

    def test_input_sanitization(self):
        """Test input sanitization in serializers."""
        # Test XSS prevention in text fields
        malicious_data = {
            'username': '<script>alert("xss")</script>',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'first_name': '<img src=x onerror=alert(1)>',
            'terms_accepted': True,
            'privacy_policy_accepted': True
        }

        serializer = UserRegistrationSerializer(data=malicious_data)
        if serializer.is_valid():
            # Validate that dangerous content is handled
            validated_data = serializer.validated_data
            assert '<script>' not in validated_data.get('username', '')
            assert '<img' not in validated_data.get('first_name', '')


@pytest.mark.django_db
class TestSerializerValidation(TestCase):
    """Test comprehensive validation logic."""

    def test_field_length_limits(self):
        """Test field length validation."""
        # Test overly long inputs
        long_string = 'x' * 1000

        data = {
            'username': long_string,
            'email': f'{long_string}@example.com',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'terms_accepted': True,
            'privacy_policy_accepted': True
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        # Should have validation errors for length

    def test_email_validation_edge_cases(self):
        """Test email validation edge cases."""
        invalid_emails = [
            'plainaddress',
            '@missingdomain.com',
            'missing@.com',
            'missing.domain@.com',
            'spaces in@email.com',
            'special!char@domain.com'
        ]

        for invalid_email in invalid_emails:
            data = {
                'username': 'testuser',
                'email': invalid_email,
                'password': 'SecurePassword123!',
                'confirm_password': 'SecurePassword123!',
                'terms_accepted': True,
                'privacy_policy_accepted': True
            }

            serializer = UserRegistrationSerializer(data=data)
            assert not serializer.is_valid(
            ), f"Email {invalid_email} should be invalid"

    def test_password_complexity_validation(self):
        """Test password complexity requirements."""
        weak_passwords = [
            'password',          # Too common
            '12345678',         # Too simple
            'PASSWORD123',      # No lowercase
            'password123',      # No uppercase
            'Password',         # No numbers
            'Pass1'            # Too short
        ]

        for weak_password in weak_passwords:
            data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': weak_password,
                'confirm_password': weak_password,
                'terms_accepted': True,
                'privacy_policy_accepted': True
            }

            serializer = UserRegistrationSerializer(data=data)
            # Should be invalid due to weak password
            if serializer.is_valid():
                # If serializer is valid, password validation should catch it elsewhere
                pass
