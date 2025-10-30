"""
Django admin configuration for profiles app.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import UserProfileBasic, ProfilePhoto, ProfileCompletenessTracker


@admin.register(UserProfileBasic)
class UserProfileAdmin(admin.ModelAdmin):
    """Comprehensive admin interface for user profiles."""

    list_display = [
        'user', 'display_name', 'profile_visibility_display', 'is_verified', 'is_complete', 'created_at'
    ]
    list_filter = [
        'profile_visibility', 'created_at', 'updated_at'
    ]
    search_fields = ['user__username', 'user__email', 'display_name', 'bio']
    readonly_fields = [
        'created_at', 'updated_at', 'user_profile_info', 'completion_status'
    ]

    def profile_visibility_display(self, obj):
        """Display profile visibility with icon."""
        visibility_icons = {
            'private': '🔒',
            'friends': '👥',
            'community': '🌍',
            'public': '🌐'
        }
        icon = visibility_icons.get(obj.profile_visibility, '❓')
        return f"{icon} {obj.get_profile_visibility_display()}"
    profile_visibility_display.short_description = 'Profile Visibility'

    def is_verified(self, obj):
        """Check if user's email is verified."""
        return obj.user.email_verified if hasattr(obj.user, 'email_verified') else False
    is_verified.boolean = True
    is_verified.short_description = 'Email Verified'

    def is_complete(self, obj):
        """Show profile completion status."""
        completed_fields = 0
        total_fields = 3  # display_name, bio, timezone

        if obj.display_name:
            completed_fields += 1
        if obj.bio:
            completed_fields += 1
        if obj.timezone and obj.timezone != 'UTC':
            completed_fields += 1

        percentage = (completed_fields / total_fields) * 100

        if percentage >= 80:
            icon = "✅"
            color = "green"
        elif percentage >= 50:
            icon = "⚠️"
            color = "orange"
        else:
            icon = "❌"
            color = "red"

        return format_html(
            '<span style="color: {};">{} {}%</span>',
            color, icon, int(percentage)
        )
    is_complete.short_description = 'Profile Complete'

    def user_profile_info(self, obj):
        """Display comprehensive user and profile information."""
        html = []

        # User info
        html.append(f"<strong>Username:</strong> {obj.user.username}")
        html.append(f"<strong>Email:</strong> {obj.user.email}")

        # Email verification
        if hasattr(obj.user, 'email_verified'):
            html.append(
                f"<strong>Email Verified:</strong> {'✅' if obj.user.email_verified else '❌'}")

        # Profile info
        html.append(
            f"<strong>Display Name:</strong> {obj.display_name or '<em>Not Set</em>'}")

        if obj.bio:
            bio_preview = obj.bio[:100] + \
                "..." if len(obj.bio) > 100 else obj.bio
            html.append(f"<strong>Bio:</strong> {bio_preview}")
        else:
            html.append("<strong>Bio:</strong> <em>Not Set</em>")

        html.append(f"<strong>Timezone:</strong> {obj.timezone}")
        html.append(
            f"<strong>Profile Visibility:</strong> {obj.get_profile_visibility_display()}")

        # Timestamps
        html.append(
            f"<strong>Profile Created:</strong> {obj.created_at.strftime('%Y-%m-%d %H:%M')}")
        html.append(
            f"<strong>Last Updated:</strong> {obj.updated_at.strftime('%Y-%m-%d %H:%M')}")

        return format_html("<br>".join(html))
    user_profile_info.short_description = 'User & Profile Information'

    def completion_status(self, obj):
        """Display detailed completion status."""
        fields_status = []

        # Check each field
        if obj.display_name:
            fields_status.append("✅ Display Name")
        else:
            fields_status.append("❌ Display Name")

        if obj.bio:
            fields_status.append("✅ Bio")
        else:
            fields_status.append("❌ Bio")

        if obj.timezone and obj.timezone != 'UTC':
            fields_status.append("✅ Timezone")
        else:
            fields_status.append("❌ Timezone (Default)")

        return format_html("<br>".join(fields_status))
    completion_status.short_description = 'Completion Details'

    fieldsets = (
        ('User & Basic Info', {
            'fields': ('user', 'display_name', 'bio', 'timezone')
        }),
        ('Privacy Settings', {
            'fields': ('profile_visibility',)
        }),
        ('Profile Summary', {
            'fields': ('user_profile_info', 'completion_status'),
            'description': 'Comprehensive profile information and completion status'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user')


@admin.register(ProfilePhoto)
class ProfilePhotoAdmin(admin.ModelAdmin):
    """
    Admin interface for profile photos.
    """

    list_display = [
        'user_email',
        'photo_thumbnail',
        'photo_moderation_status',
        'photo_visibility',
        'file_size_display',
        'uploaded_at',
    ]

    list_filter = [
        'photo_moderation_status',
        'photo_visibility',
        'uploaded_at',
        'photo_content_type',
    ]

    search_fields = [
        'user__email',
        'user__username',
        'photo_filename',
    ]

    readonly_fields = [
        'user',
        'photo_preview',
        'thumbnail_preview',
        'photo_filename',
        'photo_content_type',
        'photo_size_bytes',
        'uploaded_at',
        'updated_at',
    ]

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Photo Information', {
            'fields': (
                'photo',
                'photo_preview',
                'thumbnail',
                'thumbnail_preview',
                'photo_filename',
                'photo_content_type',
                'photo_size_bytes',
            )
        }),
        ('Settings', {
            'fields': ('photo_visibility', 'photo_moderation_status')
        }),
        ('Metadata', {
            'fields': ('uploaded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_photos', 'reject_photos', 'flag_photos']

    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    def photo_thumbnail(self, obj):
        """Display small thumbnail in list view."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />',
                obj.thumbnail.url
            )
        return "No photo"
    photo_thumbnail.short_description = 'Thumbnail'

    def photo_preview(self, obj):
        """Display photo preview in detail view."""
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px;" />',
                obj.photo.url
            )
        return "No photo"
    photo_preview.short_description = 'Photo Preview'

    def thumbnail_preview(self, obj):
        """Display thumbnail preview in detail view."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="width: 150px; height: 150px; object-fit: cover;" />',
                obj.thumbnail.url
            )
        return "No thumbnail"
    thumbnail_preview.short_description = 'Thumbnail Preview'

    def file_size_display(self, obj):
        """Display file size in human-readable format."""
        if obj.photo_size_bytes:
            size = obj.photo_size_bytes
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
        return "Unknown"
    file_size_display.short_description = 'File Size'

    def approve_photos(self, request, queryset):
        """Approve selected photos."""
        updated = queryset.update(photo_moderation_status='approved')
        self.message_user(
            request,
            f"Successfully approved {updated} photo(s)."
        )
    approve_photos.short_description = "Approve selected photos"

    def reject_photos(self, request, queryset):
        """Reject selected photos."""
        updated = queryset.update(photo_moderation_status='rejected')
        self.message_user(
            request,
            f"Successfully rejected {updated} photo(s)."
        )
    reject_photos.short_description = "Reject selected photos"

    def flag_photos(self, request, queryset):
        """Flag selected photos for review."""
        updated = queryset.update(photo_moderation_status='flagged')
        self.message_user(
            request,
            f"Successfully flagged {updated} photo(s) for review."
        )
    flag_photos.short_description = "Flag selected photos for review"


@admin.register(ProfileCompletenessTracker)
class ProfileCompletenessTrackerAdmin(admin.ModelAdmin):
    """
    Admin interface for profile completeness tracking.
    """

    list_display = [
        'user_email',
        'overall_completion_percentage',
        'completion_level',
        'completion_badges',
        'last_calculated_at',
    ]

    list_filter = [
        'completion_level',
        'has_basic_profile_badge',
        'has_verified_email_badge',
        'has_recovery_goals_badge',
        'has_comprehensive_profile_badge',
        'last_calculated_at',
    ]

    search_fields = [
        'user__email',
        'user__username',
    ]

    readonly_fields = [
        'user',
        'last_calculated_at',
        'created_at',
    ]

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Overall Completion', {
            'fields': (
                'overall_completion_percentage',
                'completion_level',
            )
        }),
        ('Section Scores', {
            'fields': (
                'basic_info_score',
                'contact_info_score',
                'recovery_info_score',
                'preferences_score',
                'profile_media_score',
            ),
            'classes': ('collapse',)
        }),
        ('Badges', {
            'fields': (
                'has_basic_profile_badge',
                'has_verified_email_badge',
                'has_recovery_goals_badge',
                'has_comprehensive_profile_badge',
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('last_calculated_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['recalculate_completeness']

    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    def completion_badges(self, obj):
        """Display earned badges."""
        badges = []
        if obj.has_basic_profile_badge:
            badges.append("📝 Basic")
        if obj.has_verified_email_badge:
            badges.append("✅ Verified")
        if obj.has_recovery_goals_badge:
            badges.append("🎯 Goals")
        if obj.has_comprehensive_profile_badge:
            badges.append("🏆 Complete")

        return " ".join(badges) if badges else "No badges"
    completion_badges.short_description = 'Badges'

    def recalculate_completeness(self, request, queryset):
        """Recalculate completeness for selected users."""
        from .services import ProfileCompletenessService

        updated = 0
        for tracker in queryset:
            ProfileCompletenessService.calculate_completeness(tracker.user)
            updated += 1

        self.message_user(
            request,
            f"Successfully recalculated completeness for {updated} user(s)."
        )
    recalculate_completeness.short_description = "Recalculate completeness for selected users"
