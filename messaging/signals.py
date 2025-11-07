"""
Signals for messaging app.

Handles automatic FeedItem creation, count updates, and cache invalidation.
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import (
    Discussion,
    Comment,
    Reaction,
    FeedItem,
    CommentHistory,
    ContentReport,
    PrayerRequest,
    Testimony,
    Scripture,
)


# =============================================================================
# FEEDITEM AUTO-POPULATION
# =============================================================================

@receiver(post_save, sender=Discussion)
def create_feed_item_for_discussion(sender, instance, created, **kwargs):
    """Create FeedItem when Discussion is created."""
    if created:
        FeedItem.create_from_discussion(instance)


@receiver(post_save, sender=Discussion)
def update_feed_item_for_discussion(sender, instance, created, **kwargs):
    """Update FeedItem when Discussion is updated."""
    if not created:
        # Update existing FeedItem
        FeedItem.objects.filter(
            content_type='discussion',
            content_id=instance.id
        ).update(
            title=instance.title,
            preview=instance.content[:300] +
                ('...' if len(instance.content) > 300 else ''),
            comment_count=instance.comment_count,
            reaction_count=instance.reaction_count,
            is_pinned=instance.is_pinned,
            is_deleted=instance.is_deleted,
        )


@receiver(post_delete, sender=Discussion)
def delete_feed_item_for_discussion(sender, instance, **kwargs):
    """Delete FeedItem when Discussion is hard deleted."""
    FeedItem.objects.filter(
        content_type='discussion',
        content_id=instance.id
    ).delete()


# =============================================================================
# COMMENT COUNT UPDATES
# =============================================================================

@receiver(post_save, sender=Comment)
def increment_comment_count_on_create(sender, instance, created, **kwargs):
    """Increment discussion's comment count when comment is created."""
    if created and not instance.is_deleted:
        instance.discussion.increment_comment_count()

        # Also update FeedItem
        FeedItem.objects.filter(
            content_type='discussion',
            content_id=instance.discussion.id
        ).update(comment_count=instance.discussion.comment_count)


@receiver(post_delete, sender=Comment)
def decrement_comment_count_on_delete(sender, instance, **kwargs):
    """Decrement discussion's comment count when comment is deleted."""
    if not instance.is_deleted:  # Only if not already soft-deleted
        instance.discussion.decrement_comment_count()

        # Also update FeedItem
        FeedItem.objects.filter(
            content_type='discussion',
            content_id=instance.discussion.id
        ).update(comment_count=instance.discussion.comment_count)


# =============================================================================
# REACTION COUNT UPDATES
# =============================================================================

@receiver(post_save, sender=Reaction)
def increment_reaction_count_on_create(sender, instance, created, **kwargs):
    """Increment reaction count when reaction is created."""
    if created:
        if instance.discussion:
            instance.discussion.increment_reaction_count()

            # Update FeedItem
            FeedItem.objects.filter(
                content_type='discussion',
                content_id=instance.discussion.id
            ).update(reaction_count=instance.discussion.reaction_count)

        elif instance.comment:
            instance.comment.increment_reaction_count()


@receiver(post_delete, sender=Reaction)
def decrement_reaction_count_on_delete(sender, instance, **kwargs):
    """Decrement reaction count when reaction is deleted."""
    if instance.discussion:
        instance.discussion.decrement_reaction_count()

        # Update FeedItem
        FeedItem.objects.filter(
            content_type='discussion',
            content_id=instance.discussion.id
        ).update(reaction_count=instance.discussion.reaction_count)

    elif instance.comment:
        instance.comment.decrement_reaction_count()


# =============================================================================
# COMMENT EDIT HISTORY
# =============================================================================

@receiver(pre_save, sender=Comment)
def save_comment_history_on_edit(sender, instance, **kwargs):
    """Save comment history before edit."""
    if instance.pk:  # Only for updates, not creates
        try:
            old_comment = Comment.objects.get(pk=instance.pk)
            # Check if content changed
            if old_comment.content != instance.content:
                CommentHistory.objects.create(
                    comment=instance,
                    content=old_comment.content,
                    edited_by=instance.author  # In actual implementation, get from request
                )
                instance.is_edited = True
                instance.edited_at = instance.updated_at
        except Comment.DoesNotExist:
            pass


# =============================================================================
# CACHE INVALIDATION
# =============================================================================

@receiver(post_save, sender=Discussion)
def invalidate_feed_cache_on_discussion_change(sender, instance, **kwargs):
    """Invalidate feed cache when discussion is created/updated."""
    cache_key = f"group:{instance.group.id}:feed:*"
    # Delete all feed cache keys for this group
    # Use delete_pattern if available (Redis), otherwise silently skip
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(cache_key)


@receiver(post_delete, sender=Discussion)
def invalidate_feed_cache_on_discussion_delete(sender, instance, **kwargs):
    """Invalidate feed cache when discussion is deleted."""
    cache_key = f"group:{instance.group.id}:feed:*"
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(cache_key)


@receiver(post_save, sender=Comment)
def invalidate_feed_cache_on_comment_change(sender, instance, **kwargs):
    """Invalidate feed cache when comment is created/updated (counts changed)."""
    cache_key = f"group:{instance.discussion.group.id}:feed:*"
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(cache_key)


@receiver(post_save, sender=Reaction)
def invalidate_feed_cache_on_reaction_change(sender, instance, **kwargs):
    """Invalidate feed cache when reaction is created (counts changed)."""
    if instance.discussion:
        cache_key = f"group:{instance.discussion.group.id}:feed:*"
    else:
        cache_key = f"group:{instance.comment.discussion.group.id}:feed:*"
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(cache_key)


# =============================================================================
# CONTENT REPORT AUTO-UPDATE
# =============================================================================

@receiver(post_save, sender=ContentReport)
def update_report_flags_on_create(sender, instance, created, **kwargs):
    """Update is_reported and report_count when report is created."""
    if created and instance.status == ContentReport.PENDING:
        content = instance.content_object
        if content:
            # Count active reports (pending or reviewing)
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(content)
            active_count = ContentReport.objects.filter(
                content_type=ct,
                object_id=content.id,
                status__in=[ContentReport.PENDING, ContentReport.REVIEWING]
            ).count()

            # Update content object
            content.is_reported = active_count > 0
            content.report_count = active_count
            content.save(update_fields=['is_reported', 'report_count'])


@receiver(post_save, sender=ContentReport)
def update_report_flags_on_status_change(sender, instance, created, **kwargs):
    """Update is_reported and report_count when report status changes."""
    if not created:  # Only on updates
        content = instance.content_object
        if content:
            # Count active reports (pending or reviewing)
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(content)
            active_count = ContentReport.objects.filter(
                content_type=ct,
                object_id=content.id,
                status__in=[ContentReport.PENDING, ContentReport.REVIEWING]
            ).count()

            # Update content object
            content.is_reported = active_count > 0
            content.report_count = active_count
            content.save(update_fields=['is_reported', 'report_count'])


@receiver(post_delete, sender=ContentReport)
def update_report_flags_on_delete(sender, instance, **kwargs):
    """Update is_reported and report_count when report is deleted."""
    content = instance.content_object
    if content:
        # Count remaining active reports
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(content)
        active_count = ContentReport.objects.filter(
            content_type=ct,
            object_id=content.id,
            status__in=[ContentReport.PENDING, ContentReport.REVIEWING]
        ).count()

        # Update content object
        content.is_reported = active_count > 0
        content.report_count = active_count
        content.save(update_fields=['is_reported', 'report_count'])


# =============================================================================
# PHASE 2: PRAYER REQUEST SIGNALS
# =============================================================================

@receiver(post_save, sender=PrayerRequest)
def create_feed_item_for_prayer(sender, instance, created, **kwargs):
    """Create FeedItem when PrayerRequest is created."""
    if created:
        # Create feed item
        FeedItem.objects.create(
            group=instance.group,
            author=instance.author,
            content_type='prayer_request',
            content_id=instance.id,
            title=f"{'🔥 URGENT: ' if instance.urgency == PrayerRequest.URGENT else ''}{instance.title}",
            preview=instance.content[:300] +
            ('...' if len(instance.content) > 300 else ''),
            comment_count=instance.comment_count,
            reaction_count=0,  # Prayer requests don't have reactions directly
            is_pinned=instance.urgency == PrayerRequest.URGENT,  # Auto-pin urgent
            is_deleted=False,
        )


@receiver(post_save, sender=PrayerRequest)
def update_feed_item_for_prayer(sender, instance, created, **kwargs):
    """Update FeedItem when PrayerRequest is updated or answered."""
    if not created:
        # Get title prefix based on status
        if instance.is_answered:
            title_prefix = '✅ ANSWERED: '
        elif instance.urgency == PrayerRequest.URGENT:
            title_prefix = '🔥 URGENT: '
        else:
            title_prefix = ''

        # Update existing FeedItem
        FeedItem.objects.filter(
            content_type='prayer_request',
            content_id=instance.id
        ).update(
            title=f"{title_prefix}{instance.title}",
            preview=instance.content[:300] +
                ('...' if len(instance.content) > 300 else ''),
            comment_count=instance.comment_count,
            is_pinned=instance.urgency == PrayerRequest.URGENT and not instance.is_answered,
        )


@receiver(post_delete, sender=PrayerRequest)
def delete_feed_item_for_prayer(sender, instance, **kwargs):
    """Delete FeedItem when PrayerRequest is hard deleted."""
    FeedItem.objects.filter(
        content_type='prayer_request',
        content_id=instance.id
    ).delete()


# =============================================================================
# PHASE 2: TESTIMONY SIGNALS
# =============================================================================

@receiver(post_save, sender=Testimony)
def create_feed_item_for_testimony(sender, instance, created, **kwargs):
    """Create FeedItem when Testimony is created."""
    if created:
        # Determine title prefix
        title_prefix = '🌍 ' if instance.is_public else '📢 '

        FeedItem.objects.create(
            group=instance.group,
            author=instance.author,
            content_type='testimony',
            content_id=instance.id,
            title=f"{title_prefix}{instance.title}",
            preview=instance.content[:300] +
            ('...' if len(instance.content) > 300 else ''),
            comment_count=instance.comment_count,
            reaction_count=instance.reaction_count,
            is_pinned=False,
            is_deleted=False,
        )


@receiver(post_save, sender=Testimony)
def update_feed_item_for_testimony(sender, instance, created, **kwargs):
    """Update FeedItem when Testimony is updated or made public."""
    if not created:
        # Determine title prefix based on public status
        if instance.is_public and instance.is_public_approved:
            title_prefix = '🌍✓ '
        elif instance.is_public:
            title_prefix = '🌍 '
        else:
            title_prefix = '📢 '

        # Update existing FeedItem
        FeedItem.objects.filter(
            content_type='testimony',
            content_id=instance.id
        ).update(
            title=f"{title_prefix}{instance.title}",
            preview=instance.content[:300] +
                ('...' if len(instance.content) > 300 else ''),
            comment_count=instance.comment_count,
            reaction_count=instance.reaction_count,
        )


@receiver(post_delete, sender=Testimony)
def delete_feed_item_for_testimony(sender, instance, **kwargs):
    """Delete FeedItem when Testimony is hard deleted."""
    FeedItem.objects.filter(
        content_type='testimony',
        content_id=instance.id
    ).delete()


# =============================================================================
# PHASE 2: SCRIPTURE SIGNALS
# =============================================================================

@receiver(post_save, sender=Scripture)
def create_feed_item_for_scripture(sender, instance, created, **kwargs):
    """Create FeedItem when Scripture is created."""
    if created:
        FeedItem.objects.create(
            group=instance.group,
            author=instance.author,
            content_type='scripture',
            content_id=instance.id,
            title=f"📖 {instance.reference} ({instance.translation})",
            preview=(
                f"{instance.verse_text[:200]}..." if len(instance.verse_text) > 200
                else instance.verse_text
            ),
            comment_count=instance.comment_count,
            reaction_count=instance.reaction_count,
            is_pinned=False,
            is_deleted=False,
        )


@receiver(post_save, sender=Scripture)
def update_feed_item_for_scripture(sender, instance, created, **kwargs):
    """Update FeedItem when Scripture is updated."""
    if not created:
        # Update existing FeedItem
        FeedItem.objects.filter(
            content_type='scripture',
            content_id=instance.id
        ).update(
            title=f"📖 {instance.reference} ({instance.translation})",
            preview=(
                f"{instance.verse_text[:200]}..." if len(instance.verse_text) > 200
                else instance.verse_text
            ),
            comment_count=instance.comment_count,
            reaction_count=instance.reaction_count,
        )


@receiver(post_delete, sender=Scripture)
def delete_feed_item_for_scripture(sender, instance, **kwargs):
    """Delete FeedItem when Scripture is hard deleted."""
    FeedItem.objects.filter(
        content_type='scripture',
        content_id=instance.id
    ).delete()


# =============================================================================
# PHASE 2: COMMENT COUNT UPDATES FOR NEW CONTENT TYPES
# =============================================================================
# NOTE: Phase 2 content types (PrayerRequest, Testimony, Scripture) do not support
# direct comments. Comments are only on Discussions. Phase 2 content is wrapped
# in FeedItems which create associated Discussions for commenting.
# Comment counts for Phase 2 content should be tracked via their associated FeedItem's
# discussion, not directly on the Phase 2 models.
# These signals are disabled as they were incorrectly attempting to handle a use case
# that doesn't exist in the current architecture.

# @receiver(post_save, sender=Comment)
# def update_phase2_comment_counts(sender, instance, created, **kwargs):
#     ...implementation commented out...

# @receiver(post_delete, sender=Comment)
# def decrement_phase2_comment_counts(sender, instance, **kwargs):
#     ...implementation commented out...


# =============================================================================
# PHASE 2: REACTION COUNT UPDATES FOR NEW CONTENT TYPES
# =============================================================================

@receiver(post_save, sender=Reaction)
def update_phase2_reaction_counts(sender, instance, created, **kwargs):
    """Update reaction counts for Phase 2 content types."""
    if created:
        content = instance.content_object

        if isinstance(content, Testimony):
            content.reaction_count = Reaction.objects.filter(
                content_type__model='testimony',
                object_id=content.id
            ).count()
            content.save(update_fields=['reaction_count'])

            # Update FeedItem
            FeedItem.objects.filter(
                content_type='testimony',
                content_id=content.id
            ).update(reaction_count=content.reaction_count)

        elif isinstance(content, Scripture):
            content.reaction_count = Reaction.objects.filter(
                content_type__model='scripture',
                object_id=content.id
            ).count()
            content.save(update_fields=['reaction_count'])

            # Update FeedItem
            FeedItem.objects.filter(
                content_type='scripture',
                content_id=content.id
            ).update(reaction_count=content.reaction_count)


@receiver(post_delete, sender=Reaction)
def decrement_phase2_reaction_counts(sender, instance, **kwargs):
    """Decrement reaction counts for Phase 2 content types."""
    content = instance.content_object

    if isinstance(content, (Testimony, Scripture)):
        model_name = content.__class__.__name__.lower()
        content.reaction_count = Reaction.objects.filter(
            content_type__model=model_name,
            object_id=content.id
        ).count()
        content.save(update_fields=['reaction_count'])

        # Update FeedItem
        FeedItem.objects.filter(
            content_type=model_name,
            content_id=content.id
        ).update(reaction_count=content.reaction_count)


# =============================================================================
# PHASE 2: NOTIFICATION SIGNALS
# =============================================================================

@receiver(post_save, sender=PrayerRequest)
def send_prayer_request_notifications(sender, instance, created, **kwargs):
    """
    Send notifications when prayer request is created or answered.

    - New urgent prayers: Immediate notification to all group members
    - New regular prayers: Notification to all group members
    - Answered prayers: Notification to group members
    """
    from .services import notification_service

    if created:
        # New prayer request created
        if instance.urgency == PrayerRequest.URGENT:
            # Send urgent prayer notification immediately
            try:
                notification_service.send_urgent_prayer_notification(instance)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Failed to send urgent prayer notification: {str(e)}")
        else:
            # Send regular prayer notification
            try:
                notification_service.send_new_prayer_notification(instance)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Failed to send new prayer notification: {str(e)}")

    else:
        # Prayer request updated - check if just answered
        # Use update_fields to detect answer changes
        if instance.is_answered:
            # Check if this was just marked as answered (not already answered)
            old_instance = PrayerRequest.objects.filter(pk=instance.pk).first()
            if old_instance and not old_instance.is_answered:
                # Just marked as answered - send notification
                try:
                    notification_service.send_prayer_answered_notification(
                        instance)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(
                        f"Failed to send prayer answered notification: {str(e)}")


@receiver(post_save, sender=Testimony)
def send_testimony_notifications(sender, instance, created, **kwargs):
    """
    Send notifications when testimony is shared or approved.

    - New testimony: Notification to group members
    - Approved for public: Notification to testimony author
    """
    from .services import notification_service

    if created:
        # New testimony shared
        try:
            notification_service.send_testimony_shared_notification(instance)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to send testimony shared notification: {str(e)}")

    else:
        # Testimony updated - check if just approved for public
        if instance.is_public and instance.is_public_approved:
            # Check if this was just approved (not already approved)
            old_instance = Testimony.objects.filter(pk=instance.pk).first()
            if old_instance and not old_instance.is_public_approved:
                # Just approved - send notification to author
                try:
                    notification_service.send_testimony_approved_notification(
                        instance)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(
                        f"Failed to send testimony approved notification: {str(e)}")


@receiver(post_save, sender=Scripture)
def send_scripture_shared_notification(sender, instance, created, **kwargs):
    """
    Send notification when scripture is shared.

    Only sends for newly created scriptures (not updates).
    """
    from .services import notification_service

    if created:
        try:
            notification_service.send_scripture_shared_notification(instance)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to send scripture shared notification: {str(e)}")
