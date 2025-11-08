"""
Celery tasks for authentication app.

Background tasks for:
- Cleaning up expired tokens
- Cleaning up expired sessions
- Security maintenance
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def cleanup_expired_tokens(self):
    """
    Delete expired authentication tokens.

    Runs daily at 1am via Celery Beat.
    Removes expired tokens to prevent database bloat:
    - Blacklisted JWT tokens
    - Password reset tokens
    - Email verification tokens

    Returns:
        dict: Summary of deleted tokens
    """
    try:
        from .models import TokenBlacklist, PasswordResetToken, EmailVerificationToken

        cutoff_date = timezone.now()

        # Delete expired blacklisted tokens
        deleted_blacklist = TokenBlacklist.objects.filter(
            expires_at__lt=cutoff_date
        ).delete()[0]

        # Delete expired password reset tokens
        deleted_reset = PasswordResetToken.objects.filter(
            expires_at__lt=cutoff_date
        ).delete()[0]

        # Delete expired email verification tokens
        deleted_verify = EmailVerificationToken.objects.filter(
            expires_at__lt=cutoff_date
        ).delete()[0]

        result = {
            'blacklist': deleted_blacklist,
            'password_reset': deleted_reset,
            'email_verification': deleted_verify,
            'total': deleted_blacklist + deleted_reset + deleted_verify,
            'status': 'success',
        }

        logger.info(
            f"Token cleanup completed: "
            f"{deleted_blacklist} blacklist, "
            f"{deleted_reset} reset, "
            f"{deleted_verify} verification tokens deleted"
        )

        return result

    except Exception as exc:
        logger.error(f"Token cleanup failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def cleanup_inactive_sessions(self):
    """
    Clean up inactive user sessions.

    Runs daily at 1:30am via Celery Beat.
    Removes sessions that have been inactive for > 30 days.

    Returns:
        dict: Summary of deleted sessions
    """
    try:
        from .models import UserSession

        cutoff_date = timezone.now() - timedelta(days=30)

        # Delete old inactive sessions
        deleted_count = UserSession.objects.filter(
            last_activity__lt=cutoff_date,
            is_active=False
        ).delete()[0]

        result = {
            'deleted': deleted_count,
            'status': 'success',
            'cutoff_date': cutoff_date.isoformat(),
        }

        logger.info(f"Cleaned up {deleted_count} inactive sessions")

        return result

    except Exception as exc:
        logger.error(f"Session cleanup failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def cleanup_old_audit_logs(self):
    """
    Archive old audit logs.

    Runs weekly on Saturday at 2am via Celery Beat.
    Keeps 1 year of audit logs for compliance.

    Returns:
        dict: Summary of archived logs
    """
    try:
        from .models import AuditLog

        cutoff_date = timezone.now() - timedelta(days=365)

        # Delete logs older than 1 year
        deleted_count = AuditLog.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]

        result = {
            'deleted': deleted_count,
            'status': 'success',
            'cutoff_date': cutoff_date.isoformat(),
        }

        logger.info(f"Cleaned up {deleted_count} audit logs")

        return result

    except Exception as exc:
        logger.error(f"Audit log cleanup failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=2)
def check_password_breach_async(self, user_id: str, password_hash: str):
    """
    Asynchronously check if password has been breached.

    This task runs after user registration to avoid blocking the registration process.
    If password is breached, sends an email notification to the user.

    Args:
        user_id: User UUID as string
        password_hash: SHA-256 hash of the password (for checking, not storing)

    Returns:
        dict: Result with breach status
    """
    try:
        from django.contrib.auth import get_user_model
        from .utils.auth import password_security

        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(
                f"User {user_id} not found for password breach check")
            return {'status': 'user_not_found'}

        # Check if password is breached (uses cached HaveIBeenPwned API)
        is_breached = password_security.check_password_breach(password_hash)

        if is_breached:
            logger.warning(
                f"User {user.email} registered with breached password",
                extra={'user_id': str(user.id)}
            )

            # TODO: Send email notification to user about breached password
            # from .utils.auth import send_password_breach_notification
            # send_password_breach_notification(user)

            return {
                'status': 'breached',
                'user_id': str(user.id),
                'email': user.email
            }

        return {
            'status': 'safe',
            'user_id': str(user.id)
        }

    except Exception as exc:
        logger.error(
            f"Password breach check failed for user {user_id}: {exc}",
            exc_info=True
        )
        # Don't retry indefinitely - breach check is optional
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        return {'status': 'error', 'error': str(exc)}
