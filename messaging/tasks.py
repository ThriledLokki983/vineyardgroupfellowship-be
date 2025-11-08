"""
Celery tasks for messaging app.

Background tasks for:
- Cleaning up soft-deleted content
- Cleaning up old notification logs
- Recounting denormalized counts
- Sending email notifications asynchronously
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def cleanup_soft_deleted_content(self):
    """
    Hard delete soft-deleted content after 30 days.

    Runs daily at 2am via Celery Beat.
    Removes discussions and comments that have been soft-deleted
    for more than 30 days to prevent database bloat.

    Returns:
        dict: Summary of deleted items
    """
    try:
        from .models import Discussion, Comment

        cutoff_date = timezone.now() - timedelta(days=30)

        # Delete old soft-deleted discussions
        deleted_discussions = Discussion.objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        ).delete()

        # Delete old soft-deleted comments
        deleted_comments = Comment.objects.filter(
            is_deleted=True,
            updated_at__lt=cutoff_date
        ).delete()

        result = {
            'discussions': deleted_discussions[0],
            'comments': deleted_comments[0],
            'status': 'success',
            'cutoff_date': cutoff_date.isoformat(),
        }

        logger.info(
            f"Cleanup completed: {deleted_discussions[0]} discussions, "
            f"{deleted_comments[0]} comments deleted"
        )

        return result

    except Exception as exc:
        logger.error(f"Cleanup task failed: {exc}", exc_info=True)
        # Retry in 5 minutes (300 seconds)
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def cleanup_old_notification_logs(self):
    """
    Delete notification logs older than 90 days.

    Runs daily at 2:30am via Celery Beat.
    Keeps database from growing infinitely while maintaining
    90 days of notification history for debugging.

    Returns:
        dict: Summary of deleted logs
    """
    try:
        from .models import NotificationLog

        cutoff_date = timezone.now() - timedelta(days=90)

        deleted_count = NotificationLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]

        result = {
            'deleted': deleted_count,
            'status': 'success',
            'cutoff_date': cutoff_date.isoformat(),
        }

        logger.info(f"Cleaned up {deleted_count} notification logs")

        return result

    except Exception as exc:
        logger.error(f"Notification log cleanup failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=2)
def recount_denormalized_counts(self):
    """
    Recalculate all denormalized counts to fix drift.

    Runs weekly on Sunday at 3am via Celery Beat.
    Fixes any discrepancies between denormalized counts
    (comment_count, reaction_count) and actual database counts.

    Returns:
        dict: Summary of fixed counts
    """
    try:
        from .models import Discussion, Comment, Reaction, PrayerRequest, Testimony, Scripture

        fixed_counts = {
            'discussions': 0,
            'prayers': 0,
            'testimonies': 0,
            'scriptures': 0,
        }

        # Fix discussion comment counts
        for discussion in Discussion.objects.all():
            actual_comment_count = Comment.objects.filter(
                discussion=discussion,
                is_deleted=False
            ).count()

            actual_reaction_count = Reaction.objects.filter(
                content_type='discussion',
                object_id=discussion.id
            ).count()

            needs_update = False
            update_fields = []

            if discussion.comment_count != actual_comment_count:
                discussion.comment_count = actual_comment_count
                update_fields.append('comment_count')
                needs_update = True

            if discussion.reaction_count != actual_reaction_count:
                discussion.reaction_count = actual_reaction_count
                update_fields.append('reaction_count')
                needs_update = True

            if needs_update:
                discussion.save(update_fields=update_fields)
                fixed_counts['discussions'] += 1

        # Fix prayer request counts
        for prayer in PrayerRequest.objects.all():
            actual_comment_count = Comment.objects.filter(
                content_type='prayer_request',
                content_id=prayer.id,
                is_deleted=False
            ).count()

            actual_reaction_count = Reaction.objects.filter(
                content_type='prayer_request',
                object_id=prayer.id
            ).count()

            needs_update = False
            update_fields = []

            if prayer.comment_count != actual_comment_count:
                prayer.comment_count = actual_comment_count
                update_fields.append('comment_count')
                needs_update = True

            if prayer.reaction_count != actual_reaction_count:
                prayer.reaction_count = actual_reaction_count
                update_fields.append('reaction_count')
                needs_update = True

            if needs_update:
                prayer.save(update_fields=update_fields)
                fixed_counts['prayers'] += 1

        # Fix testimony counts
        for testimony in Testimony.objects.all():
            actual_comment_count = Comment.objects.filter(
                content_type='testimony',
                content_id=testimony.id,
                is_deleted=False
            ).count()

            actual_reaction_count = Reaction.objects.filter(
                content_type='testimony',
                object_id=testimony.id
            ).count()

            needs_update = False
            update_fields = []

            if testimony.comment_count != actual_comment_count:
                testimony.comment_count = actual_comment_count
                update_fields.append('comment_count')
                needs_update = True

            if testimony.reaction_count != actual_reaction_count:
                testimony.reaction_count = actual_reaction_count
                update_fields.append('reaction_count')
                needs_update = True

            if needs_update:
                testimony.save(update_fields=update_fields)
                fixed_counts['testimonies'] += 1

        # Fix scripture counts
        for scripture in Scripture.objects.all():
            actual_comment_count = Comment.objects.filter(
                content_type='scripture',
                content_id=scripture.id,
                is_deleted=False
            ).count()

            actual_reaction_count = Reaction.objects.filter(
                content_type='scripture',
                object_id=scripture.id
            ).count()

            needs_update = False
            update_fields = []

            if scripture.comment_count != actual_comment_count:
                scripture.comment_count = actual_comment_count
                update_fields.append('comment_count')
                needs_update = True

            if scripture.reaction_count != actual_reaction_count:
                scripture.reaction_count = actual_reaction_count
                update_fields.append('reaction_count')
                needs_update = True

            if needs_update:
                scripture.save(update_fields=update_fields)
                fixed_counts['scriptures'] += 1

        result = {
            'fixed_counts': fixed_counts,
            'total_fixed': sum(fixed_counts.values()),
            'status': 'success',
        }

        logger.info(
            f"Recount completed: Fixed {result['total_fixed']} items - "
            f"Discussions: {fixed_counts['discussions']}, "
            f"Prayers: {fixed_counts['prayers']}, "
            f"Testimonies: {fixed_counts['testimonies']}, "
            f"Scriptures: {fixed_counts['scriptures']}"
        )

        return result

    except Exception as exc:
        logger.error(f"Recount task failed: {exc}", exc_info=True)
        # Retry in 10 minutes
        raise self.retry(exc=exc, countdown=600)
