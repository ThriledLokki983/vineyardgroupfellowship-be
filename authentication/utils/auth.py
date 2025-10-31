"""
Authentication utilities for Vineyard Group Fellowship platform.

This module combines email verification and password management utilities:
- Email verification with secure token generation
- Password reset functionality with security features
- Password strength validation and breach checking
- Email sending services with template support

Created: October 2025
"""

import secrets
import hashlib
import logging
import threading
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _

from ..models import AuditLog

User = get_user_model()
logger = logging.getLogger(__name__)


# === EMAIL UTILITIES ===

def send_email_async(send_func, *args, **kwargs):
    """
    Send email asynchronously in a background thread to prevent request timeouts.

    This is critical for Railway/production where SMTP connections can be slow
    and cause HTTP request timeouts (30s limit on Railway).

    Args:
        send_func: The email send function to call
        *args, **kwargs: Arguments to pass to send_func

    Returns:
        True if email was queued successfully
    """
    def send_thread():
        try:
            send_func(*args, **kwargs)
            logger.info(f"Async email sent successfully")
        except Exception as e:
            logger.error(f"Async email send failed: {e}", exc_info=True)

    thread = threading.Thread(target=send_thread)
    thread.daemon = True  # Daemon thread won't block program exit
    thread.start()

    logger.info("Email queued for async sending")
    return True


def normalize_email(email):
    """
    Normalize email addresses by converting to lowercase and handling edge cases.

    Args:
        email (str): Email address to normalize

    Returns:
        str: Normalized email address
    """
    if not email:
        return email

    # Convert to lowercase and strip whitespace
    email = email.strip().lower()

    # Handle Gmail-specific normalization (remove dots and plus-addressing)
    if email.endswith('@gmail.com') or email.endswith('@googlemail.com'):
        local_part, domain = email.split('@', 1)
        # Remove dots from Gmail local part
        local_part = local_part.replace('.', '')
        # Remove plus-addressing
        if '+' in local_part:
            local_part = local_part.split('+')[0]
        email = f"{local_part}@{domain}"

    return email


# === EMAIL VERIFICATION UTILITIES ===

class EmailVerificationToken:
    """
    Secure token generator for email verification.

    Features:
    - Cryptographically secure token generation
    - Configurable expiration times
    - Base64 URL-safe encoding for user IDs
    - Token validation with security checks
    """

    def __init__(self, token_lifetime: timedelta = None):
        """
        Initialize token generator.

        Args:
            token_lifetime: How long tokens remain valid (default: 24 hours)
        """
        self.token_lifetime = token_lifetime or timedelta(hours=24)

    def make_token(self, user: User) -> str:
        """
        Generate a secure verification token for a user.

        Args:
            user: The user for whom to generate the token

        Returns:
            A secure token string
        """
        timestamp = int(timezone.now().timestamp())

        # Create token payload with user info and timestamp
        payload = f"{user.pk}:{user.email}:{timestamp}"

        # Generate token hash
        token_hash = hashlib.sha256(payload.encode()).hexdigest()

        # Combine timestamp and hash for the final token
        token = f"{timestamp}:{token_hash}"

        logger.info(
            f"Generated email verification token for user: {user.email}")
        return token

    def check_token(self, user: User, token: str) -> bool:
        """
        Validate a verification token for a user.

        Args:
            user: The user to validate the token for
            token: The token to validate

        Returns:
            True if token is valid, False otherwise
        """
        try:
            if not token or ':' not in token:
                return False

            timestamp_str, token_hash = token.split(':', 1)
            timestamp = int(timestamp_str)

            # Check if token has expired
            token_time = datetime.fromtimestamp(
                timestamp, tz=timezone.get_current_timezone())
            if timezone.now() - token_time > self.token_lifetime:
                logger.warning(
                    f"Expired email verification token for user: {user.email}")
                return False

            # Create expected token payload
            user_payload = f"{user.pk}:{user.email}:{timestamp}"
            expected_hash = hashlib.sha256(user_payload.encode()).hexdigest()

            if token_hash == expected_hash:
                logger.info(
                    f"Valid email verification token for user: {user.email}")
                return True

            logger.warning(
                f"Invalid email verification token for user: {user.email}")
            return False

        except (ValueError, TypeError) as e:
            logger.error(f"Error validating email verification token: {e}")
            return False

    def encode_uid(self, user: User) -> str:
        """
        Encode user ID for URL inclusion.

        Args:
            user: The user whose ID to encode

        Returns:
            Base64 encoded user ID
        """
        return urlsafe_base64_encode(force_bytes(user.pk))

    def decode_uid(self, uidb64: str) -> Optional[User]:
        """
        Decode user ID from URL parameter.

        Args:
            uidb64: Base64 encoded user ID

        Returns:
            User instance if valid, None otherwise
        """
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            return user
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None


class EmailVerificationService:
    """
    Service for sending email verification emails.

    Features:
    - HTML and text email templates
    - Secure verification link generation
    - Error handling and logging
    - Template context preparation
    """

    def __init__(self):
        """Initialize the email verification service."""
        self.token_generator = EmailVerificationToken()

    def send_verification_email(self, user: User, request=None) -> bool:
        """
        Send verification email to user asynchronously.

        Args:
            user: The user to send verification email to
            request: Django request object for URL building

        Returns:
            True if email queued successfully, False otherwise
        """
        try:
            # Generate verification token
            token = self.token_generator.make_token(user)
            uidb64 = self.token_generator.encode_uid(user)

            # Build verification URL - use backend URL for token validation
            backend_url = getattr(settings, 'BACKEND_URL',
                                  'http://localhost:8001')
            verification_url = f"{backend_url}/api/v1/auth/email/verify/{uidb64}/{token}/"

            # Prepare email context
            context = {
                'user': user,
                'verification_url': verification_url,
                'site_name': getattr(settings, 'SITE_NAME', 'Vineyard Group Fellowship'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@Vineyard Group Fellowship.com'),
                'token_expiry_hours': 24,
                'current_year': timezone.now().year,
            }

            # Render email templates
            subject = _(
                'Verify your email address - %(site_name)s') % {'site_name': context['site_name']}

            text_content = render_to_string(
                'authentication/email_verification_email.txt',
                context
            )

            html_content = render_to_string(
                'authentication/email_verification_email.html',
                context
            )

            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=getattr(
                    settings, 'DEFAULT_FROM_EMAIL', 'noreply@Vineyard Group Fellowship.com'),
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")

            # Send email asynchronously to prevent request timeout
            import threading
            from django.core.mail import get_connection
            import time

            def send_async():
                start_time = time.time()
                try:
                    # Create a new connection with timeout settings
                    email_timeout = getattr(settings, 'EMAIL_TIMEOUT', 60)
                    logger.info(f"EMAIL_TIMEOUT setting: {email_timeout}s")
                    logger.info(
                        f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'not set')}")
                    logger.info(
                        f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'not set')}")
                    logger.info(
                        f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'not set')}")

                    logger.info("Creating email connection...")
                    connection = get_connection(
                        timeout=email_timeout,
                        fail_silently=False
                    )
                    logger.info("Connection created, attaching to email...")
                    email.connection = connection

                    logger.info("Sending email...")
                    email.send(fail_silently=False)
                    elapsed = time.time() - start_time
                    logger.info(
                        f"Email verification sent to: {user.email} (took {elapsed:.2f}s)")
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.error(
                        f"Async email send failed for {user.email} after {elapsed:.2f}s: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")

            thread = threading.Thread(target=send_async)
            thread.daemon = True  # Daemon thread won't prevent program exit
            thread.start()

            logger.info(f"Email verification queued for: {user.email}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to queue email verification for {user.email}: {e}")
            return False


# === PASSWORD MANAGEMENT UTILITIES ===

class PasswordResetToken:
    """
    Enhanced password reset token generator with expiration and security features.
    """

    def __init__(self):
        self.token_generator = PasswordResetTokenGenerator()

    def make_token(self, user: User) -> str:
        """
        Generate a secure password reset token for the user.

        Args:
            user: The user requesting password reset

        Returns:
            A secure token string
        """
        return self.token_generator.make_token(user)

    def check_token(self, user: User, token: str) -> bool:
        """
        Check if the password reset token is valid for the user.

        Args:
            user: The user the token was generated for
            token: The token to validate

        Returns:
            True if token is valid, False otherwise
        """
        return self.token_generator.check_token(user, token)

    def encode_uid(self, user: User) -> str:
        """
        Encode user ID for password reset URL.

        Args:
            user: The user to encode

        Returns:
            URL-safe base64 encoded user ID
        """
        return urlsafe_base64_encode(force_bytes(user.pk))

    def decode_uid(self, uidb64: str) -> Optional[User]:
        """
        Decode user ID from password reset URL.

        Args:
            uidb64: URL-safe base64 encoded user ID

        Returns:
            User instance if found, None otherwise
        """
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            return user
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None


class PasswordResetEmailService:
    """
    Service for sending password reset emails with security features.
    """

    def __init__(self):
        self.token_service = PasswordResetToken()

    def send_password_reset_email(
        self,
        user: User,
        request=None,
        template_name: str = 'authentication/password_reset_email.html'
    ) -> bool:
        """
        Send password reset email to user.

        Args:
            user: User requesting password reset
            request: HTTP request object for context
            template_name: Email template to use

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Generate reset token and URL
            token = self.token_service.make_token(user)
            uid = self.token_service.encode_uid(user)

            # Build reset URL - always use frontend URL
            base_url = getattr(settings, 'FRONTEND_URL',
                               'http://localhost:3000')
            reset_url = f"{base_url}/auth/reset-password/{uid}/{token}/"

            # Prepare email context
            context = {
                'user': user,
                'reset_url': reset_url,
                'site_name': getattr(settings, 'SITE_NAME', 'Vineyard Group Fellowship'),
                'uid': uid,
                'token': token,
                'expiry_hours': getattr(settings, 'PASSWORD_RESET_TIMEOUT', 86400) // 3600,
            }

            # Render email content
            subject = _('Password Reset Request for {site_name}').format(
                site_name=context['site_name']
            )

            # Use HTML template if available, fallback to plain text
            try:
                html_message = render_to_string(template_name, context)
                plain_message = render_to_string(
                    template_name.replace('.html', '.txt'),
                    context
                )
            except Exception:
                # Fallback to simple plain text message
                plain_message = self._generate_fallback_message(context)
                html_message = None

            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=getattr(
                    settings, 'DEFAULT_FROM_EMAIL', 'noreply@Vineyard Group Fellowship.com'),
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )

            # Log successful email send
            if request:
                AuditLog.objects.create(
                    user=user,
                    event_type='password_reset_email_sent',
                    description='Password reset email sent successfully',
                    ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                    user_agent=request.META.get(
                        'HTTP_USER_AGENT', 'Test Client'),
                    success=True,
                    risk_level='medium',
                    metadata={
                        'email': user.email,
                        'reset_url_generated': True
                    }
                )

            return True

        except Exception as e:
            # Log failed email send
            if request:
                AuditLog.objects.create(
                    user=user,
                    event_type='password_reset_email_failed',
                    description=f'Password reset email failed: {str(e)}',
                    ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                    user_agent=request.META.get(
                        'HTTP_USER_AGENT', 'Test Client'),
                    success=False,
                    risk_level='medium',
                    metadata={
                        'email': user.email,
                        'error': str(e)
                    }
                )

            return False

    def _generate_fallback_message(self, context: Dict[str, Any]) -> str:
        """
        Generate a fallback plain text password reset message.

        Args:
            context: Template context dictionary

        Returns:
            Plain text email message
        """
        return _("""
Hello {username},

You requested a password reset for your {site_name} account.

To reset your password, click the link below:
{reset_url}

This link will expire in {expiry_hours} hours.

If you didn't request this, please ignore this email.

Best regards,
The {site_name} Team
        """).format(**context).strip()


class PasswordStrengthValidator:
    """
    Enhanced password strength validation with security features.
    """

    @staticmethod
    def validate_password_strength(password: str, user=None) -> Dict[str, Any]:
        """
        Validate password strength with multiple criteria.

        Args:
            password: Password to validate
            user: User instance for context-aware validation

        Returns:
            Dictionary with validation results
        """
        errors = []
        score = 0
        max_score = 10

        # Length check
        if len(password) < 8:
            errors.append(_("Password must be at least 8 characters long."))
        elif len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1

        # Character variety checks
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if has_lower:
            score += 1
        else:
            errors.append(
                _("Password must contain at least one lowercase letter."))

        if has_upper:
            score += 1
        else:
            errors.append(
                _("Password must contain at least one uppercase letter."))

        if has_digit:
            score += 1
        else:
            errors.append(_("Password must contain at least one number."))

        if has_special:
            score += 2
        else:
            errors.append(
                _("Password must contain at least one special character."))

        # Common patterns check
        common_patterns = [
            'password', 'admin', 'user', 'login', 'welcome',
            '123456', 'qwerty', 'abc123', 'password123'
        ]

        if any(pattern in password.lower() for pattern in common_patterns):
            errors.append(
                _("Password contains common patterns that should be avoided."))
            score = max(0, score - 2)

        # User-specific checks
        if user:
            user_related = [
                user.username.lower() if user.username else '',
                user.email.split('@')[0].lower() if user.email else '',
                user.first_name.lower() if user.first_name else '',
                user.last_name.lower() if user.last_name else ''
            ]

            if any(related and related in password.lower() for related in user_related):
                errors.append(
                    _("Password should not contain your personal information."))
                score = max(0, score - 1)

        # Calculate strength level
        if score >= 8:
            strength = 'very_strong'
        elif score >= 6:
            strength = 'strong'
        elif score >= 4:
            strength = 'medium'
        elif score >= 2:
            strength = 'weak'
        else:
            strength = 'very_weak'

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'score': score,
            'max_score': max_score,
            'strength': strength,
            'percentage': int((score / max_score) * 100)
        }


class PasswordSecurityService:
    """
    Service for password security operations and breach checking.
    """

    @staticmethod
    def check_password_breach(password: str, timeout: int = 5) -> bool:
        """
        Check if password has been found in data breaches using HaveIBeenPwned API.

        Args:
            password: Password to check
            timeout: Request timeout in seconds

        Returns:
            True if password found in breaches, False otherwise
        """
        try:
            import requests

            # Generate SHA-1 hash of password
            sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
            prefix = sha1_hash[:5]
            suffix = sha1_hash[5:]

            # Query HaveIBeenPwned API with k-anonymity
            response = requests.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                timeout=timeout,
                headers={
                    'User-Agent': 'Vineyard Group Fellowship-PasswordChecker/1.0'}
            )

            if response.status_code == 200:
                # Check if our suffix appears in the response
                for line in response.text.splitlines():
                    hash_suffix, count = line.split(':')
                    if hash_suffix == suffix:
                        return True

            return False

        except Exception:
            # Fail open on network errors - don't block user
            return False

    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """
        Generate a cryptographically secure password.

        Args:
            length: Length of password to generate

        Returns:
            Secure random password
        """
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))


class EmailVerificationValidator:
    """
    Validator for email verification operations.

    Features:
    - Token format validation
    - User state validation
    - Security checks
    - Error message standardization
    """

    def __init__(self):
        """Initialize the validator."""
        self.token_generator = EmailVerificationToken()

    def validate_verification_request(self, uidb64: str, token: str) -> Dict[str, Any]:
        """
        Validate email verification request.

        Args:
            uidb64: Base64 encoded user ID
            token: Verification token

        Returns:
            Dictionary with validation results
        """
        result = {
            'is_valid': False,
            'user': None,
            'errors': [],
        }

        # Validate uidb64
        user = self.token_generator.decode_uid(uidb64)
        if not user:
            result['errors'].append(_("Invalid user identifier."))
            return result

        result['user'] = user

        # Check if user is already verified
        if user.email_verified:
            result['errors'].append(_("Email is already verified."))
            return result

        # Note: We don't check is_active here because inactive users should be able to verify their email
        # The verification process will activate them

        # Validate token
        if not self.token_generator.check_token(user, token):
            result['errors'].append(
                _("Invalid or expired verification token."))
            return result

        result['is_valid'] = True
        return result

    def verify_user_email(self, user: User) -> bool:
        """
        Mark user's email as verified.

        Args:
            user: The user whose email to verify

        Returns:
            True if verification successful, False otherwise
        """
        try:
            # Update user's email verification status
            user.email_verified = True
            user.email_verified_at = timezone.now()
            user.is_active = True
            user.save(update_fields=['email_verified',
                      'email_verified_at', 'is_active'])

            logger.info(f"Email verified for user: {user.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to verify email for user {user.email}: {e}")
            return False


# === UTILITY INSTANCES AND CONVENIENCE FUNCTIONS ===

# Email verification utilities
email_verification_token = EmailVerificationToken()
email_verification_service = EmailVerificationService()
email_verification_validator = EmailVerificationValidator()

# Password utilities
password_reset_token = PasswordResetToken()
password_email_service = PasswordResetEmailService()
password_validator = PasswordStrengthValidator()
password_security = PasswordSecurityService()


# Convenience functions for easy import
def send_verification_email(user: User, request=None) -> bool:
    """Send email verification to user."""
    return email_verification_service.send_verification_email(user, request)


def send_password_reset_email(user: User, request=None) -> bool:
    """Send password reset email to user."""
    return password_email_service.send_password_reset_email(user, request)


def validate_password_strength(password: str, user=None) -> Dict[str, Any]:
    """Validate password strength."""
    return password_validator.validate_password_strength(password, user)


def verify_email_token(uidb64: str, token: str) -> Dict[str, Any]:
    """
    Convenience function to verify email token.

    Args:
        uidb64: Base64 encoded user ID
        token: Verification token

    Returns:
        Dictionary with validation results
    """
    validator = EmailVerificationValidator()
    return validator.validate_verification_request(uidb64, token)


def check_password_breach(password: str) -> bool:
    """Check if password has been breached."""
    return password_security.check_password_breach(password)


# === UTILITY FUNCTIONS ===

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: Length of the token in bytes (default 32)

    Returns:
        Secure random token as hex string
    """
    return secrets.token_hex(length)


def generate_verification_token() -> str:
    """Generate a secure token for email verification."""
    return generate_secure_token(32)


def generate_reset_token() -> str:
    """Generate a secure token for password reset."""
    return generate_secure_token(32)


def is_disposable_email(email: str) -> bool:
    """
    Check if email is from a disposable email service.

    Args:
        email: Email address to check

    Returns:
        True if email is from a disposable service
    """
    # Common disposable email domains
    disposable_domains = {
        '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
        'tempmail.org', 'yopmail.com', '0-mail.com', '33mail.com',
        'temp-mail.org', 'throwaway.email', 'fakeinbox.com'
    }

    if not email or '@' not in email:
        return False

    domain = email.split('@')[1].lower()
    return domain in disposable_domains


def estimate_password_strength(password: str) -> str:
    """
    Estimate password strength level.

    Args:
        password: Password to evaluate

    Returns:
        Strength level: 'weak', 'medium', 'strong', 'very_strong'
    """
    if not password:
        return 'weak'

    score = 0

    # Length scoring
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1

    # Character variety
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[0-9]', password):
        score += 1
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\?]', password):
        score += 1

    # Return strength based on score
    if score <= 2:
        return 'weak'
    elif score <= 4:
        return 'medium'
    elif score <= 6:
        return 'strong'
    else:
        return 'very_strong'


def get_client_ip(request) -> str:
    """
    Extract client IP address from request.

    Args:
        request: Django HTTP request object

    Returns:
        Client IP address
    """
    # Check for forwarded IP (common in production behind proxy)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')

    return ip or '127.0.0.1'


class PasswordValidator:
    """Password validation utility class."""

    @staticmethod
    def validate_password_strength(password: str, user=None) -> Dict[str, Any]:
        """Validate password strength - alias for main function."""
        return password_security.validate_password_strength(password, user)
