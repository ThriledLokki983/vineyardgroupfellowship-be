"""
Admin interface for messaging app.
"""

from django.contrib import admin
from django.utils.html import format_html
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


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'author',
        'group',
        'category',
        'comment_count',
        'reaction_count',
        'is_pinned',
        'is_deleted',
        'created_at',
    ]
    list_filter = [
        'category',
        'is_pinned',
        'is_deleted',
        'created_at',
    ]
    search_fields = [
        'title',
        'content',
        'author__username',
        'author__email',
        'group__name',
    ]
    readonly_fields = [
        'id',
        'comment_count',
        'reaction_count',
        'created_at',
        'updated_at',
        'deleted_at',
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'group', 'author', 'category')
        }),
        ('Content', {
            'fields': ('title', 'content')
        }),
        ('Stats', {
            'fields': ('comment_count', 'reaction_count')
        }),
        ('Flags', {
            'fields': ('is_pinned', 'is_deleted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    actions = ['pin_discussions', 'unpin_discussions',
               'soft_delete_discussions']

    def pin_discussions(self, request, queryset):
        queryset.update(is_pinned=True)
    pin_discussions.short_description = "Pin selected discussions"

    def unpin_discussions(self, request, queryset):
        queryset.update(is_pinned=False)
    unpin_discussions.short_description = "Unpin selected discussions"

    def soft_delete_discussions(self, request, queryset):
        for discussion in queryset:
            discussion.soft_delete()
    soft_delete_discussions.short_description = "Soft delete selected discussions"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        'content_preview',
        'author',
        'discussion',
        'parent',
        'reaction_count',
        'is_edited',
        'is_deleted',
        'created_at',
    ]
    list_filter = [
        'is_edited',
        'is_deleted',
        'created_at',
    ]
    search_fields = [
        'content',
        'author__username',
        'author__email',
        'discussion__title',
    ]
    readonly_fields = [
        'id',
        'reaction_count',
        'is_edited',
        'edited_at',
        'created_at',
        'updated_at',
        'deleted_at',
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'discussion', 'author', 'parent')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Stats', {
            'fields': ('reaction_count',)
        }),
        ('Edit Tracking', {
            'fields': ('is_edited', 'edited_at')
        }),
        ('Flags', {
            'fields': ('is_deleted',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'

    def content_preview(self, obj):
        return obj.content[:75] + '...' if len(obj.content) > 75 else obj.content
    content_preview.short_description = 'Content'


class CommentHistoryInline(admin.TabularInline):
    model = CommentHistory
    extra = 0
    readonly_fields = ['content', 'edited_at', 'edited_by']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CommentHistory)
class CommentHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'comment',
        'content_preview',
        'edited_by',
        'edited_at',
    ]
    list_filter = ['edited_at']
    search_fields = [
        'content',
        'comment__content',
        'edited_by__username',
    ]
    readonly_fields = ['id', 'comment', 'content', 'edited_at', 'edited_by']
    date_hierarchy = 'edited_at'

    def content_preview(self, obj):
        return obj.content[:75] + '...' if len(obj.content) > 75 else obj.content
    content_preview.short_description = 'Previous Content'

    def has_add_permission(self, request):
        return False


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'reaction_type',
        'target',
        'created_at',
    ]
    list_filter = [
        'reaction_type',
        'created_at',
    ]
    search_fields = [
        'user__username',
        'user__email',
        'discussion__title',
        'comment__content',
    ]
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'

    def target(self, obj):
        if obj.discussion:
            return format_html('Discussion: <a href="/admin/messaging/discussion/{}/change/">{}</a>',
                               obj.discussion.id, obj.discussion.title)
        elif obj.comment:
            preview = obj.comment.content[:50]
            return format_html('Comment: {}...', preview)
        return 'Unknown'
    target.short_description = 'Reacted To'


@admin.register(FeedItem)
class FeedItemAdmin(admin.ModelAdmin):
    list_display = [
        'content_type',
        'title',
        'author',
        'group',
        'comment_count',
        'reaction_count',
        'is_pinned',
        'is_deleted',
        'created_at',
    ]
    list_filter = [
        'content_type',
        'is_pinned',
        'is_deleted',
        'created_at',
    ]
    search_fields = [
        'title',
        'preview',
        'author__username',
        'group__name',
    ]
    readonly_fields = [
        'id',
        'content_type',
        'content_id',
        'group',
        'author',
        'title',
        'preview',
        'comment_count',
        'reaction_count',
        'is_pinned',
        'is_deleted',
        'created_at',
        'updated_at',
    ]
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False  # FeedItems are auto-created via signals


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'email_enabled',
        'quiet_hours_enabled',
        'quiet_hours_display',
        'created_at',
    ]
    list_filter = [
        'email_enabled',
        'quiet_hours_enabled',
        'email_new_discussion',
        'email_new_comment',
        'email_urgent_prayer',
    ]
    search_fields = [
        'user__username',
        'user__email',
    ]
    readonly_fields = [
        'id',
        'unsubscribe_token',
        'created_at',
        'updated_at',
    ]
    fieldsets = (
        ('User', {
            'fields': ('id', 'user')
        }),
        ('Email Preferences', {
            'fields': (
                'email_enabled',
                'email_new_discussion',
                'email_new_comment',
                'email_new_reaction',
                'email_urgent_prayer',
            )
        }),
        ('Quiet Hours', {
            'fields': (
                'quiet_hours_enabled',
                'quiet_hours_start',
                'quiet_hours_end',
            )
        }),
        ('Unsubscribe', {
            'fields': ('unsubscribe_token',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def quiet_hours_display(self, obj):
        if obj.quiet_hours_enabled:
            return f"{obj.quiet_hours_start} - {obj.quiet_hours_end}"
        return "Disabled"
    quiet_hours_display.short_description = 'Quiet Hours'


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'notification_type',
        'status',
        'to_email',
        'subject_preview',
        'created_at',
    ]
    list_filter = [
        'notification_type',
        'status',
        'created_at',
    ]
    search_fields = [
        'user__username',
        'user__email',
        'to_email',
        'subject',
    ]
    readonly_fields = [
        'id',
        'user',
        'notification_type',
        'status',
        'to_email',
        'subject',
        'error_message',
        'created_at',
    ]
    date_hierarchy = 'created_at'

    def subject_preview(self, obj):
        return obj.subject[:75] + '...' if len(obj.subject) > 75 else obj.subject
    subject_preview.short_description = 'Subject'

    def has_add_permission(self, request):
        return False  # Logs are auto-created

    def has_change_permission(self, request, obj=None):
        return False  # Logs are immutable


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'reporter_link',
        'content_preview',
        'reason',
        'status',
        'reviewed_by',
        'created_at',
    ]
    list_filter = [
        'status',
        'reason',
        'content_type',
        'created_at',
        'reviewed_at',
    ]
    search_fields = [
        'reporter__username',
        'reporter__email',
        'details',
        'review_notes',
    ]
    readonly_fields = [
        'id',
        'reporter',
        'content_type',
        'object_id',
        'content_link',
        'created_at',
        'updated_at',
    ]
    fieldsets = [
        ('Report Information', {
            'fields': [
                'id',
                'reporter',
                'content_type',
                'object_id',
                'content_link',
                'reason',
                'details',
            ]
        }),
        ('Review', {
            'fields': [
                'status',
                'reviewed_by',
                'reviewed_at',
                'review_notes',
            ]
        }),
        ('Timestamps', {
            'fields': [
                'created_at',
                'updated_at',
            ],
            'classes': ['collapse'],
        }),
    ]
    date_hierarchy = 'created_at'

    def reporter_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:authentication_user_change',
                      args=[obj.reporter.id])
        return format_html('<a href="{}">{}</a>', url, obj.reporter.username)
    reporter_link.short_description = 'Reporter'

    def content_preview(self, obj):
        content = obj.content_object
        if not content:
            return '[Deleted]'

        if isinstance(content, Discussion):
            preview = content.title[:50]
        elif isinstance(content, Comment):
            preview = content.content[:50]
        else:
            preview = str(content)[:50]

        return preview + '...' if len(str(preview)) >= 50 else preview
    content_preview.short_description = 'Content'

    def content_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        content = obj.content_object
        if not content:
            return '[Content deleted]'

        if isinstance(content, Discussion):
            url = reverse('admin:messaging_discussion_change',
                          args=[content.id])
            return format_html('<a href="{}">{}</a>', url, content.title)
        elif isinstance(content, Comment):
            url = reverse('admin:messaging_comment_change', args=[content.id])
            return format_html('<a href="{}">{}</a>', url, f'Comment by {content.author.username}')

        return str(content)
    content_link.short_description = 'View Content'

    def has_add_permission(self, request):
        return False  # Reports created through API only


# =============================================================================
# PHASE 2: FAITH FEATURES ADMIN
# =============================================================================

@admin.register(PrayerRequest)
class PrayerRequestAdmin(admin.ModelAdmin):
    """Admin interface for prayer requests."""

    list_display = [
        'urgency_icon',
        'title',
        'author',
        'group',
        'category',
        'urgency',
        'is_answered',
        'prayer_count',
        'comment_count',
        'is_reported',
        'created_at',
    ]
    list_filter = [
        'urgency',
        'category',
        'is_answered',
        'is_reported',
        'created_at',
    ]
    search_fields = [
        'title',
        'content',
        'author__username',
        'group__name',
        'answer_description',
    ]
    readonly_fields = [
        'id',
        'prayer_count',
        'comment_count',
        'report_count',
        'created_at',
        'updated_at',
        'answered_at',
    ]
    fieldsets = [
        ('Prayer Details', {
            'fields': [
                'id',
                'group',
                'author',
                'title',
                'content',
                'category',
                'urgency',
            ]
        }),
        ('Answer Tracking', {
            'fields': [
                'is_answered',
                'answered_at',
                'answer_description',
            ]
        }),
        ('Engagement', {
            'fields': [
                'prayer_count',
                'comment_count',
            ]
        }),
        ('Moderation', {
            'fields': [
                'is_reported',
                'report_count',
            ]
        }),
        ('Timestamps', {
            'fields': [
                'created_at',
                'updated_at',
            ]
        }),
    ]
    actions = ['mark_as_answered']
    date_hierarchy = 'created_at'

    def urgency_icon(self, obj):
        """Display urgency with icon."""
        icon = '🔥' if obj.urgency == 'urgent' else '🙏'
        color = 'red' if obj.urgency == 'urgent' else 'green'
        return format_html(
            '<span style="color: {}; font-size: 16px;">{} {}</span>',
            color,
            icon,
            obj.get_urgency_display()
        )
    urgency_icon.short_description = 'Urgency'

    @admin.action(description='Mark selected prayers as answered')
    def mark_as_answered(self, request, queryset):
        """Mark prayers as answered."""
        count = 0
        for prayer in queryset.filter(is_answered=False):
            prayer.mark_answered()
            count += 1

        self.message_user(
            request,
            f'{count} prayer request(s) marked as answered.'
        )


@admin.register(Testimony)
class TestimonyAdmin(admin.ModelAdmin):
    """Admin interface for testimonies."""

    list_display = [
        'public_icon',
        'title',
        'author',
        'group',
        'is_public',
        'is_public_approved',
        'has_prayer_link',
        'reaction_count',
        'comment_count',
        'is_reported',
        'created_at',
    ]
    list_filter = [
        'is_public',
        'is_public_approved',
        'is_reported',
        'created_at',
    ]
    search_fields = [
        'title',
        'content',
        'author__username',
        'group__name',
    ]
    readonly_fields = [
        'id',
        'reaction_count',
        'comment_count',
        'report_count',
        'created_at',
        'updated_at',
        'public_shared_at',
    ]
    fieldsets = [
        ('Testimony Details', {
            'fields': [
                'id',
                'group',
                'author',
                'title',
                'content',
                'answered_prayer',
            ]
        }),
        ('Public Sharing', {
            'fields': [
                'is_public',
                'public_shared_at',
                'is_public_approved',
                'approved_by',
            ]
        }),
        ('Engagement', {
            'fields': [
                'reaction_count',
                'comment_count',
            ]
        }),
        ('Moderation', {
            'fields': [
                'is_reported',
                'report_count',
            ]
        }),
        ('Timestamps', {
            'fields': [
                'created_at',
                'updated_at',
            ]
        }),
    ]
    actions = ['approve_for_public']
    date_hierarchy = 'created_at'

    def public_icon(self, obj):
        """Display public status with icon."""
        if obj.is_public and obj.is_public_approved:
            return format_html(
                '<span style="color: green; font-size: 16px;">🌍 Public ✓</span>'
            )
        elif obj.is_public:
            return format_html(
                '<span style="color: orange; font-size: 16px;">🌍 Pending</span>'
            )
        return format_html(
            '<span style="color: gray; font-size: 16px;">👥 Private</span>'
        )
    public_icon.short_description = 'Visibility'

    def has_prayer_link(self, obj):
        """Check if linked to answered prayer."""
        return bool(obj.answered_prayer)
    has_prayer_link.boolean = True
    has_prayer_link.short_description = 'Prayer Link'

    @admin.action(description='Approve selected testimonies for public sharing')
    def approve_for_public(self, request, queryset):
        """Approve testimonies for public sharing."""
        count = 0
        for testimony in queryset.filter(is_public=True, is_public_approved=False):
            testimony.is_public_approved = True
            testimony.approved_by = request.user
            testimony.save(update_fields=['is_public_approved', 'approved_by'])
            count += 1

        self.message_user(
            request,
            f'{count} testimony/testimonies approved for public sharing.'
        )


@admin.register(Scripture)
class ScriptureAdmin(admin.ModelAdmin):
    """Admin interface for scripture shares."""

    list_display = [
        'reference_icon',
        'reference',
        'translation',
        'author',
        'group',
        'source',
        'has_reflection',
        'reaction_count',
        'comment_count',
        'is_reported',
        'created_at',
    ]
    list_filter = [
        'translation',
        'source',
        'is_reported',
        'created_at',
    ]
    search_fields = [
        'reference',
        'verse_text',
        'personal_reflection',
        'author__username',
        'group__name',
    ]
    readonly_fields = [
        'id',
        'reaction_count',
        'comment_count',
        'report_count',
        'created_at',
        'updated_at',
    ]
    fieldsets = [
        ('Scripture Details', {
            'fields': [
                'id',
                'group',
                'author',
                'reference',
                'verse_text',
                'translation',
                'source',
            ]
        }),
        ('Personal Reflection', {
            'fields': [
                'personal_reflection',
            ]
        }),
        ('Engagement', {
            'fields': [
                'reaction_count',
                'comment_count',
            ]
        }),
        ('Moderation', {
            'fields': [
                'is_reported',
                'report_count',
            ]
        }),
        ('Timestamps', {
            'fields': [
                'created_at',
                'updated_at',
            ]
        }),
    ]
    date_hierarchy = 'created_at'

    def reference_icon(self, obj):
        """Display scripture reference with icon."""
        return format_html(
            '<span style="font-size: 16px;">📖 {}</span>',
            obj.reference
        )
    reference_icon.short_description = 'Scripture'

    def has_reflection(self, obj):
        """Check if personal reflection is included."""
        return bool(obj.personal_reflection)
    has_reflection.boolean = True
    has_reflection.short_description = 'Has Reflection'
