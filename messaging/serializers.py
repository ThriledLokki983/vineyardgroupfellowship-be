"""
Serializers for messaging app.

Handles serialization/deserialization of messaging models for the API.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    Discussion,
    Comment,
    CommentHistory,
    Reaction,
    FeedItem,
    NotificationPreference,
    NotificationLog,
    ContentReport,
    PrayerRequest,
    Testimony,
    Scripture,
)
from group.models import Group

User = get_user_model()


# =============================================================================
# USER SERIALIZER (minimal, for nested display)
# =============================================================================

class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for nested serialization."""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = fields


# =============================================================================
# DISCUSSION SERIALIZERS
# =============================================================================

class DiscussionListSerializer(serializers.ModelSerializer):
    """
    List serializer for discussions (lightweight for feed).
    """
    author = UserMinimalSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Discussion
        fields = [
            'id',
            'group',
            'group_name',
            'author',
            'title',
            'content',
            'category',
            'comment_count',
            'reaction_count',
            'is_pinned',
            'is_deleted',
            'created_at',
            'updated_at',
            'can_edit',
            'can_delete',
        ]
        read_only_fields = [
            'id',
            'author',
            'comment_count',
            'reaction_count',
            'is_deleted',
            'created_at',
            'updated_at',
        ]

    def get_can_edit(self, obj):
        """Check if current user can edit this discussion."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # Author can edit their own discussion
        return obj.author == request.user

    def get_can_delete(self, obj):
        """Check if current user can delete this discussion."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # Author or group leader can delete
        is_author = obj.author == request.user
        # TODO: Add is_group_leader check when we have membership model
        return is_author


class DiscussionDetailSerializer(serializers.ModelSerializer):
    """
    Detail serializer for discussions (includes more info).
    """
    author = UserMinimalSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Discussion
        fields = [
            'id',
            'group',
            'group_name',
            'author',
            'title',
            'content',
            'category',
            'comment_count',
            'reaction_count',
            'is_pinned',
            'is_deleted',
            'created_at',
            'updated_at',
            'deleted_at',
            'can_edit',
            'can_delete',
        ]
        read_only_fields = [
            'id',
            'author',
            'comment_count',
            'reaction_count',
            'is_deleted',
            'created_at',
            'updated_at',
            'deleted_at',
        ]

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user

    def get_can_delete(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user

    def validate_title(self, value):
        """Validate title length."""
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Title must be at least 5 characters long.")
        return value.strip()

    def validate_content(self, value):
        """Validate content length."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Content must be at least 10 characters long.")
        return value.strip()


class DiscussionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating discussions.
    """

    class Meta:
        model = Discussion
        fields = [
            'group',
            'title',
            'content',
            'category',
        ]

    def validate_title(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Title must be at least 5 characters long.")
        return value.strip()

    def validate_content(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Content must be at least 10 characters long.")
        return value.strip()

    def create(self, validated_data):
        """Create discussion with current user as author."""
        request = self.context.get('request')
        validated_data['author'] = request.user
        return super().create(validated_data)


# =============================================================================
# COMMENT SERIALIZERS
# =============================================================================

class CommentSerializer(serializers.ModelSerializer):
    """
    Serializer for comments (supports threading and polymorphic content).
    """
    author = UserMinimalSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    edit_time_remaining = serializers.SerializerMethodField()
    content_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            'content_type',
            'content_id',
            'content_type_name',
            'discussion',  # Legacy field for backward compatibility
            'author',
            'parent',
            'content',
            'reaction_count',
            'is_edited',
            'edited_at',
            'is_deleted',
            'created_at',
            'updated_at',
            'replies',
            'can_edit',
            'can_delete',
            'edit_time_remaining',
        ]
        read_only_fields = [
            'id',
            'author',
            'reaction_count',
            'is_edited',
            'edited_at',
            'is_deleted',
            'created_at',
            'updated_at',
            'content_type_name',
        ]

    def get_content_type_name(self, obj):
        """Return human-readable content type name."""
        if obj.content_type:
            return obj.content_type.model
        return 'discussion'  # Default for legacy comments

    def get_replies(self, obj):
        """Get nested replies (1 level deep to avoid infinite recursion)."""
        if obj.replies.exists():
            # Only show non-deleted replies
            replies = obj.replies.filter(is_deleted=False)
            # Avoid infinite recursion by using a simplified serializer
            return CommentSimpleSerializer(replies, many=True, context=self.context).data
        return []

    def get_can_edit(self, obj):
        """Check if current user can edit this comment."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if obj.author != request.user:
            return False
        return obj.can_edit()  # Checks 15-minute window

    def get_can_delete(self, obj):
        """Check if current user can delete this comment."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # Author or group leader can delete
        return obj.author == request.user

    def get_edit_time_remaining(self, obj):
        """Get seconds remaining in edit window."""
        if obj.is_deleted:
            return 0
        edit_window = timezone.timedelta(minutes=15)
        elapsed = timezone.now() - obj.created_at
        remaining = edit_window - elapsed
        return max(0, int(remaining.total_seconds()))

    def validate_content(self, value):
        """Validate content is not empty."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Content cannot be empty.")
        return value.strip()

    def create(self, validated_data):
        """Create comment with current user as author."""
        request = self.context.get('request')
        validated_data['author'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update comment (edit functionality)."""
        # Check edit window
        if not instance.can_edit():
            raise serializers.ValidationError(
                "Edit window has expired (15 minutes).")

        # Update content
        instance.content = validated_data.get('content', instance.content)
        instance.is_edited = True
        instance.edited_at = timezone.now()
        instance.save()

        return instance


class CommentSimpleSerializer(serializers.ModelSerializer):
    """
    Simplified comment serializer (for nested replies, no recursion).
    """
    author = UserMinimalSerializer(read_only=True)
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            'author',
            'parent',  # Include parent to show if this is a reply
            'content',
            'reaction_count',
            'is_edited',
            'created_at',
            'can_edit',
        ]
        read_only_fields = fields

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if obj.author != request.user:
            return False
        return obj.can_edit()


class CommentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating comments (supports polymorphic content).
    Accepts either:
    - discussion (legacy) OR
    - content_type + content_id (new polymorphic approach)
    """
    scripture = serializers.UUIDField(write_only=True, required=False)
    prayer = serializers.UUIDField(write_only=True, required=False)
    testimony = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Comment
        fields = ['discussion', 'scripture', 'prayer', 'testimony',
                  'content_type', 'content_id', 'parent', 'content']

    def validate_content(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Content cannot be empty.")
        return value.strip()

    def validate(self, data):
        """
        Validate that either:
        1. discussion is provided (legacy), OR
        2. content_type + content_id are provided, OR
        3. One of the shorthand fields (scripture, prayer, testimony) is provided
        """
        from django.contrib.contenttypes.models import ContentType
        from messaging.models import Scripture, PrayerRequest, Testimony, Discussion

        # Count how many content identifiers are provided
        content_identifiers = [
            data.get('discussion'),
            data.get('scripture'),
            data.get('prayer'),
            data.get('testimony'),
            data.get('content_type') and data.get('content_id')
        ]
        provided_count = sum(1 for x in content_identifiers if x)

        if provided_count == 0:
            raise serializers.ValidationError(
                "Must provide either discussion, scripture, prayer, testimony, or content_type+content_id"
            )

        if provided_count > 1:
            raise serializers.ValidationError(
                "Can only comment on one content item at a time"
            )

        # Handle shorthand fields by converting to content_type + content_id
        if data.get('scripture'):
            data['content_type'] = ContentType.objects.get_for_model(Scripture)
            data['content_id'] = data.pop('scripture')
        elif data.get('prayer'):
            data['content_type'] = ContentType.objects.get_for_model(Prayer)
            data['content_id'] = data.pop('prayer')
        elif data.get('testimony'):
            data['content_type'] = ContentType.objects.get_for_model(Testimony)
            data['content_id'] = data.pop('testimony')
        elif data.get('discussion'):
            # For backward compatibility, set content_type/content_id from discussion
            data['content_type'] = ContentType.objects.get_for_model(
                Discussion)
            data['content_id'] = data['discussion'].id

        # Validate parent belongs to same content
        if data.get('parent'):
            parent = data['parent']
            if parent.content_type != data.get('content_type') or parent.content_id != data.get('content_id'):
                raise serializers.ValidationError(
                    "Parent comment must belong to the same content item."
                )

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['author'] = request.user
        return super().create(validated_data)


# =============================================================================
# COMMENT HISTORY SERIALIZER
# =============================================================================

class CommentHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for comment edit history.
    """
    edited_by = UserMinimalSerializer(read_only=True)

    class Meta:
        model = CommentHistory
        fields = [
            'id',
            'comment',
            'content',
            'edited_at',
            'edited_by',
        ]
        read_only_fields = fields


# =============================================================================
# REACTION SERIALIZERS
# =============================================================================

class ReactionSerializer(serializers.ModelSerializer):
    """
    Serializer for reactions.

    Supports reactions on all content types via GenericForeignKey:
    - Discussion
    - Comment
    - PrayerRequest
    - Testimony
    - Scripture
    """
    user = UserMinimalSerializer(read_only=True)
    content_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Reaction
        fields = [
            'id',
            'user',
            'content_type',
            'object_id',
            'content_type_name',
            'reaction_type',
            'created_at',
            # Legacy fields (deprecated but kept for backward compatibility)
            'discussion',
            'comment',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'content_type_name']

    def get_content_type_name(self, obj):
        """Get human-readable content type name."""
        return obj.content_type.model if obj.content_type else None

    def validate(self, data):
        """Validate reaction has valid content_type and object_id."""
        if not data.get('content_type') or not data.get('object_id'):
            raise serializers.ValidationError(
                "Both content_type and object_id are required.")
        return data

    def create(self, validated_data):
        """Create reaction with current user."""
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class ReactionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating reactions.

    Accepts content_type and object_id for GenericForeignKey support.
    Supports all content types: Discussion, Comment, PrayerRequest, Testimony, Scripture.
    """

    class Meta:
        model = Reaction
        fields = ['content_type', 'object_id', 'reaction_type']

    def validate(self, data):
        """Validate content_type and object_id."""
        from django.contrib.contenttypes.models import ContentType

        if not data.get('content_type') or not data.get('object_id'):
            raise serializers.ValidationError(
                "Both content_type and object_id are required.")

        # Validate content type is allowed
        content_type = data.get('content_type')
        allowed_models = ['discussion', 'comment',
                          'prayerrequest', 'testimony', 'scripture']
        if content_type.model not in allowed_models:
            raise serializers.ValidationError(
                f"Invalid content type. Must be one of: {', '.join(allowed_models)}")

        # Validate object exists
        model_class = content_type.model_class()
        if not model_class.objects.filter(pk=data.get('object_id')).exists():
            raise serializers.ValidationError("Content object does not exist.")

        return data

    def create(self, validated_data):
        """Create reaction with current user."""
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


# =============================================================================
# FEEDITEM SERIALIZER
# =============================================================================

class FeedItemSerializer(serializers.ModelSerializer):
    """
    Serializer for feed items (read-only, auto-populated).

    Includes 'has_viewed' field to indicate if current user has viewed the item.
    This field uses prefetch_related optimization to avoid N+1 queries.
    """
    author = UserMinimalSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    has_viewed = serializers.SerializerMethodField()

    class Meta:
        model = FeedItem
        fields = [
            'id',
            'group',
            'group_name',
            'content_type',
            'content_id',
            'author',
            'title',
            'preview',
            'comment_count',
            'reaction_count',
            'is_pinned',
            'is_deleted',
            'has_viewed',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_has_viewed(self, obj):
        """
        Check if current user has viewed this feed item.

        Uses prefetched 'user_views' attribute to avoid N+1 queries.
        The viewset should prefetch views for the current user.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        # Check if we have prefetched views (optimization)
        if hasattr(obj, 'user_views'):
            # user_views is prefetched and filtered for current user
            return len(obj.user_views) > 0

        # Fallback: direct query (less efficient)
        return obj.views.filter(user=request.user).exists()


# =============================================================================
# NOTIFICATION SERIALIZERS
# =============================================================================

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for notification preferences.
    """

    class Meta:
        model = NotificationPreference
        fields = [
            'id',
            'user',
            'email_enabled',
            'email_new_discussion',
            'email_new_comment',
            'email_new_reaction',
            'email_urgent_prayer',
            'quiet_hours_enabled',
            'quiet_hours_start',
            'quiet_hours_end',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    """
    Serializer for notification logs (read-only).
    """
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            'id',
            'user',
            'notification_type',
            'status',
            'to_email',
            'subject',
            'error_message',
            'created_at',
        ]
        read_only_fields = fields


# =============================================================================
# CONTENT REPORT SERIALIZERS
# =============================================================================

class ContentReportCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating content reports.

    Users can report discussions or comments for moderation.
    """

    class Meta:
        model = ContentReport
        fields = [
            'id',
            'content_type',
            'object_id',
            'reason',
            'details',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        """Validate that content exists and user hasn't already reported it."""
        from django.contrib.contenttypes.models import ContentType

        content_type = data.get('content_type')
        object_id = data.get('object_id')
        reporter = self.context['request'].user

        # Check if content exists
        try:
            model_class = content_type.model_class()
            content = model_class.objects.get(id=object_id)
        except model_class.DoesNotExist:
            raise serializers.ValidationError("Content not found.")

        # Check for duplicate report
        existing = ContentReport.objects.filter(
            reporter=reporter,
            content_type=content_type,
            object_id=object_id
        ).first()

        if existing:
            raise serializers.ValidationError(
                "You have already reported this content."
            )

        return data

    def create(self, validated_data):
        """Create report with current user as reporter."""
        validated_data['reporter'] = self.context['request'].user
        return super().create(validated_data)


class ContentReportSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for viewing content reports (moderators).
    """
    reporter = UserMinimalSerializer(read_only=True)
    reviewed_by = UserMinimalSerializer(read_only=True)
    content_preview = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField()

    class Meta:
        model = ContentReport
        fields = [
            'id',
            'reporter',
            'content_type',
            'object_id',
            'content_preview',
            'group_id',
            'reason',
            'details',
            'status',
            'reviewed_by',
            'reviewed_at',
            'review_notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'reporter',
            'content_type',
            'object_id',
            'created_at',
            'updated_at',
        ]

    def get_content_preview(self, obj):
        """Get preview of reported content."""
        content = obj.content_object
        if not content:
            return "[Content deleted]"

        if isinstance(content, Discussion):
            return {
                'type': 'discussion',
                'title': content.title,
                'preview': content.content[:200] + '...' if len(content.content) > 200 else content.content,
                'author': content.author.username,
            }
        elif isinstance(content, Comment):
            return {
                'type': 'comment',
                'content': content.content[:200] + '...' if len(content.content) > 200 else content.content,
                'author': content.author.username,
                'discussion_title': content.discussion.title,
            }
        return None

    def get_group_id(self, obj):
        """Get the group ID for filtering."""
        return str(obj.group.id) if obj.group else None


class ContentReportReviewSerializer(serializers.Serializer):
    """
    Serializer for reviewing reports (resolve/dismiss actions).
    """
    action = serializers.ChoiceField(
        choices=['resolve', 'dismiss'],
        help_text="Action to take on the report"
    )
    notes = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional notes about the decision"
    )


# =============================================================================
# PHASE 2: PRAYER REQUEST SERIALIZERS
# =============================================================================

class PrayerRequestListSerializer(serializers.ModelSerializer):
    """List serializer for prayer requests (lightweight for feed)."""

    author = UserMinimalSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_mark_answered = serializers.SerializerMethodField()
    is_praying = serializers.SerializerMethodField()

    class Meta:
        model = PrayerRequest
        fields = [
            'id',
            'group',
            'group_name',
            'author',
            'title',
            'content',
            'category',
            'urgency',
            'is_answered',
            'answered_at',
            'prayer_count',
            'comment_count',
            'is_reported',
            'created_at',
            'updated_at',
            'can_edit',
            'can_mark_answered',
            'is_praying',
        ]
        read_only_fields = [
            'id',
            'author',
            'prayer_count',
            'comment_count',
            'is_reported',
            'answered_at',
            'created_at',
            'updated_at',
        ]

    def get_can_edit(self, obj):
        """Check if current user can edit this prayer request."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user

    def get_can_mark_answered(self, obj):
        """Check if current user can mark this prayer as answered."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # Only author can mark as answered
        return obj.author == request.user and not obj.is_answered

    def get_is_praying(self, obj):
        """Check if current user is praying for this request."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # TODO: Implement when we add prayer tracking
        return False


class PrayerRequestDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for prayer requests with full information."""

    author = UserMinimalSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_mark_answered = serializers.SerializerMethodField()
    is_praying = serializers.SerializerMethodField()

    class Meta:
        model = PrayerRequest
        fields = [
            'id',
            'group',
            'group_name',
            'author',
            'title',
            'content',
            'category',
            'urgency',
            'is_answered',
            'answered_at',
            'answer_description',
            'prayer_count',
            'comment_count',
            'is_reported',
            'report_count',
            'created_at',
            'updated_at',
            'can_edit',
            'can_mark_answered',
            'is_praying',
        ]
        read_only_fields = [
            'id',
            'author',
            'prayer_count',
            'comment_count',
            'is_reported',
            'report_count',
            'answered_at',
            'created_at',
            'updated_at',
        ]

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user

    def get_can_mark_answered(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user and not obj.is_answered

    def get_is_praying(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return False


class PrayerRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating prayer requests."""

    class Meta:
        model = PrayerRequest
        fields = [
            'group',
            'title',
            'content',
            'category',
            'urgency',
        ]

    def validate_title(self, value):
        """Validate title length."""
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Title must be at least 5 characters long."
            )
        return value.strip()

    def validate_content(self, value):
        """Validate content length."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Prayer request must be at least 10 characters long."
            )
        if len(value) > 1000:
            raise serializers.ValidationError(
                "Prayer request cannot exceed 1000 characters."
            )
        return value.strip()

    def create(self, validated_data):
        """Create prayer request with current user as author."""
        request = self.context.get('request')
        validated_data['author'] = request.user
        return super().create(validated_data)


class PrayerRequestAnswerSerializer(serializers.Serializer):
    """Serializer for marking prayer as answered."""

    answer_description = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text="Description of how the prayer was answered"
    )


# =============================================================================
# PHASE 2: TESTIMONY SERIALIZERS
# =============================================================================

class TestimonyListSerializer(serializers.ModelSerializer):
    """List serializer for testimonies (lightweight for feed)."""

    author = UserMinimalSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    answered_prayer_title = serializers.CharField(
        source='answered_prayer.title',
        read_only=True
    )
    can_edit = serializers.SerializerMethodField()
    can_share_public = serializers.SerializerMethodField()

    class Meta:
        model = Testimony
        fields = [
            'id',
            'group',
            'group_name',
            'author',
            'title',
            'content',
            'answered_prayer',
            'answered_prayer_title',
            'is_public',
            'is_public_approved',
            'reaction_count',
            'comment_count',
            'is_reported',
            'created_at',
            'updated_at',
            'can_edit',
            'can_share_public',
        ]
        read_only_fields = [
            'id',
            'author',
            'reaction_count',
            'comment_count',
            'is_reported',
            'is_public_approved',
            'created_at',
            'updated_at',
        ]

    def get_can_edit(self, obj):
        """Check if current user can edit this testimony."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user

    def get_can_share_public(self, obj):
        """Check if current user can share this publicly."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user and not obj.is_public


class TestimonyDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for testimonies with full information."""

    author = UserMinimalSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    answered_prayer_details = PrayerRequestListSerializer(
        source='answered_prayer',
        read_only=True
    )
    approved_by_user = UserMinimalSerializer(
        source='approved_by',
        read_only=True
    )
    can_edit = serializers.SerializerMethodField()
    can_share_public = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()

    class Meta:
        model = Testimony
        fields = [
            'id',
            'group',
            'group_name',
            'author',
            'title',
            'content',
            'answered_prayer',
            'answered_prayer_details',
            'is_public',
            'public_shared_at',
            'is_public_approved',
            'approved_by',
            'approved_by_user',
            'reaction_count',
            'comment_count',
            'is_reported',
            'report_count',
            'created_at',
            'updated_at',
            'can_edit',
            'can_share_public',
            'can_approve',
        ]
        read_only_fields = [
            'id',
            'author',
            'reaction_count',
            'comment_count',
            'is_reported',
            'report_count',
            'public_shared_at',
            'is_public_approved',
            'approved_by',
            'created_at',
            'updated_at',
        ]

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user

    def get_can_share_public(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user and not obj.is_public

    def get_can_approve(self, obj):
        """Check if current user can approve public sharing."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # TODO: Add is_group_leader check when we have membership model
        return obj.is_public and not obj.is_public_approved


class TestimonyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating testimonies."""

    class Meta:
        model = Testimony
        fields = [
            'group',
            'title',
            'content',
            'answered_prayer',
            'is_public',
        ]

    def validate_title(self, value):
        """Validate title length."""
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Title must be at least 5 characters long."
            )
        return value.strip()

    def validate_content(self, value):
        """Validate content length."""
        if len(value.strip()) < 20:
            raise serializers.ValidationError(
                "Testimony must be at least 20 characters long."
            )
        if len(value) > 2000:
            raise serializers.ValidationError(
                "Testimony cannot exceed 2000 characters."
            )
        return value.strip()

    def validate_answered_prayer(self, value):
        """Validate answered prayer link."""
        if value and not value.is_answered:
            raise serializers.ValidationError(
                "Can only link to answered prayer requests."
            )
        return value

    def create(self, validated_data):
        """Create testimony with current user as author."""
        request = self.context.get('request')
        validated_data['author'] = request.user
        return super().create(validated_data)


class TestimonyPublicShareSerializer(serializers.Serializer):
    """Serializer for sharing testimony publicly."""

    confirm = serializers.BooleanField(
        required=True,
        help_text="Confirm you want to share this publicly"
    )

    def validate_confirm(self, value):
        """Ensure confirmation is True."""
        if not value:
            raise serializers.ValidationError(
                "You must confirm to share publicly."
            )
        return value


# =============================================================================
# PHASE 2: SCRIPTURE SERIALIZERS
# =============================================================================

class ScriptureListSerializer(serializers.ModelSerializer):
    """List serializer for scriptures (lightweight for feed)."""

    author = UserMinimalSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    has_reflection = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Scripture
        fields = [
            'id',
            'group',
            'group_name',
            'author',
            'reference',
            'verse_text',
            'translation',
            'has_reflection',
            'source',
            'reaction_count',
            'comment_count',
            'is_reported',
            'created_at',
            'updated_at',
            'can_edit',
        ]
        read_only_fields = [
            'id',
            'author',
            'reaction_count',
            'comment_count',
            'is_reported',
            'source',
            'created_at',
            'updated_at',
        ]

    def get_has_reflection(self, obj):
        """Check if scripture has personal reflection."""
        return bool(obj.personal_reflection)

    def get_can_edit(self, obj):
        """Check if current user can edit this scripture."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user


class ScriptureDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for scriptures with full information."""

    author = UserMinimalSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    has_reflection = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Scripture
        fields = [
            'id',
            'group',
            'group_name',
            'author',
            'reference',
            'verse_text',
            'translation',
            'personal_reflection',
            'source',
            'reaction_count',
            'comment_count',
            'is_reported',
            'report_count',
            'created_at',
            'updated_at',
            'has_reflection',
            'can_edit',
        ]
        read_only_fields = [
            'id',
            'author',
            'reaction_count',
            'comment_count',
            'is_reported',
            'report_count',
            'source',
            'created_at',
            'updated_at',
        ]

    def get_has_reflection(self, obj):
        return bool(obj.personal_reflection)

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user


class ScriptureCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating scripture shares."""

    class Meta:
        model = Scripture
        fields = [
            'group',
            'reference',
            'verse_text',
            'translation',
            'personal_reflection',
            'source',
        ]

    def validate_reference(self, value):
        """Validate Bible reference format."""
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Bible reference must be at least 3 characters long."
            )
        return value.strip()

    def validate_verse_text(self, value):
        """Validate verse text."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Verse text must be at least 10 characters long."
            )
        return value.strip()

    def validate_personal_reflection(self, value):
        """Validate personal reflection length."""
        if value and len(value) > 1000:
            raise serializers.ValidationError(
                "Personal reflection cannot exceed 1000 characters."
            )
        return value.strip() if value else ''

    def create(self, validated_data):
        """Create scripture with current user as author."""
        request = self.context.get('request')
        validated_data['author'] = request.user
        return super().create(validated_data)


class ScriptureVerseSearchSerializer(serializers.Serializer):
    """Serializer for Bible verse search/lookup."""

    reference = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Bible reference (e.g., 'John 3:16', 'Psalm 23:1-6')"
    )
    translation = serializers.CharField(
        max_length=20,
        default='KJV',
        help_text="Bible translation (KJV, NIV, ESV, etc.)"
    )

    def validate_reference(self, value):
        """Validate reference format."""
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Bible reference must be at least 3 characters long."
            )
        return value.strip()
