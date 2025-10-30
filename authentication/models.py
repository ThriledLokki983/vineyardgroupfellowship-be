"""
Authentication models for Vineyard Group Fellowship.

This module contains core authentication-related models including:
- User session tracking
- JWT token blacklisting
- Email verification tokens
- Password reset tokens
- Security audit logging
- Password history tracking

Note: UserProfile model is in the profiles app to separate concerns.
"""

import uuid
from datetime import datetime, timedelta
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator
from django.contrib.auth import get_user_model
import structlog

logger = structlog.get_logger(__name__)


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.

    Uses email as the primary authentication method while maintaining
    username field for compatibility. Adds email verification and
    enhanced security features.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text="Required. Enter a valid email address."
    )
    email_verified = models.BooleanField(
        default=False,
        help_text="Whether the user's email has been verified."
    )
    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when email was verified."
    )

    # Authentication preferences
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
    )

    # Account security
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of consecutive failed login attempts."
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Account locked until this timestamp."
    )
    password_changed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When password was last changed."
    )

    # Privacy and compliance
    terms_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user accepted terms of service."
    )
    privacy_policy_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user accepted privacy policy."
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'auth_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['email_verified']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.email

    def is_account_locked(self):
        """Check if account is currently locked."""
        if self.locked_until:
            return timezone.now() < self.locked_until
        return False

    def lock_account(self, duration_minutes=30):
        """Lock account for specified duration."""
        self.locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['locked_until'])

        logger.info(
            "Account locked",
            user_id=str(self.id),
            email=self.email,
            locked_until=self.locked_until.isoformat()
        )

    def unlock_account(self):
        """Unlock account and reset failed attempts."""
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['locked_until', 'failed_login_attempts'])

        logger.info(
            "Account unlocked",
            user_id=str(self.id),
            email=self.email
        )

    def record_failed_login(self):
        """Record a failed login attempt."""
        self.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account(duration_minutes=30)

        self.save(update_fields=['failed_login_attempts'])

        logger.warning(
            "Failed login attempt",
            user_id=str(self.id),
            email=self.email,
            attempt_count=self.failed_login_attempts
        )

    def record_successful_login(self):
        """Reset failed login attempts on successful login."""
        if self.failed_login_attempts > 0:
            self.failed_login_attempts = 0
            self.save(update_fields=['failed_login_attempts'])


class UserSession(models.Model):
    """
    Track user sessions for security and device management.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vineyard_sessions'
    )

    # Session identification
    session_key = models.CharField(
        _('session key'), max_length=40, unique=True)
    refresh_token_jti = models.CharField(
        _('refresh token JTI'),
        max_length=255,
        blank=True,
        help_text=_('JWT ID for token blacklisting.')
    )

    # Device/client information
    device_name = models.CharField(
        _('device name'),
        max_length=100,
        blank=True,
        help_text=_(
            'User-provided device name (e.g., "iPhone", "Work Laptop").')
    )
    device_fingerprint = models.CharField(
        _('device fingerprint'),
        max_length=255,
        blank=True,
        help_text=_('Generated device fingerprint for security tracking.')
    )
    user_agent = models.TextField(_('user agent'), blank=True)
    ip_address = models.GenericIPAddressField(
        _('IP address'), null=True, blank=True)

    # Geolocation (optional, privacy-conscious)
    city = models.CharField(_('city'), max_length=100, blank=True)
    country = models.CharField(_('country'), max_length=100, blank=True)

    # Session status
    is_active = models.BooleanField(_('is active'), default=True)
    is_verified = models.BooleanField(
        _('is verified'),
        default=False,
        help_text=_('Whether this session has been verified via 2FA.')
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    last_activity_at = models.DateTimeField(
        _('last activity at'), auto_now=True)
    last_rotation_at = models.DateTimeField(
        _('last rotation at'),
        default=timezone.now,
        help_text=_('Track token rotations for security monitoring.')
    )
    expires_at = models.DateTimeField(_('expires at'))

    class Meta:
        db_table = 'auth_user_session'
        verbose_name = _('User Session')
        verbose_name_plural = _('User Sessions')
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
            models.Index(fields=['refresh_token_jti']),
            models.Index(fields=['device_fingerprint']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['last_rotation_at']),
        ]

    def clean(self):
        """Validate model data"""
        if self.expires_at and self.expires_at <= timezone.now():
            raise ValidationError("Session cannot expire in the past")

    def __str__(self):
        status = "Active" if self.is_active and not self.is_expired else "Inactive"
        return f"{self.user.email} - {self.device_name or 'Unknown Device'} ({status})"

    @property
    def is_expired(self):
        """Check if session is expired."""
        return timezone.now() > self.expires_at

    def is_near_expiry(self, threshold_minutes=60):
        """Check if session expires within threshold minutes"""
        if not self.expires_at:
            return False
        threshold = timezone.now() + timezone.timedelta(minutes=threshold_minutes)
        return self.expires_at <= threshold

    def needs_rotation(self, rotation_interval_days=7):
        """Check if refresh token needs rotation based on last rotation"""
        if not self.last_rotation_at:
            return True
        threshold = self.last_rotation_at + \
            timezone.timedelta(days=rotation_interval_days)
        return timezone.now() >= threshold

    def mark_rotation(self):
        """Mark that token rotation occurred"""
        self.last_rotation_at = timezone.now()
        self.save(update_fields=['last_rotation_at'])

    def deactivate(self, reason=None):
        """Deactivate session and create audit log"""
        self.is_active = False
        self.save(update_fields=['is_active'])

        # Create audit log entry
        AuditLog.objects.create(
            user=self.user,
            action='session_terminated',
            ip_address=getattr(self, '_current_ip', self.ip_address),
            user_agent=getattr(self, '_current_user_agent',
                               self.user_agent or ''),
            details={'reason': reason or 'manual_deactivation',
                     'session_id': str(self.id)}
        )

    def extend_expiry(self, days=14):
        """Extend session expiry."""
        self.expires_at = timezone.now() + timezone.timedelta(days=days)
        self.save(update_fields=['expires_at'])

    @classmethod
    def cleanup_expired(cls):
        """Remove expired sessions"""
        now = timezone.now()
        expired_count = cls.objects.filter(
            models.Q(expires_at__lt=now) | models.Q(is_active=False)
        ).delete()[0]
        return expired_count

    @classmethod
    def get_active_sessions_for_user(cls, user):
        """Get all active sessions for a user"""
        return cls.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).order_by('-created_at')

    # Token Rotation & Session Validation Methods
    def validate_session_integrity(self) -> dict:
        """
        Validate session integrity and detect anomalies.

        Returns:
            Dictionary with validation results
        """
        issues = []
        risk_level = 'low'

        # Check session age
        if self.created_at:
            session_age = timezone.now() - self.created_at
            if session_age > timezone.timedelta(days=30):
                issues.append('Session is very old (>30 days)')
                risk_level = 'high'
            elif session_age > timezone.timedelta(days=7):
                issues.append('Session is aging (>7 days)')
                if risk_level == 'low':
                    risk_level = 'medium'

        # Check for inactivity
        if self.last_activity_at:
            inactive_time = timezone.now() - self.last_activity_at
            if inactive_time > timezone.timedelta(days=7):
                issues.append('Session inactive for over 7 days')
                risk_level = 'high'
            elif inactive_time > timezone.timedelta(days=1):
                issues.append('Session inactive for over 1 day')
                if risk_level == 'low':
                    risk_level = 'medium'

        # Check if refresh token is blacklisted
        if self.refresh_token_jti and TokenBlacklist.is_blacklisted(self.refresh_token_jti):
            issues.append('Refresh token is blacklisted')
            risk_level = 'high'

        return {
            'is_valid': len(issues) == 0 or risk_level != 'high',
            'risk_level': risk_level,
            'issues': issues,
            'last_validated': timezone.now().isoformat()
        }

    def invalidate_session_tokens(self, reason: str = 'session_terminated',
                                  ip_address: str = None, user_agent: str = None):
        """
        Invalidate all tokens associated with this session.

        Args:
            reason: Reason for invalidation
            ip_address: IP address of the request
            user_agent: User agent of the request
        """
        if self.refresh_token_jti:
            # Calculate token expiration
            from django.conf import settings
            refresh_lifetime = settings.SIMPLE_JWT.get(
                'REFRESH_TOKEN_LIFETIME', timezone.timedelta(days=14)
            )
            expires_at = self.created_at + refresh_lifetime

            TokenBlacklist.blacklist_token(
                jti=self.refresh_token_jti,
                user=self.user,
                token_type='refresh',
                reason=reason,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )

        # Mark session as inactive
        self.is_active = False
        self.save(update_fields=['is_active'])

    def rotate_refresh_token(self, new_jti: str, ip_address: str = None, user_agent: str = None):
        """
        Rotate the refresh token for this session.

        Args:
            new_jti: New token JTI
            ip_address: IP address of the request
            user_agent: User agent of the request
        """
        old_jti = self.refresh_token_jti

        if old_jti:
            # Blacklist the old token
            from django.conf import settings
            refresh_lifetime = settings.SIMPLE_JWT.get(
                'REFRESH_TOKEN_LIFETIME', timezone.timedelta(days=14)
            )
            expires_at = self.created_at + refresh_lifetime

            TokenBlacklist.blacklist_token(
                jti=old_jti,
                user=self.user,
                token_type='refresh',
                reason='rotation',
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )

        # Update session with new JTI
        self.refresh_token_jti = new_jti
        self.last_activity_at = timezone.now()
        self.save(update_fields=['refresh_token_jti', 'last_activity_at'])

    @classmethod
    def cleanup_invalid_sessions(cls) -> dict:
        """
        Clean up invalid and expired sessions.

        Returns:
            Dictionary with cleanup statistics
        """
        # Find sessions with blacklisted tokens
        blacklisted_jtis = TokenBlacklist.objects.filter(
            expires_at__gt=timezone.now()
        ).values_list('jti', flat=True)

        blacklisted_sessions = cls.objects.filter(
            refresh_token_jti__in=blacklisted_jtis
        )
        blacklisted_count = blacklisted_sessions.count()
        blacklisted_sessions.update(is_active=False)

        # Find very old sessions (>90 days)
        old_cutoff = timezone.now() - timezone.timedelta(days=90)
        old_sessions = cls.objects.filter(
            created_at__lt=old_cutoff,
            is_active=True
        )
        old_count = old_sessions.count()
        old_sessions.update(is_active=False)

        # Find inactive sessions (>30 days)
        inactive_cutoff = timezone.now() - timezone.timedelta(days=30)
        inactive_sessions = cls.objects.filter(
            last_activity_at__lt=inactive_cutoff,
            is_active=True
        )
        inactive_count = inactive_sessions.count()
        inactive_sessions.update(is_active=False)

        return {
            'blacklisted_sessions': blacklisted_count,
            'old_sessions': old_count,
            'inactive_sessions': inactive_count,
            'total_cleaned': blacklisted_count + old_count + inactive_count
        }


class TokenBlacklist(models.Model):
    """
    JWT token blacklist for immediate token revocation.

    Stores revoked JWT tokens to prevent their reuse. This provides
    immediate token invalidation for security purposes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    jti = models.CharField(
        max_length=255,
        unique=True,
        help_text="JWT ID (jti claim) of the blacklisted token"
    )
    token_type = models.CharField(
        max_length=20,
        choices=[
            ('access', 'Access Token'),
            ('refresh', 'Refresh Token'),
        ]
    )
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='blacklisted_tokens'
    )
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="When the token would have naturally expired"
    )
    reason = models.CharField(
        max_length=100,
        choices=[
            ('logout', 'User Logout'),
            ('password_change', 'Password Changed'),
            ('security_breach', 'Security Breach'),
            ('admin_action', 'Admin Action'),
            ('token_rotation', 'Token Rotation'),
        ],
        default='logout'
    )

    class Meta:
        db_table = 'auth_token_blacklist'
        indexes = [
            models.Index(fields=['jti']),
            models.Index(fields=['user']),
            models.Index(fields=['blacklisted_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.token_type} - {self.blacklisted_at}"

    @classmethod
    def is_blacklisted(cls, jti):
        """Check if a token JTI is blacklisted."""
        return cls.objects.filter(jti=jti, expires_at__gt=timezone.now()).exists()

    @classmethod
    def blacklist_token(cls, jti, user, token_type, reason='logout', expires_at=None,
                        ip_address=None, user_agent=None):
        """Blacklist a token."""
        if expires_at is None:
            from django.conf import settings
            refresh_lifetime = settings.SIMPLE_JWT.get(
                'REFRESH_TOKEN_LIFETIME', timezone.timedelta(days=14)
            )
            expires_at = timezone.now() + refresh_lifetime

        return cls.objects.create(
            jti=jti,
            user=user,
            token_type=token_type,
            reason=reason,
            expires_at=expires_at
        )


class EmailVerificationToken(models.Model):
    """
    Secure email verification tokens.

    One-time use tokens for email verification with expiration
    and security tracking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='email_verification_tokens'
    )
    token = models.CharField(max_length=255, unique=True)
    email = models.EmailField(
        help_text="Email address being verified (in case of email change)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(
        null=True,
        help_text="IP address where token was requested"
    )

    class Meta:
        db_table = 'auth_email_verification_token'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_used']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.email} - {self.created_at}"

    def is_expired(self):
        """Check if token has expired."""
        return timezone.now() > self.expires_at

    def is_valid(self):
        """Check if token is valid for use."""
        return not self.is_used and not self.is_expired()

    def use_token(self):
        """Mark token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class PasswordResetToken(models.Model):
    """
    Secure password reset tokens.

    One-time use tokens for password reset with enhanced security
    tracking and automatic invalidation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(
        null=True,
        help_text="IP address where token was requested"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent where token was requested"
    )

    class Meta:
        db_table = 'auth_password_reset_token'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_used']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.created_at}"

    def is_expired(self):
        """Check if token has expired."""
        return timezone.now() > self.expires_at

    def is_valid(self):
        """Check if token is valid for use."""
        return not self.is_used and not self.is_expired()

    def use_token(self):
        """Mark token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class PasswordHistory(models.Model):
    """
    Track password history to prevent reuse.

    Stores hashed passwords to prevent users from reusing
    recent passwords for enhanced security.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='password_history'
    )
    password_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auth_password_history'
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.created_at}"


class AuditLog(models.Model):
    """
    Security audit logging for authentication events.

    Comprehensive logging of security-related events for
    monitoring, compliance, and incident response.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )

    # Event details
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('login_success', 'Successful Login'),
            ('login_failure', 'Failed Login'),
            ('logout', 'Logout'),
            ('password_change', 'Password Change'),
            ('password_reset_request', 'Password Reset Request'),
            ('password_reset_complete', 'Password Reset Complete'),
            ('email_verification', 'Email Verification'),
            ('account_locked', 'Account Locked'),
            ('account_unlocked', 'Account Unlocked'),
            ('token_refresh', 'Token Refresh'),
            ('session_terminated', 'Session Terminated'),
            ('security_event', 'Security Event'),
        ]
    )
    description = models.TextField(help_text="Detailed event description")

    # Request context
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=40, blank=True)

    # Event metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(
        help_text="Whether the action was successful"
    )
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
            ('critical', 'Critical Risk'),
        ],
        default='low'
    )

    # Additional data (JSON field for extensibility)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional event-specific data"
    )

    class Meta:
        db_table = 'auth_audit_log'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['risk_level', 'timestamp']),
            models.Index(fields=['success', 'timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        user_email = self.user.email if self.user else "Anonymous"
        return f"{user_email} - {self.event_type} - {self.timestamp}"

    @classmethod
    def log_event(cls, event_type, user=None, description="", ip_address=None,
                  user_agent="", session_id="", success=True, risk_level='low',
                  metadata=None):
        """
        Convenience method to create audit log entries.
        """
        return cls.objects.create(
            user=user,
            event_type=event_type,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            success=success,
            risk_level=risk_level,
            metadata=metadata or {}
        )
