"""
Notification Service for Phase 2 Faith Features.

Handles email notifications for:
- Urgent prayer requests
- Answered prayers
- New prayer requests
- Testimony sharing and approvals
- Scripture sharing

Features:
- Quiet hours respect
- Rate limiting (max 5 emails/hour)
- User preference checking
- Notification logging
- Batch notifications for efficiency
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Q

from ..models import (
    NotificationPreference,
    NotificationLog,
    PrayerRequest,
    Testimony,
    Scripture,
)
from group.models import GroupMembership

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending email notifications with rate limiting and preferences.
    """

    # Rate limiting: max emails per hour per user
    MAX_EMAILS_PER_HOUR = 5

    # Notification type to preference field mapping
    PREFERENCE_MAPPING = {
        'urgent_prayer': 'email_urgent_prayer',
        'prayer_answered': 'email_prayer_answered',
        'new_prayer': 'email_new_prayer',
        'testimony_shared': 'email_testimony_shared',
        'testimony_approved': 'email_testimony_approved',
        'scripture_shared': 'email_scripture_shared',
        'new_discussion': 'email_new_discussion',
        'new_comment': 'email_new_comment',
        'new_reaction': 'email_new_reaction',
    }

    def __init__(self):
        """Initialize notification service."""
        self.from_email = settings.DEFAULT_FROM_EMAIL

    def send_urgent_prayer_notification(
        self,
        prayer_request: PrayerRequest
    ) -> Dict[str, int]:
        """
        Send notification to all group members about urgent prayer.

        Args:
            prayer_request: The urgent prayer request

        Returns:
            Dict with counts: {sent: int, skipped: int, failed: int}
        """
        # Get all active group members (except author)
        members = self._get_group_members(
            prayer_request.group,
            exclude_user=prayer_request.author
        )

        results = {'sent': 0, 'skipped': 0, 'failed': 0}

        for member in members:
            status = self._send_notification(
                user=member,
                notification_type='urgent_prayer',
                subject=f'🔥 URGENT: Prayer Request from {prayer_request.author.first_name or prayer_request.author.username}',
                template='messaging/emails/urgent_prayer.html',
                context={
                    'prayer': prayer_request,
                    'recipient': member,
                    'group': prayer_request.group,
                }
            )

            if status == 'sent':
                results['sent'] += 1
            elif status in ['failed']:
                results['failed'] += 1
            else:
                results['skipped'] += 1

        logger.info(
            f"Urgent prayer notification for {prayer_request.id}: "
            f"sent={results['sent']}, skipped={results['skipped']}, "
            f"failed={results['failed']}"
        )

        return results

    def send_prayer_answered_notification(
        self,
        prayer_request: PrayerRequest,
        recipients: Optional[List[User]] = None
    ) -> Dict[str, int]:
        """
        Send notification when prayer is answered.

        Notifies:
        - Group members who "prayed" for this request
        - All group members (if recipients not specified)

        Args:
            prayer_request: The answered prayer
            recipients: Optional list of specific users to notify

        Returns:
            Dict with counts: {sent: int, skipped: int, failed: int}
        """
        if not recipients:
            # Get all active group members (except author)
            recipients = self._get_group_members(
                prayer_request.group,
                exclude_user=prayer_request.author
            )

        results = {'sent': 0, 'skipped': 0, 'failed': 0}

        for member in recipients:
            status = self._send_notification(
                user=member,
                notification_type='prayer_answered',
                subject=f'✅ Prayer Answered: {prayer_request.title}',
                template='messaging/emails/prayer_answered.html',
                context={
                    'prayer': prayer_request,
                    'recipient': member,
                    'group': prayer_request.group,
                }
            )

            if status == 'sent':
                results['sent'] += 1
            elif status in ['failed']:
                results['failed'] += 1
            else:
                results['skipped'] += 1

        logger.info(
            f"Prayer answered notification for {prayer_request.id}: "
            f"sent={results['sent']}, skipped={results['skipped']}, "
            f"failed={results['failed']}"
        )

        return results

    def send_new_prayer_notification(
        self,
        prayer_request: PrayerRequest
    ) -> Dict[str, int]:
        """
        Send notification for new prayer request (non-urgent).

        Args:
            prayer_request: The new prayer request

        Returns:
            Dict with counts: {sent: int, skipped: int, failed: int}
        """
        # Get all active group members (except author)
        members = self._get_group_members(
            prayer_request.group,
            exclude_user=prayer_request.author
        )

        results = {'sent': 0, 'skipped': 0, 'failed': 0}

        for member in members:
            status = self._send_notification(
                user=member,
                notification_type='new_prayer',
                subject=f'🙏 New Prayer Request: {prayer_request.title}',
                template='messaging/emails/new_prayer.html',
                context={
                    'prayer': prayer_request,
                    'recipient': member,
                    'group': prayer_request.group,
                }
            )

            if status == 'sent':
                results['sent'] += 1
            elif status in ['failed']:
                results['failed'] += 1
            else:
                results['skipped'] += 1

        logger.info(
            f"New prayer notification for {prayer_request.id}: "
            f"sent={results['sent']}, skipped={results['skipped']}, "
            f"failed={results['failed']}"
        )

        return results

    def send_testimony_approved_notification(
        self,
        testimony: Testimony
    ) -> str:
        """
        Send notification to testimony author when approved for public.

        Args:
            testimony: The approved testimony

        Returns:
            Status: 'sent', 'skipped_*', or 'failed'
        """
        status = self._send_notification(
            user=testimony.author,
            notification_type='testimony_approved',
            subject='🌍 Your Testimony Has Been Approved for Public Sharing!',
            template='messaging/emails/testimony_approved.html',
            context={
                'testimony': testimony,
                'recipient': testimony.author,
                'group': testimony.group,
                'approved_by': testimony.approved_by,
            }
        )

        logger.info(
            f"Testimony approved notification for {testimony.id}: status={status}"
        )

        return status

    def send_testimony_shared_notification(
        self,
        testimony: Testimony
    ) -> Dict[str, int]:
        """
        Send notification when new testimony is shared.

        Args:
            testimony: The new testimony

        Returns:
            Dict with counts: {sent: int, skipped: int, failed: int}
        """
        # Get all active group members (except author)
        members = self._get_group_members(
            testimony.group,
            exclude_user=testimony.author
        )

        results = {'sent': 0, 'skipped': 0, 'failed': 0}

        for member in members:
            status = self._send_notification(
                user=member,
                notification_type='testimony_shared',
                subject=f'📢 New Testimony: {testimony.title}',
                template='messaging/emails/testimony_shared.html',
                context={
                    'testimony': testimony,
                    'recipient': member,
                    'group': testimony.group,
                }
            )

            if status == 'sent':
                results['sent'] += 1
            elif status in ['failed']:
                results['failed'] += 1
            else:
                results['skipped'] += 1

        logger.info(
            f"Testimony shared notification for {testimony.id}: "
            f"sent={results['sent']}, skipped={results['skipped']}, "
            f"failed={results['failed']}"
        )

        return results

    def send_scripture_shared_notification(
        self,
        scripture: Scripture
    ) -> Dict[str, int]:
        """
        Send notification when scripture is shared.

        Args:
            scripture: The shared scripture

        Returns:
            Dict with counts: {sent: int, skipped: int, failed: int}
        """
        # Get all active group members (except author)
        members = self._get_group_members(
            scripture.group,
            exclude_user=scripture.author
        )

        results = {'sent': 0, 'skipped': 0, 'failed': 0}

        for member in members:
            status = self._send_notification(
                user=member,
                notification_type='scripture_shared',
                subject=f'📖 Scripture Shared: {scripture.reference}',
                template='messaging/emails/scripture_shared.html',
                context={
                    'scripture': scripture,
                    'recipient': member,
                    'group': scripture.group,
                }
            )

            if status == 'sent':
                results['sent'] += 1
            elif status in ['failed']:
                results['failed'] += 1
            else:
                results['skipped'] += 1

        logger.info(
            f"Scripture shared notification for {scripture.id}: "
            f"sent={results['sent']}, skipped={results['skipped']}, "
            f"failed={results['failed']}"
        )

        return results

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _send_notification(
        self,
        user: User,
        notification_type: str,
        subject: str,
        template: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Send individual notification with all checks.

        Args:
            user: Recipient user
            notification_type: Type of notification
            subject: Email subject
            template: Email template path
            context: Template context

        Returns:
            Status: 'sent', 'skipped_*', or 'failed'
        """
        # Get or create notification preferences
        preferences, created = NotificationPreference.objects.get_or_create(
            user=user
        )

        # Check 1: Email enabled globally
        if not preferences.email_enabled:
            self._log_notification(
                user, notification_type, 'skipped_disabled',
                subject
            )
            return 'skipped_disabled'

        # Check 2: Specific notification type enabled
        pref_field = self.PREFERENCE_MAPPING.get(notification_type)
        if pref_field and not getattr(preferences, pref_field, True):
            self._log_notification(
                user, notification_type, 'skipped_disabled',
                subject
            )
            return 'skipped_disabled'

        # Check 3: Quiet hours
        if preferences.is_in_quiet_hours():
            self._log_notification(
                user, notification_type, 'skipped_quiet_hours',
                subject
            )
            return 'skipped_quiet_hours'

        # Check 4: Rate limiting
        if self._is_rate_limited(user):
            self._log_notification(
                user, notification_type, 'skipped_rate_limit',
                subject
            )
            return 'skipped_rate_limit'

        # All checks passed - send email
        try:
            # Add unsubscribe link to context
            context['unsubscribe_token'] = preferences.unsubscribe_token
            context['preferences_url'] = f"{settings.FRONTEND_URL}/settings/notifications"

            # Render HTML and text versions
            html_content = render_to_string(template, context)
            text_content = render_to_string(
                template.replace('.html', '.txt'),
                context
            )

            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=[user.email],
            )
            email.attach_alternative(html_content, "text/html")

            # Send email
            email.send(fail_silently=False)

            # Log success
            self._log_notification(
                user, notification_type, 'sent',
                subject
            )

            return 'sent'

        except Exception as e:
            logger.error(
                f"Failed to send {notification_type} email to {user.email}: {str(e)}"
            )
            self._log_notification(
                user, notification_type, 'failed',
                subject
            )
            return 'failed'

    def _is_rate_limited(self, user: User) -> bool:
        """
        Check if user has hit rate limit.

        Args:
            user: User to check

        Returns:
            True if rate limited, False otherwise
        """
        one_hour_ago = timezone.now() - timedelta(hours=1)

        sent_count = NotificationLog.objects.filter(
            user=user,
            status='sent',
            created_at__gte=one_hour_ago
        ).count()

        return sent_count >= self.MAX_EMAILS_PER_HOUR

    def _log_notification(
        self,
        user: User,
        notification_type: str,
        status: str,
        message: str
    ):
        """
        Log notification attempt.

        Args:
            user: Recipient user
            notification_type: Type of notification
            status: Status (sent, failed, skipped_*)
            subject: Email subject
        """
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            status=status,
            to_email=user.email,
            subject=subject
        )

    def _get_group_members(
        self,
        group,
        exclude_user: Optional[User] = None
    ) -> List[User]:
        """
        Get all active members of a group.

        Args:
            group: Group to get members from
            exclude_user: User to exclude (typically the author)

        Returns:
            List of User objects
        """
        query = GroupMembership.objects.filter(
            group=group,
            status='active'
        )

        if exclude_user:
            query = query.exclude(user=exclude_user)

        return [membership.user for membership in query.select_related('user')]


# Singleton instance
notification_service = NotificationService()
