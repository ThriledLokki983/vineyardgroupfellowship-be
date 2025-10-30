"""
Email service utilities for Vineyard Group Fellowship.

This module contains utilities for:
- Email template rendering
- Email service integration
- Delivery tracking
- Anti-spam measures
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import structlog

logger = structlog.get_logger(__name__)


class EmailService:
    """
    Service for sending transactional emails.
    """

    @staticmethod
    def send_verification_email(user, verification_token):
        """
        Send email verification email.

        Args:
            user: User instance
            verification_token: EmailVerificationToken instance
        """
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token.token}"

        context = {
            'user': user,
            'verification_url': verification_url,
            'token': verification_token.token,
            'expires_hours': 24,
            'site_name': 'Vineyard Group Fellowship',
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@vineyardgroupfellowship.com')
        }

        subject = "Verify Your Email - Vineyard Group Fellowship"

        try:
            # Render email templates
            text_content = render_to_string(
                'authentication/emails/verify_email.txt', context)
            html_content = render_to_string(
                'authentication/emails/verify_email.html', context)

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[verification_token.email]
            )
            msg.attach_alternative(html_content, "text/html")

            # Send email
            msg.send()

            logger.info(
                "Verification email sent successfully",
                user_id=str(user.id),
                email=verification_token.email,
                token_id=str(verification_token.id)
            )

        except Exception as e:
            logger.error(
                "Failed to send verification email",
                user_id=str(user.id),
                email=verification_token.email,
                error=str(e)
            )
            raise

    @staticmethod
    def send_password_reset_email(user, reset_token):
        """
        Send password reset email.

        Args:
            user: User instance
            reset_token: PasswordResetToken instance
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token.token}"

        context = {
            'user': user,
            'reset_url': reset_url,
            'token': reset_token.token,
            'expires_hours': 1,
            'site_name': 'Vineyard Group Fellowship',
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@vineyardgroupfellowship.com')
        }

        subject = "Password Reset - Vineyard Group Fellowship"

        try:
            # Render email templates
            text_content = render_to_string(
                'authentication/emails/password_reset.txt', context)
            html_content = render_to_string(
                'authentication/emails/password_reset.html', context)

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")

            # Send email
            msg.send()

            logger.info(
                "Password reset email sent successfully",
                user_id=str(user.id),
                email=user.email,
                token_id=str(reset_token.id)
            )

        except Exception as e:
            logger.error(
                "Failed to send password reset email",
                user_id=str(user.id),
                email=user.email,
                error=str(e)
            )
            raise

    @staticmethod
    def send_password_changed_notification(user, request=None):
        """
        Send notification that password was changed.

        Args:
            user: User instance
            request: HTTP request object for context
        """
        from .sessions import get_client_ip

        ip_address = get_client_ip(request) if request else 'Unknown'
        user_agent = request.META.get(
            'HTTP_USER_AGENT', 'Unknown') if request else 'Unknown'

        context = {
            'user': user,
            'change_time': timezone.now(),
            'ip_address': ip_address,
            'user_agent': user_agent,
            'site_name': 'Vineyard Group Fellowship',
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@vineyardgroupfellowship.com')
        }

        subject = "Password Changed - Vineyard Group Fellowship"

        try:
            # Render email templates
            text_content = render_to_string(
                'authentication/emails/password_changed.txt', context)
            html_content = render_to_string(
                'authentication/emails/password_changed.html', context)

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")

            # Send email
            msg.send()

            logger.info(
                "Password changed notification sent",
                user_id=str(user.id),
                email=user.email
            )

        except Exception as e:
            logger.error(
                "Failed to send password changed notification",
                user_id=str(user.id),
                email=user.email,
                error=str(e)
            )
            # Don't raise - this is a notification, not critical

    @staticmethod
    def send_suspicious_login_alert(user, session, anomalies):
        """
        Send alert for suspicious login activity.

        Args:
            user: User instance
            session: UserSession instance
            anomalies: List of detected anomalies
        """
        context = {
            'user': user,
            'session': session,
            'anomalies': anomalies,
            'login_time': session.created_at,
            'location': f"{session.city}, {session.country_code}" if session.city else "Unknown",
            'device': f"{session.device_type} - {session.browser_name}",
            'site_name': 'Vineyard Group Fellowship',
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@vineyardgroupfellowship.com')
        }

        subject = "Suspicious Login Activity - Vineyard Group Fellowship"

        try:
            # Render email templates
            text_content = render_to_string(
                'authentication/emails/suspicious_login.txt', context)
            html_content = render_to_string(
                'authentication/emails/suspicious_login.html', context)

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")

            # Send email
            msg.send()

            logger.info(
                "Suspicious login alert sent",
                user_id=str(user.id),
                email=user.email,
                session_id=str(session.id)
            )

        except Exception as e:
            logger.error(
                "Failed to send suspicious login alert",
                user_id=str(user.id),
                email=user.email,
                error=str(e)
            )
            # Don't raise - this is a notification

    @staticmethod
    def send_welcome_email(user):
        """
        Send welcome email after email verification.

        Args:
            user: User instance
        """
        context = {
            'user': user,
            'site_name': 'Vineyard Group Fellowship',
            'login_url': f"{settings.FRONTEND_URL}/login",
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@vineyardgroupfellowship.com')
        }

        subject = "Welcome to Vineyard Group Fellowship!"

        try:
            # Render email templates
            text_content = render_to_string(
                'authentication/emails/welcome.txt', context)
            html_content = render_to_string(
                'authentication/emails/welcome.html', context)

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")

            # Send email
            msg.send()

            logger.info(
                "Welcome email sent",
                user_id=str(user.id),
                email=user.email
            )

        except Exception as e:
            logger.error(
                "Failed to send welcome email",
                user_id=str(user.id),
                email=user.email,
                error=str(e)
            )
            # Don't raise - this is a nice-to-have


def validate_email_settings():
    """
    Validate email configuration.

    Returns:
        dict: Validation results
    """
    issues = []
    warnings = []

    # Check required settings
    required_settings = [
        'EMAIL_HOST',
        'EMAIL_PORT',
        'DEFAULT_FROM_EMAIL'
    ]

    for setting_name in required_settings:
        if not hasattr(settings, setting_name) or not getattr(settings, setting_name):
            issues.append(f"Missing required setting: {setting_name}")

    # Check email backend
    if not hasattr(settings, 'EMAIL_BACKEND'):
        issues.append("EMAIL_BACKEND not configured")
    elif settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
        warnings.append("Using console email backend (development only)")

    # Check authentication
    if hasattr(settings, 'EMAIL_HOST') and settings.EMAIL_HOST:
        if not hasattr(settings, 'EMAIL_HOST_USER') or not settings.EMAIL_HOST_USER:
            warnings.append(
                "EMAIL_HOST_USER not set - may cause authentication issues")

    # Check TLS/SSL
    if not getattr(settings, 'EMAIL_USE_TLS', False) and not getattr(settings, 'EMAIL_USE_SSL', False):
        warnings.append("Neither EMAIL_USE_TLS nor EMAIL_USE_SSL is enabled")

    return {
        'is_valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings
    }


def test_email_connection():
    """
    Test email connection and configuration.

    Returns:
        dict: Test results
    """
    from django.core.mail import get_connection

    try:
        connection = get_connection()
        connection.open()
        connection.close()

        return {
            'success': True,
            'message': "Email connection successful"
        }

    except Exception as e:
        return {
            'success': False,
            'message': f"Email connection failed: {str(e)}"
        }


class EmailThrottler:
    """
    Throttle email sending to prevent spam and abuse.
    """

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

    def can_send_email(self, email_type, recipient, window_minutes=60, max_emails=3):
        """
        Check if email can be sent based on throttling rules.

        Args:
            email_type: Type of email (verification, reset, etc.)
            recipient: Email recipient
            window_minutes: Time window in minutes
            max_emails: Maximum emails in window

        Returns:
            bool: True if email can be sent
        """
        if not self.redis_client:
            return True  # Allow if no Redis available

        key = f"email_throttle:{email_type}:{recipient}"
        current_count = self.redis_client.get(key)

        if current_count is None:
            # First email in window
            self.redis_client.setex(key, window_minutes * 60, 1)
            return True

        if int(current_count) < max_emails:
            # Within limit
            self.redis_client.incr(key)
            return True

        # Throttled
        logger.warning(
            "Email throttled",
            email_type=email_type,
            recipient=recipient,
            current_count=current_count,
            max_emails=max_emails
        )
        return False

    def record_email_sent(self, email_type, recipient):
        """
        Record that an email was sent.

        Args:
            email_type: Type of email
            recipient: Email recipient
        """
        if not self.redis_client:
            return

        # This is already handled in can_send_email for Redis-based throttling
        pass
