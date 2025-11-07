"""
Messaging models for Vineyard Group Fellowship.

This module contains models for group messaging functionality including:
- Discussions (group posts)
- Comments (threaded comments on discussions)
- Reactions (emoji reactions)
- Prayer Requests
- Testimonies
- Scripture Sharing
- FeedItem (denormalized feed for performance)
- CommentHistory (edit tracking)
- NotificationPreference (user notification settings)
- NotificationLog (notification tracking for compliance)

Phase 1 Models:
- Discussion, Comment, Reaction, FeedItem, CommentHistory
- NotificationPreference, NotificationLog

Phase 2 Models (to be added):
- PrayerRequest, Testimony, Scripture

Phase 3 Models (to be added):
- ContentFlag, Tag
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError
from django.db.models import F
from group.models import Group

User = get_user_model()


# =============================================================================
# PHASE 1: CORE MODELS
# =============================================================================

class Discussion(models.Model):
    """
    Discussion posts in a group.

    Only group leaders can create discussions.
    Discussions are the top-level content items in a group's feed.
    """

    CATEGORY_CHOICES = [
        ('bible_study', _('Bible Study')),
        ('prayer_worship', _('Prayer & Worship')),
        ('faith_discipleship', _('Faith & Discipleship')),
        ('testimonies', _('Testimonies')),
        ('general', _('General Discussion')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='discussions',
        help_text=_('The group this discussion belongs to')
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='discussions',
        help_text=_('User who created this discussion')
    )

    # Content
    title = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(5)],
        help_text=_('Discussion title (5-200 characters)')
    )
    content = models.TextField(
        validators=[MinLengthValidator(10)],
        help_text=_('Discussion content (min 10 characters)')
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='general',
        help_text=_('Discussion category')
    )

    # Denormalized counts (for performance)
    comment_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of comments (updated via signals)')
    )
    reaction_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of reactions (updated via signals)')
    )

    # Flags
    is_pinned = models.BooleanField(
        default=False,
        help_text=_('Pinned discussions appear at the top of the feed')
    )
    is_deleted = models.BooleanField(
        default=False,
        help_text=_('Soft delete flag')
    )

    # Moderation
    is_reported = models.BooleanField(
        default=False,
        help_text=_('True if content has been reported')
    )
    report_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of active reports')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'messaging_discussion'
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['group', '-created_at']),
            models.Index(fields=['group', 'is_deleted', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['category', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title} by {self.author.username} in {self.group.name}"

    def soft_delete(self):
        """Soft delete the discussion."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def increment_comment_count(self):
        """Atomically increment comment count."""
        Discussion.objects.filter(pk=self.pk).update(
            comment_count=F('comment_count') + 1)
        self.refresh_from_db(fields=['comment_count'])

    def decrement_comment_count(self):
        """Atomically decrement comment count."""
        Discussion.objects.filter(pk=self.pk).update(
            comment_count=F('comment_count') - 1)
        self.refresh_from_db(fields=['comment_count'])

    def increment_reaction_count(self):
        """Atomically increment reaction count."""
        Discussion.objects.filter(pk=self.pk).update(
            reaction_count=F('reaction_count') + 1)
        self.refresh_from_db(fields=['reaction_count'])

    def decrement_reaction_count(self):
        """Atomically decrement reaction count."""
        Discussion.objects.filter(pk=self.pk).update(
            reaction_count=F('reaction_count') - 1)
        self.refresh_from_db(fields=['reaction_count'])


class Comment(models.Model):
    """
    Comments on discussions.

    Supports threading (replies to comments) and edit tracking.
    Users can edit their own comments within 15 minutes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    discussion = models.ForeignKey(
        Discussion,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text=_('Discussion this comment belongs to')
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text=_('User who wrote this comment')
    )

    # Threading
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        help_text=_('Parent comment for threaded replies')
    )

    # Content
    content = models.TextField(
        validators=[MinLengthValidator(1)],
        help_text=_('Comment content')
    )

    # Denormalized counts
    reaction_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of reactions')
    )

    # Edit tracking
    is_edited = models.BooleanField(
        default=False,
        help_text=_('Whether this comment has been edited')
    )
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Last edit timestamp')
    )

    # Flags
    is_deleted = models.BooleanField(
        default=False,
        help_text=_('Soft delete flag')
    )

    # Moderation
    is_reported = models.BooleanField(
        default=False,
        help_text=_('True if content has been reported')
    )
    report_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of active reports')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'messaging_comment'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['discussion', '-created_at']),
            models.Index(fields=['discussion', 'is_deleted', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['parent', '-created_at']),
        ]

    def __str__(self):
        preview = self.content[:50]
        return f"Comment by {self.author.username}: {preview}..."

    def can_edit(self):
        """Check if comment can still be edited (within 15 minutes)."""
        if self.is_deleted:
            return False
        edit_window = timezone.timedelta(minutes=15)
        return timezone.now() - self.created_at < edit_window

    def soft_delete(self):
        """Soft delete the comment."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def increment_reaction_count(self):
        """Atomically increment reaction count."""
        Comment.objects.filter(pk=self.pk).update(
            reaction_count=F('reaction_count') + 1)
        self.refresh_from_db(fields=['reaction_count'])

    def decrement_reaction_count(self):
        """Atomically decrement reaction count."""
        Comment.objects.filter(pk=self.pk).update(
            reaction_count=F('reaction_count') - 1)
        self.refresh_from_db(fields=['reaction_count'])


class CommentHistory(models.Model):
    """
    Tracks edit history of comments.

    Every time a comment is edited, the previous version is saved here.
    This provides accountability and prevents abuse of edit functionality.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='edit_history',
        help_text=_('Comment that was edited')
    )

    # Content snapshot
    content = models.TextField(
        help_text=_('Comment content before edit')
    )

    # Metadata
    edited_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When this edit was made')
    )
    edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text=_('User who made the edit')
    )

    class Meta:
        db_table = 'messaging_comment_history'
        ordering = ['-edited_at']
        indexes = [
            models.Index(fields=['comment', '-edited_at']),
        ]
        verbose_name_plural = 'Comment histories'

    def __str__(self):
        return f"Edit of comment {self.comment.id} at {self.edited_at}"


class Reaction(models.Model):
    """
    Emoji reactions to discussions and comments.

    Each user can only react once per content item (enforced by unique constraint).
    Reactions are NOT soft-deleted - they are hard deleted.
    """

    REACTION_TYPES = [
        ('👍', _('Thumbs Up')),
        ('❤️', _('Heart')),
        ('🙏', _('Praying')),
        ('🔥', _('Fire')),
        ('👏', _('Clapping')),
        ('😊', _('Smile')),
        ('💯', _('100')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reactions',
        help_text=_('User who reacted')
    )

    # Polymorphic relationship (either discussion OR comment)
    discussion = models.ForeignKey(
        Discussion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reactions',
        help_text=_('Discussion being reacted to (if applicable)')
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reactions',
        help_text=_('Comment being reacted to (if applicable)')
    )

    # Reaction type
    reaction_type = models.CharField(
        max_length=10,
        choices=REACTION_TYPES,
        default='👍',
        help_text=_('Type of reaction')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messaging_reaction'
        constraints = [
            # Ensure one reaction per user per content item
            models.UniqueConstraint(
                fields=['user', 'discussion'],
                name='unique_user_discussion_reaction',
                condition=models.Q(discussion__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['user', 'comment'],
                name='unique_user_comment_reaction',
                condition=models.Q(comment__isnull=False)
            ),
            # Ensure reaction is for EITHER discussion OR comment, not both
            models.CheckConstraint(
                check=(
                    models.Q(discussion__isnull=False, comment__isnull=True) |
                    models.Q(discussion__isnull=True, comment__isnull=False)
                ),
                name='reaction_for_discussion_or_comment'
            ),
        ]
        indexes = [
            models.Index(fields=['discussion', 'reaction_type']),
            models.Index(fields=['comment', 'reaction_type']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        target = self.discussion or self.comment
        return f"{self.user.username} reacted {self.reaction_type} to {target}"

    def clean(self):
        """Validate that reaction is for either discussion or comment, not both."""
        if self.discussion and self.comment:
            raise ValidationError(
                'Reaction must be for either discussion or comment, not both.')
        if not self.discussion and not self.comment:
            raise ValidationError(
                'Reaction must be for either discussion or comment.')


class FeedItem(models.Model):
    """
    Denormalized feed for performance.

    This model consolidates all content types (Discussion, Prayer, Testimony, Scripture)
    into a single table for efficient feed queries. It's automatically populated via
    signals when content is created.

    CRITICAL: This prevents N+1 query problems and allows single-query feed fetching.
    """

    CONTENT_TYPES = [
        ('discussion', _('Discussion')),
        ('prayer', _('Prayer Request')),       # Phase 2
        ('testimony', _('Testimony')),          # Phase 2
        ('scripture', _('Scripture')),          # Phase 2
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='feed_items',
        help_text=_('Group this feed item belongs to')
    )

    # Content identification
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPES,
        help_text=_('Type of content')
    )
    content_id = models.UUIDField(
        help_text=_('ID of the actual content object')
    )

    # Denormalized data (for display without joins)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='feed_items',
        help_text=_('Author of the content')
    )
    title = models.CharField(
        max_length=500,
        help_text=_('Content title/preview')
    )
    preview = models.TextField(
        max_length=300,
        help_text=_('Content preview (first 300 chars)')
    )

    # Denormalized counts
    comment_count = models.PositiveIntegerField(default=0)
    reaction_count = models.PositiveIntegerField(default=0)

    # Flags
    is_pinned = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the content was created')
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messaging_feed_item'
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['group', 'is_deleted', '-created_at']),
            models.Index(fields=['group', 'content_type', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['content_type', 'content_id']),
        ]

    def __str__(self):
        return f"{self.content_type.title()}: {self.title}"

    @classmethod
    def create_from_discussion(cls, discussion):
        """Create FeedItem from Discussion."""
        preview = discussion.content[:300]
        if len(discussion.content) > 300:
            preview += '...'

        return cls.objects.create(
            group=discussion.group,
            content_type='discussion',
            content_id=discussion.id,
            author=discussion.author,
            title=discussion.title,
            preview=preview,
            comment_count=discussion.comment_count,
            reaction_count=discussion.reaction_count,
            is_pinned=discussion.is_pinned,
            is_deleted=discussion.is_deleted,
            created_at=discussion.created_at,
        )


class FeedItemView(models.Model):
    """
    Track which users have viewed which feed items.
    
    This enables "read/unread" status for feed items, helping users
    keep track of what they've already seen. Each record represents
    one user viewing one feed item.
    
    Features:
    - Per-user, per-item tracking
    - Timestamp of when viewed
    - Unique constraint prevents duplicate views
    - Efficient indexing for fast lookups
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feed_item = models.ForeignKey(
        FeedItem,
        on_delete=models.CASCADE,
        related_name='views',
        help_text=_('Feed item that was viewed')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='feed_item_views',
        help_text=_('User who viewed the item')
    )
    viewed_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the user viewed this item')
    )
    
    class Meta:
        db_table = 'messaging_feed_item_view'
        unique_together = [['feed_item', 'user']]
        indexes = [
            models.Index(fields=['user', '-viewed_at'], name='feed_view_user_time_idx'),
            models.Index(fields=['feed_item', 'user'], name='feed_view_item_user_idx'),
        ]
        ordering = ['-viewed_at']
    
    def __str__(self):
        return f"{self.user.email} viewed {self.feed_item.title} at {self.viewed_at}"


# =============================================================================
# NOTIFICATION MODELS (Phase 1 - Moved from Phase 3)
# =============================================================================

class NotificationPreference(models.Model):
    """
    User notification preferences.

    Controls when and how users receive email notifications.
    CRITICAL for GDPR compliance and CAN-SPAM Act.
    Moved to Phase 1 to prevent notification spam from day 1.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preference',
        help_text=_('User these preferences belong to')
    )

    # Email preferences
    email_enabled = models.BooleanField(
        default=True,
        help_text=_('Master switch for all email notifications')
    )
    email_new_discussion = models.BooleanField(
        default=True,
        help_text=_('Email when new discussion is posted')
    )
    email_new_comment = models.BooleanField(
        default=True,
        help_text=_('Email when someone comments on your post')
    )
    email_new_reaction = models.BooleanField(
        default=False,
        help_text=_('Email when someone reacts to your content')
    )

    # Phase 2: Faith Features Notifications
    email_urgent_prayer = models.BooleanField(
        default=True,
        help_text=_('Email for urgent prayer requests')
    )
    email_prayer_answered = models.BooleanField(
        default=True,
        help_text=_('Email when a prayer you prayed for is answered')
    )
    email_new_prayer = models.BooleanField(
        default=True,
        help_text=_('Email for new prayer requests in your groups')
    )
    email_testimony_shared = models.BooleanField(
        default=True,
        help_text=_('Email when new testimonies are shared')
    )
    email_testimony_approved = models.BooleanField(
        default=True,
        help_text=_('Email when your testimony is approved for public sharing')
    )
    email_scripture_shared = models.BooleanField(
        default=False,
        help_text=_('Email when scripture is shared in your groups')
    )

    # Quiet hours
    quiet_hours_enabled = models.BooleanField(
        default=True,
        help_text=_('Enable quiet hours (no emails during this time)')
    )
    quiet_hours_start = models.TimeField(
        default='22:00',
        help_text=_('Quiet hours start time (default: 10 PM)')
    )
    quiet_hours_end = models.TimeField(
        default='08:00',
        help_text=_('Quiet hours end time (default: 8 AM)')
    )

    # Unsubscribe token
    unsubscribe_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text=_('Token for one-click unsubscribe links')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messaging_notification_preference'

    def __str__(self):
        return f"Notification preferences for {self.user.username}"

    def is_in_quiet_hours(self):
        """Check if current time is within user's quiet hours."""
        if not self.quiet_hours_enabled:
            return False

        now = timezone.localtime().time()

        # Convert strings to time objects if needed
        from datetime import time as datetime_time
        if isinstance(self.quiet_hours_start, str):
            start = datetime_time.fromisoformat(self.quiet_hours_start)
        else:
            start = self.quiet_hours_start

        if isinstance(self.quiet_hours_end, str):
            end = datetime_time.fromisoformat(self.quiet_hours_end)
        else:
            end = self.quiet_hours_end

        # Handle quiet hours that span midnight
        if start < end:
            return start <= now < end
        else:
            return now >= start or now < end


class NotificationLog(models.Model):
    """
    Log of all notifications sent.

    Tracks every notification sent for:
    - Rate limiting (max 5 emails/hour per user)
    - Debugging
    - Compliance (GDPR, CAN-SPAM)
    - Analytics

    CRITICAL: Prevents notification spam and legal issues.
    """

    NOTIFICATION_TYPES = [
        ('new_discussion', _('New Discussion')),
        ('new_comment', _('New Comment')),
        ('new_reaction', _('New Reaction')),
        ('discussion_pinned', _('Discussion Pinned')),
        # Phase 2: Faith Features
        ('urgent_prayer', _('Urgent Prayer Request')),
        ('prayer_answered', _('Prayer Answered')),
        ('new_prayer', _('New Prayer Request')),
        ('testimony_shared', _('New Testimony')),
        ('testimony_approved', _('Testimony Approved for Public')),
        ('scripture_shared', _('New Scripture')),
    ]

    STATUS_CHOICES = [
        ('sent', _('Sent')),
        ('failed', _('Failed')),
        ('skipped_quiet_hours', _('Skipped - Quiet Hours')),
        ('skipped_rate_limit', _('Skipped - Rate Limit')),
        ('skipped_disabled', _('Skipped - Disabled')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_logs',
        help_text=_('User who received (or should have received) notification')
    )

    # Notification details
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        help_text=_('Type of notification')
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        help_text=_('Notification status')
    )

    # Email details
    to_email = models.EmailField(
        help_text=_('Email address notification was sent to')
    )
    subject = models.CharField(
        max_length=200,
        help_text=_('Email subject line')
    )

    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text=_('Error message if sending failed')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messaging_notification_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type} to {self.user.username} - {self.status}"

    @classmethod
    def count_recent_sends(cls, user, hours=1):
        """Count notifications sent to user in last N hours."""
        since = timezone.now() - timezone.timedelta(hours=hours)
        return cls.objects.filter(
            user=user,
            status='sent',
            created_at__gte=since
        ).count()


# =============================================================================
# CONTENT MODERATION
# =============================================================================

class ContentReport(models.Model):
    """
    Reports of inappropriate content for moderation.

    Members can flag discussions or comments for review by group leaders.
    Leaders can then review and take action (resolve or dismiss).
    """

    # Report reasons
    SPAM = 'spam'
    INAPPROPRIATE = 'inappropriate'
    HARASSMENT = 'harassment'
    OFF_TOPIC = 'off_topic'
    FALSE_INFORMATION = 'false_info'
    OTHER = 'other'

    REASON_CHOICES = [
        (SPAM, _('Spam or advertising')),
        (INAPPROPRIATE, _('Inappropriate content')),
        (HARASSMENT, _('Harassment or bullying')),
        (OFF_TOPIC, _('Off-topic or not faith-related')),
        (FALSE_INFORMATION, _('False or misleading information')),
        (OTHER, _('Other (see details)')),
    ]

    # Report status
    PENDING = 'pending'
    REVIEWING = 'reviewing'
    RESOLVED = 'resolved'
    DISMISSED = 'dismissed'

    STATUS_CHOICES = [
        (PENDING, _('Pending review')),
        (REVIEWING, _('Under review')),
        (RESOLVED, _('Resolved (action taken)')),
        (DISMISSED, _('Dismissed (no action needed)')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Reporter
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='content_reports',
        help_text=_('User who reported the content')
    )

    # Reported content (generic to support both discussions and comments)
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.contrib.contenttypes.models import ContentType

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ['discussion', 'comment']},
        help_text=_('Type of content being reported')
    )
    object_id = models.UUIDField(
        help_text=_('ID of the reported content')
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    # Report details
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        help_text=_('Reason for reporting')
    )
    details = models.TextField(
        blank=True,
        max_length=500,
        help_text=_('Additional details about the report')
    )

    # Review tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        help_text=_('Current status of the report')
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_reports',
        help_text=_('Group leader who reviewed this report')
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the report was reviewed')
    )
    review_notes = models.TextField(
        blank=True,
        max_length=500,
        help_text=_('Notes from the reviewer')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messaging_content_report'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['reporter', '-created_at']),
            models.Index(fields=['reviewed_by', '-created_at']),
        ]
        # Prevent duplicate reports from same user on same content
        constraints = [
            models.UniqueConstraint(
                fields=['reporter', 'content_type', 'object_id'],
                name='unique_report_per_user_per_content'
            )
        ]

    def __str__(self):
        return f"Report by {self.reporter.username} - {self.get_reason_display()} ({self.status})"

    def resolve(self, reviewed_by, notes=''):
        """Mark report as resolved."""
        self.status = self.RESOLVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()

    def dismiss(self, reviewed_by, notes=''):
        """Mark report as dismissed."""
        self.status = self.DISMISSED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()

    @property
    def group(self):
        """Get the group this report belongs to."""
        if hasattr(self.content_object, 'group'):
            return self.content_object.group
        elif hasattr(self.content_object, 'discussion'):
            return self.content_object.discussion.group
        return None


# =============================================================================
# PHASE 2: FAITH FEATURES
# =============================================================================

class PrayerRequest(models.Model):
    """
    Prayer requests shared within a group.

    Members can share prayer needs and track answered prayers.
    Supports urgency levels for time-sensitive requests.
    """

    # Urgency levels
    NORMAL = 'normal'
    URGENT = 'urgent'

    URGENCY_CHOICES = [
        (NORMAL, _('Normal')),
        (URGENT, _('Urgent')),
    ]

    # Prayer categories
    PERSONAL = 'personal'
    FAMILY = 'family'
    COMMUNITY = 'community'
    THANKSGIVING = 'thanksgiving'

    CATEGORY_CHOICES = [
        (PERSONAL, _('Personal')),
        (FAMILY, _('Family')),
        (COMMUNITY, _('Community')),
        (THANKSGIVING, _('Thanksgiving/Praise')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='prayer_requests',
        help_text=_('Group this prayer request belongs to')
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prayer_requests',
        help_text=_('User who created this prayer request')
    )

    # Prayer details
    title = models.CharField(
        max_length=200,
        help_text=_('Brief prayer request title')
    )
    content = models.TextField(
        max_length=1000,
        validators=[MinLengthValidator(10)],
        help_text=_('Detailed prayer request (max 1000 characters)')
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=PERSONAL,
        help_text=_('Category of prayer request')
    )
    urgency = models.CharField(
        max_length=10,
        choices=URGENCY_CHOICES,
        default=NORMAL,
        help_text=_('Urgency level')
    )

    # Answer tracking
    is_answered = models.BooleanField(
        default=False,
        help_text=_('Whether this prayer has been answered')
    )
    answered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the prayer was answered')
    )
    answer_description = models.TextField(
        blank=True,
        max_length=1000,
        help_text=_('Description of how prayer was answered')
    )

    # Engagement counts
    prayer_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of people praying')
    )
    comment_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of comments')
    )

    # Moderation
    is_reported = models.BooleanField(
        default=False,
        help_text=_('True if content has been reported')
    )
    report_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of active reports')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messaging_prayer_request'
        ordering = ['-urgency', '-created_at']  # Urgent first, then newest
        indexes = [
            models.Index(fields=['group', '-created_at']),
            models.Index(fields=['group', 'urgency', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['is_answered', '-created_at']),
        ]

    def __str__(self):
        urgency_icon = '🔥' if self.urgency == self.URGENT else '🙏'
        return f"{urgency_icon} {self.title} by {self.author.username}"

    def mark_answered(self, answer_description=''):
        """Mark prayer request as answered."""
        self.is_answered = True
        self.answered_at = timezone.now()
        self.answer_description = answer_description
        self.save(update_fields=['is_answered',
                  'answered_at', 'answer_description'])

    def increment_prayer_count(self):
        """Atomically increment prayer count."""
        PrayerRequest.objects.filter(pk=self.pk).update(
            prayer_count=F('prayer_count') + 1)
        self.refresh_from_db(fields=['prayer_count'])


class Testimony(models.Model):
    """
    Testimonies of God's faithfulness and answered prayers.

    Can be linked to answered prayer requests.
    Optionally shared publicly beyond the group.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='testimonies',
        help_text=_('Group this testimony belongs to')
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='testimonies',
        help_text=_('User who shared this testimony')
    )

    # Testimony content
    title = models.CharField(
        max_length=200,
        help_text=_('Testimony title')
    )
    content = models.TextField(
        max_length=2000,
        validators=[MinLengthValidator(20)],
        help_text=_('Full testimony (max 2000 characters)')
    )

    # Link to answered prayer (optional)
    answered_prayer = models.ForeignKey(
        PrayerRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonies',
        help_text=_('Link to answered prayer request')
    )

    # Public sharing
    is_public = models.BooleanField(
        default=False,
        help_text=_('Share publicly to inspire others')
    )
    public_shared_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When testimony was shared publicly')
    )
    is_public_approved = models.BooleanField(
        default=False,
        help_text=_('Leader approval for public sharing')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_testimonies',
        help_text=_('Leader who approved public sharing')
    )

    # Engagement counts
    reaction_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of reactions')
    )
    comment_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of comments')
    )

    # Moderation
    is_reported = models.BooleanField(
        default=False,
        help_text=_('True if content has been reported')
    )
    report_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of active reports')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messaging_testimony'
        verbose_name_plural = 'testimonies'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['group', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(
                fields=['is_public', 'is_public_approved', '-created_at']),
            models.Index(fields=['answered_prayer', '-created_at']),
        ]

    def __str__(self):
        public_icon = '🌍' if self.is_public else '👥'
        return f"{public_icon} {self.title} by {self.author.username}"

    def share_publicly(self, approved_by=None):
        """Share testimony publicly."""
        self.is_public = True
        self.public_shared_at = timezone.now()
        if approved_by:
            self.is_public_approved = True
            self.approved_by = approved_by
        self.save(update_fields=[
                  'is_public', 'public_shared_at', 'is_public_approved', 'approved_by'])


class Scripture(models.Model):
    """
    Bible scripture sharing with personal reflections.

    Supports automated verse lookup via Bible API or manual entry.
    """

    # Scripture sources
    API = 'api'
    MANUAL = 'manual'

    SOURCE_CHOICES = [
        (API, _('Bible API')),
        (MANUAL, _('Manual Entry')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='scriptures',
        help_text=_('Group this scripture share belongs to')
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='scriptures',
        help_text=_('User who shared this scripture')
    )

    # Scripture details
    reference = models.CharField(
        max_length=100,
        help_text=_('Bible reference (e.g., "John 3:16", "Psalm 23:1-6")')
    )
    verse_text = models.TextField(
        help_text=_('Full scripture text')
    )
    translation = models.CharField(
        max_length=20,
        default='KJV',
        help_text=_('Bible translation (KJV, NIV, ESV, etc.)')
    )

    # Personal reflection
    personal_reflection = models.TextField(
        blank=True,
        max_length=1000,
        help_text=_('Personal thoughts and application')
    )

    # Source tracking
    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default=API,
        help_text=_('How the verse was added')
    )

    # Engagement counts
    reaction_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of reactions')
    )
    comment_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of comments')
    )

    # Moderation
    is_reported = models.BooleanField(
        default=False,
        help_text=_('True if content has been reported')
    )
    report_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of active reports')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messaging_scripture'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['group', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['reference']),
            models.Index(fields=['translation', '-created_at']),
        ]

    def __str__(self):
        return f"📖 {self.reference} shared by {self.author.username}"
