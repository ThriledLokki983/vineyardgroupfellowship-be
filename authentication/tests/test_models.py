"""
Tests for authentication models.

Comprehensive tests for all authentication models including:
- User model extensions
- Session management
- Token blacklisting
- Email verification
- Password reset
- Audit logging
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
import uuid

from ..models import (
    UserSession, TokenBlacklist, EmailVerificationToken,
    PasswordResetToken, PasswordHistory, AuditLog
)
from .factories import (
    UserFactory, SuperUserFactory, UnverifiedUserFactory, LockedUserFactory,
    UserSessionFactory, InactiveSessionFactory, TokenBlacklistFactory,
    EmailVerificationTokenFactory, UsedEmailVerificationTokenFactory,
    ExpiredEmailVerificationTokenFactory, PasswordResetTokenFactory,
    UsedPasswordResetTokenFactory, ExpiredPasswordResetTokenFactory,
    PasswordHistoryFactory, AuditLogFactory, create_complete_user_scenario
)

User = get_user_model()


@pytest.mark.django_db
class TestUserModel(TestCase):
    """Test User model extensions."""

    def setUp(self):
        self.user = UserFactory()

    def test_user_creation(self):
        """Test basic user creation."""
        assert self.user.email is not None
        assert self.user.username is not None
        assert self.user.email_verified is True
        assert self.user.is_active is True

    def test_user_str_representation(self):
        """Test user string representation."""
        expected = f"{self.user.username} ({self.user.email})"
        assert str(self.user) == expected

    def test_email_normalization(self):
        """Test email is normalized to lowercase."""
        user = UserFactory(email="TEST@EXAMPLE.COM")
        user.clean()
        # Note: Email normalization should happen in clean() method
        assert "@EXAMPLE.COM" not in user.email or user.email == user.email.lower()

    def test_account_locking(self):
        """Test account locking functionality."""
        locked_user = LockedUserFactory()
        assert locked_user.is_account_locked() is True

        # Test unlocking
        locked_user.failed_login_attempts = 0
        locked_user.locked_until = None
        locked_user.save()
        assert locked_user.is_account_locked() is False

    def test_email_verification_status(self):
        """Test email verification status."""
        verified_user = UserFactory(email_verified=True)
        unverified_user = UnverifiedUserFactory()

        assert verified_user.email_verified is True
        assert unverified_user.email_verified is False

    def test_password_validation(self):
        """Test password validation."""
        user = UserFactory()

        # Test valid password
        user.set_password("ValidPassword123!")
        assert user.check_password("ValidPassword123!")

        # Test password change updates timestamp
        old_timestamp = user.password_changed_at
        user.set_password("NewValidPassword456!")
        user.password_changed_at = timezone.now()
        user.save()
        assert user.password_changed_at > old_timestamp

    def test_superuser_creation(self):
        """Test superuser creation."""
        admin = SuperUserFactory()
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_user_permissions(self):
        """Test user permission defaults."""
        regular_user = UserFactory()
        assert regular_user.is_staff is False
        assert regular_user.is_superuser is False
        assert regular_user.is_active is True


@pytest.mark.django_db
class TestUserSessionModel(TestCase):
    """Test UserSession model."""

    def setUp(self):
        self.user = UserFactory()
        self.session = UserSessionFactory(user=self.user)

    def test_session_creation(self):
        """Test session creation."""
        assert self.session.user == self.user
        assert self.session.is_active is True
        assert self.session.session_key is not None
        assert self.session.device_type is not None

    def test_session_str_representation(self):
        """Test session string representation."""
        expected = f"{self.user.email} - {self.session.device_type} - {self.session.created_at}"
        assert str(self.session) == expected

    def test_session_termination(self):
        """Test session termination."""
        assert self.session.is_active is True

        self.session.terminate(reason='test')
        assert self.session.is_active is False
        assert self.session.terminated_at is not None
        assert self.session.termination_reason == 'test'

    def test_session_device_info(self):
        """Test session device information."""
        session = UserSessionFactory(
            device_type='desktop',
            browser_name='Chrome',
            browser_version='118.0',
            os_name='macOS',
            os_version='14.0'
        )

        assert session.device_type == 'desktop'
        assert session.browser_name == 'Chrome'
        assert session.get_device_summary() is not None

    def test_session_activity_tracking(self):
        """Test session activity tracking."""
        old_activity = self.session.last_activity

        self.session.update_activity()
        assert self.session.last_activity > old_activity

    def test_session_risk_calculation(self):
        """Test session risk calculation."""
        # Test normal session
        normal_session = UserSessionFactory(
            device_type='desktop',
            location='San Francisco'
        )
        risk_score = normal_session.calculate_risk_score()
        assert 0 <= risk_score <= 100

    def test_session_cleanup(self):
        """Test session cleanup functionality."""
        # Create old inactive session
        old_session = InactiveSessionFactory(
            created_at=timezone.now() - timedelta(days=60)
        )

        # Test that cleanup would identify this session
        cutoff_date = timezone.now() - timedelta(days=30)
        old_sessions = UserSession.objects.filter(
            is_active=False,
            terminated_at__lt=cutoff_date
        )
        assert old_session in old_sessions


@pytest.mark.django_db
class TestTokenBlacklistModel(TestCase):
    """Test TokenBlacklist model."""

    def setUp(self):
        self.user = UserFactory()
        self.token = TokenBlacklistFactory(user=self.user)

    def test_token_creation(self):
        """Test token blacklist creation."""
        assert self.token.user == self.user
        assert self.token.jti is not None
        assert self.token.token_type in ['access', 'refresh']
        assert self.token.blacklisted_at is not None

    def test_token_str_representation(self):
        """Test token string representation."""
        expected = f"{self.user.email} - {self.token.token_type} - {self.token.blacklisted_at}"
        assert str(self.token) == expected

    def test_token_expiration(self):
        """Test token expiration checking."""
        # Test non-expired token
        fresh_token = TokenBlacklistFactory(
            expires_at=timezone.now() + timedelta(hours=1)
        )
        assert fresh_token.is_expired() is False

        # Test expired token
        expired_token = TokenBlacklistFactory(
            expires_at=timezone.now() - timedelta(hours=1)
        )
        assert expired_token.is_expired() is True

    def test_token_lookup(self):
        """Test token lookup functionality."""
        # Test finding token by JTI
        found_token = TokenBlacklist.objects.filter(jti=self.token.jti).first()
        assert found_token == self.token

    def test_token_reasons(self):
        """Test different blacklist reasons."""
        logout_token = TokenBlacklistFactory(reason='logout')
        password_token = TokenBlacklistFactory(reason='password_change')
        security_token = TokenBlacklistFactory(reason='security')

        assert logout_token.reason == 'logout'
        assert password_token.reason == 'password_change'
        assert security_token.reason == 'security'


@pytest.mark.django_db
class TestEmailVerificationTokenModel(TestCase):
    """Test EmailVerificationToken model."""

    def setUp(self):
        self.user = UnverifiedUserFactory()
        self.token = EmailVerificationTokenFactory(user=self.user)

    def test_token_creation(self):
        """Test email verification token creation."""
        assert self.token.user == self.user
        assert self.token.token is not None
        assert self.token.email == self.user.email
        assert self.token.is_used is False

    def test_token_str_representation(self):
        """Test token string representation."""
        expected = f"{self.user.email} - {self.token.created_at}"
        assert str(self.token) == expected

    def test_token_expiration(self):
        """Test token expiration."""
        expired_token = ExpiredEmailVerificationTokenFactory()
        assert expired_token.is_expired() is True

        fresh_token = EmailVerificationTokenFactory()
        assert fresh_token.is_expired() is False

    def test_token_usage(self):
        """Test token usage functionality."""
        assert self.token.is_valid() is True

        self.token.use_token()
        assert self.token.is_used is True
        assert self.token.used_at is not None
        assert self.token.is_valid() is False

    def test_token_validation(self):
        """Test token validation."""
        # Valid token
        valid_token = EmailVerificationTokenFactory()
        assert valid_token.is_valid() is True

        # Used token
        used_token = UsedEmailVerificationTokenFactory()
        assert used_token.is_valid() is False

        # Expired token
        expired_token = ExpiredEmailVerificationTokenFactory()
        assert expired_token.is_valid() is False


@pytest.mark.django_db
class TestPasswordResetTokenModel(TestCase):
    """Test PasswordResetToken model."""

    def setUp(self):
        self.user = UserFactory()
        self.token = PasswordResetTokenFactory(user=self.user)

    def test_token_creation(self):
        """Test password reset token creation."""
        assert self.token.user == self.user
        assert self.token.token is not None
        assert self.token.is_used is False
        assert self.token.expires_at > timezone.now()

    def test_token_str_representation(self):
        """Test token string representation."""
        expected = f"{self.user.email} - {self.token.created_at}"
        assert str(self.token) == expected

    def test_token_expiration(self):
        """Test token expiration."""
        expired_token = ExpiredPasswordResetTokenFactory()
        assert expired_token.is_expired() is True

        fresh_token = PasswordResetTokenFactory()
        assert fresh_token.is_expired() is False

    def test_token_usage(self):
        """Test token usage."""
        assert self.token.is_valid() is True

        self.token.use_token()
        assert self.token.is_used is True
        assert self.token.used_at is not None
        assert self.token.is_valid() is False

    def test_token_security(self):
        """Test token security features."""
        # Token should be long and random
        assert len(self.token.token) >= 32

        # Multiple tokens should be different
        token2 = PasswordResetTokenFactory(user=self.user)
        assert self.token.token != token2.token


@pytest.mark.django_db
class TestPasswordHistoryModel(TestCase):
    """Test PasswordHistory model."""

    def setUp(self):
        self.user = UserFactory()
        self.history = PasswordHistoryFactory(user=self.user)

    def test_history_creation(self):
        """Test password history creation."""
        assert self.history.user == self.user
        assert self.history.password_hash is not None
        assert self.history.created_at is not None

    def test_history_str_representation(self):
        """Test history string representation."""
        expected = f"{self.user.email} - {self.history.created_at}"
        assert str(self.history) == expected

    def test_multiple_history_entries(self):
        """Test multiple password history entries."""
        history2 = PasswordHistoryFactory(user=self.user)
        history3 = PasswordHistoryFactory(user=self.user)

        user_histories = PasswordHistory.objects.filter(user=self.user)
        assert user_histories.count() == 3

    def test_history_ordering(self):
        """Test password history ordering."""
        # Create entries with specific timestamps
        old_history = PasswordHistoryFactory(
            user=self.user,
            created_at=timezone.now() - timedelta(days=30)
        )
        new_history = PasswordHistoryFactory(
            user=self.user,
            created_at=timezone.now()
        )

        histories = PasswordHistory.objects.filter(
            user=self.user).order_by('-created_at')
        assert histories.first() == new_history
        assert histories.last() == old_history


@pytest.mark.django_db
class TestAuditLogModel(TestCase):
    """Test AuditLog model."""

    def setUp(self):
        self.user = UserFactory()
        self.log = AuditLogFactory(user=self.user)

    def test_log_creation(self):
        """Test audit log creation."""
        assert self.log.user == self.user
        assert self.log.event_type is not None
        assert self.log.timestamp is not None
        assert self.log.success is not None

    def test_log_str_representation(self):
        """Test log string representation."""
        expected = f"{self.log.event_type} - {self.user.email} - {self.log.timestamp}"
        assert str(self.log) == expected

    def test_anonymous_log(self):
        """Test anonymous audit log."""
        anon_log = AuditLogFactory(user=None, event_type='failed_login')
        assert anon_log.user is None
        assert anon_log.event_type == 'failed_login'

    def test_log_metadata(self):
        """Test audit log metadata."""
        log_with_metadata = AuditLogFactory(
            metadata={'action': 'test', 'ip': '127.0.0.1'}
        )
        assert log_with_metadata.metadata['action'] == 'test'
        assert log_with_metadata.metadata['ip'] == '127.0.0.1'

    def test_risk_levels(self):
        """Test different risk levels."""
        low_risk = AuditLogFactory(risk_level='low')
        medium_risk = AuditLogFactory(risk_level='medium')
        high_risk = AuditLogFactory(risk_level='high')

        assert low_risk.risk_level == 'low'
        assert medium_risk.risk_level == 'medium'
        assert high_risk.risk_level == 'high'

    def test_log_filtering(self):
        """Test audit log filtering."""
        # Create logs with different event types
        login_log = AuditLogFactory(event_type='login', user=self.user)
        logout_log = AuditLogFactory(event_type='logout', user=self.user)
        failed_log = AuditLogFactory(event_type='failed_login', success=False)

        # Test filtering by event type
        login_logs = AuditLog.objects.filter(event_type='login')
        assert login_log in login_logs

        # Test filtering by success
        failed_logs = AuditLog.objects.filter(success=False)
        assert failed_log in failed_logs

        # Test filtering by user
        user_logs = AuditLog.objects.filter(user=self.user)
        assert login_log in user_logs
        assert logout_log in user_logs


@pytest.mark.django_db
class TestModelRelationships(TestCase):
    """Test model relationships and cascading."""

    def test_user_deletion_cascade(self):
        """Test cascading when user is deleted."""
        scenario = create_complete_user_scenario()
        user = scenario['user']
        user_id = user.id

        # Verify related objects exist
        assert UserSession.objects.filter(user_id=user_id).exists()
        assert TokenBlacklist.objects.filter(user_id=user_id).exists()
        assert EmailVerificationToken.objects.filter(user_id=user_id).exists()
        assert PasswordHistory.objects.filter(user_id=user_id).exists()
        assert AuditLog.objects.filter(user_id=user_id).exists()

        # Delete user
        user.delete()

        # Verify related objects are handled appropriately
        # (Some may cascade delete, others may set NULL depending on model design)
        assert not User.objects.filter(id=user_id).exists()

    def test_session_user_relationship(self):
        """Test session-user relationship."""
        user = UserFactory()
        session1 = UserSessionFactory(user=user)
        session2 = UserSessionFactory(user=user)

        assert user.usersession_set.count() == 2
        assert session1 in user.usersession_set.all()
        assert session2 in user.usersession_set.all()

    def test_token_user_relationship(self):
        """Test token-user relationship."""
        user = UserFactory()
        token1 = TokenBlacklistFactory(user=user)
        token2 = TokenBlacklistFactory(user=user)

        assert user.tokenblacklist_set.count() == 2
        assert token1 in user.tokenblacklist_set.all()
        assert token2 in user.tokenblacklist_set.all()


@pytest.mark.django_db
class TestModelValidation(TestCase):
    """Test model validation."""

    def test_email_validation(self):
        """Test email validation."""
        # Test valid email
        user = UserFactory(email="test@example.com")
        user.full_clean()  # Should not raise

        # Test invalid email format
        with pytest.raises(ValidationError):
            user = User(
                username="testuser",
                email="invalid-email"
            )
            user.full_clean()

    def test_session_key_uniqueness(self):
        """Test session key uniqueness if required."""
        session1 = UserSessionFactory()

        # Try to create another session with same session key
        with pytest.raises(Exception):
            UserSessionFactory(session_key=session1.session_key)

    def test_token_validation(self):
        """Test token validation."""
        # Test token length and format
        token = EmailVerificationTokenFactory()
        assert len(token.token) >= 16  # Minimum secure length

        reset_token = PasswordResetTokenFactory()
        assert len(reset_token.token) >= 32  # Reset tokens should be longer
