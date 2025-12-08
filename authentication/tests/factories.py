"""
Factory Boy factories for authentication testing.

Provides test data generation for authentication models using Factory Boy.
Ensures realistic and varied test data for comprehensive testing.
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

from ..models import (
    UserSession, TokenBlacklist, EmailVerificationToken,
    PasswordResetToken, PasswordHistory, AuditLog
)

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for User model."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_staff = False
    is_superuser = False
    email_verified = True
    email_verified_at = factory.LazyFunction(timezone.now)
    failed_login_attempts = 0
    terms_accepted_at = factory.LazyFunction(timezone.now)
    privacy_policy_accepted_at = factory.LazyFunction(timezone.now)

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """Set user password."""
        if not create:
            return

        password = extracted or 'TestPassword123!'
        self.set_password(password)
        self.save()


class SuperUserFactory(UserFactory):
    """Factory for superuser."""

    is_staff = True
    is_superuser = True
    username = factory.Sequence(lambda n: f"admin{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")


class UnverifiedUserFactory(UserFactory):
    """Factory for unverified user."""

    email_verified = False
    email_verified_at = None


class LockedUserFactory(UserFactory):
    """Factory for locked user account."""

    failed_login_attempts = 5
    locked_until = factory.LazyFunction(
        lambda: timezone.now() + timedelta(hours=1))


class UserSessionFactory(DjangoModelFactory):
    """Factory for UserSession model."""

    class Meta:
        model = UserSession

    user = factory.SubFactory(UserFactory)
    session_key = factory.LazyFunction(lambda: f"session_{uuid.uuid4().hex}")
    refresh_token_jti = factory.LazyFunction(lambda: str(uuid.uuid4()))
    device_type = factory.Iterator(['desktop', 'mobile', 'tablet'])
    browser_name = factory.Iterator(['Chrome', 'Firefox', 'Safari', 'Edge'])
    browser_version = factory.Faker('numerify', text='##.#.#')
    os_name = factory.Iterator(['Windows', 'macOS', 'Linux', 'iOS', 'Android'])
    os_version = factory.Faker('numerify', text='##.#')
    ip_address = factory.Faker('ipv4')
    user_agent = factory.Faker('user_agent')
    device_fingerprint = factory.LazyFunction(lambda: f"fp_{uuid.uuid4().hex}")
    location = factory.Faker('city')
    is_active = True
    created_at = factory.LazyFunction(timezone.now)
    last_activity = factory.LazyFunction(timezone.now)


class InactiveSessionFactory(UserSessionFactory):
    """Factory for inactive session."""

    is_active = False
    terminated_at = factory.LazyFunction(timezone.now)
    termination_reason = 'logout'


class TokenBlacklistFactory(DjangoModelFactory):
    """Factory for TokenBlacklist model."""

    class Meta:
        model = TokenBlacklist

    user = factory.SubFactory(UserFactory)
    jti = factory.LazyFunction(lambda: str(uuid.uuid4()))
    token_type = factory.Iterator(['access', 'refresh'])
    reason = factory.Iterator(['logout', 'password_change', 'security'])
    blacklisted_at = factory.LazyFunction(timezone.now)
    expires_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=14))


class EmailVerificationTokenFactory(DjangoModelFactory):
    """Factory for EmailVerificationToken model."""

    class Meta:
        model = EmailVerificationToken

    user = factory.SubFactory(UnverifiedUserFactory)
    token = factory.LazyFunction(lambda: f"verify_{uuid.uuid4().hex}")
    email = factory.LazyAttribute(lambda obj: obj.user.email)
    created_at = factory.LazyFunction(timezone.now)
    expires_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(hours=24))
    is_used = False
    ip_address = factory.Faker('ipv4')


class UsedEmailVerificationTokenFactory(EmailVerificationTokenFactory):
    """Factory for used email verification token."""

    is_used = True
    used_at = factory.LazyFunction(timezone.now)


class ExpiredEmailVerificationTokenFactory(EmailVerificationTokenFactory):
    """Factory for expired email verification token."""

    created_at = factory.LazyFunction(
        lambda: timezone.now() - timedelta(days=2))
    expires_at = factory.LazyFunction(
        lambda: timezone.now() - timedelta(hours=1))


class PasswordResetTokenFactory(DjangoModelFactory):
    """Factory for PasswordResetToken model."""

    class Meta:
        model = PasswordResetToken

    user = factory.SubFactory(UserFactory)
    token = factory.LazyFunction(lambda: f"reset_{uuid.uuid4().hex}")
    created_at = factory.LazyFunction(timezone.now)
    expires_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(hours=1))
    is_used = False
    ip_address = factory.Faker('ipv4')
    user_agent = factory.Faker('user_agent')


class UsedPasswordResetTokenFactory(PasswordResetTokenFactory):
    """Factory for used password reset token."""

    is_used = True
    used_at = factory.LazyFunction(timezone.now)


class ExpiredPasswordResetTokenFactory(PasswordResetTokenFactory):
    """Factory for expired password reset token."""

    created_at = factory.LazyFunction(
        lambda: timezone.now() - timedelta(hours=2))
    expires_at = factory.LazyFunction(
        lambda: timezone.now() - timedelta(minutes=30))


class PasswordHistoryFactory(DjangoModelFactory):
    """Factory for PasswordHistory model."""

    class Meta:
        model = PasswordHistory

    user = factory.SubFactory(UserFactory)
    password_hash = factory.Faker('sha256')
    created_at = factory.LazyFunction(timezone.now)


class AuditLogFactory(DjangoModelFactory):
    """Factory for AuditLog model."""

    class Meta:
        model = AuditLog

    user = factory.SubFactory(UserFactory)
    event_type = factory.Iterator([
        'login', 'logout', 'registration', 'password_change',
        'password_reset', 'email_verification', 'account_locked'
    ])
    description = factory.LazyAttribute(
        lambda obj: f"{obj.event_type.title()} event")
    ip_address = factory.Faker('ipv4')
    user_agent = factory.Faker('user_agent')
    session_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    timestamp = factory.LazyFunction(timezone.now)
    success = True
    risk_level = factory.Iterator(['low', 'medium', 'high'])
    metadata = factory.Dict({
        'test': True,
        'factory_generated': True
    })


class FailedAuditLogFactory(AuditLogFactory):
    """Factory for failed audit log entry."""

    success = False
    risk_level = 'high'
    event_type = factory.Iterator([
        'failed_login', 'invalid_token', 'suspicious_activity'
    ])


class AnonymousAuditLogFactory(AuditLogFactory):
    """Factory for anonymous audit log entry."""

    user = None
    event_type = factory.Iterator([
        'failed_login', 'registration_attempt', 'password_reset_request'
    ])


# Helper functions for test data generation

def create_user_with_sessions(session_count=3, **user_kwargs):
    """Create a user with multiple sessions."""
    user = UserFactory(**user_kwargs)
    sessions = []
    for _ in range(session_count):
        session = UserSessionFactory(user=user)
        sessions.append(session)
    return user, sessions


def create_user_with_tokens(token_count=2, **user_kwargs):
    """Create a user with blacklisted tokens."""
    user = UserFactory(**user_kwargs)
    tokens = []
    for _ in range(token_count):
        token = TokenBlacklistFactory(user=user)
        tokens.append(token)
    return user, tokens


def create_complete_user_scenario():
    """Create a complete user scenario with all related objects."""
    user = UserFactory()

    # Sessions
    active_session = UserSessionFactory(user=user)
    inactive_session = InactiveSessionFactory(user=user)

    # Tokens
    blacklisted_token = TokenBlacklistFactory(user=user)

    # Email verification (already verified)
    used_verification = UsedEmailVerificationTokenFactory(user=user)

    # Password history
    old_password = PasswordHistoryFactory(user=user)

    # Audit logs
    login_log = AuditLogFactory(user=user, event_type='login')
    password_change_log = AuditLogFactory(
        user=user, event_type='password_change')

    return {
        'user': user,
        'active_session': active_session,
        'inactive_session': inactive_session,
        'blacklisted_token': blacklisted_token,
        'used_verification': used_verification,
        'old_password': old_password,
        'login_log': login_log,
        'password_change_log': password_change_log
    }


def create_user_with_profile(**user_kwargs):
    """
    Create a user with an associated profile.
    
    This is a convenience factory for tests that need both a user
    and their profile created together.
    
    Args:
        **user_kwargs: Keyword arguments to pass to UserFactory
    
    Returns:
        tuple: (user, profile)
    """
    from profiles.models import UserProfileBasic
    
    # Create user with any provided kwargs
    user = UserFactory(**user_kwargs)
    
    # Get or create profile (might already exist due to signals)
    profile, created = UserProfileBasic.objects.get_or_create(user=user)
    
    return user, profile

