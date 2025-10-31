"""
Django admin configuration for authentication models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib.admin.sites import NotRegistered

from .models import UserSession, AuditLog, TokenBlacklist, EmailVerificationToken, PasswordResetToken
from profiles.models import UserProfileBasic

User = get_user_model()


class CustomUserAdmin(BaseUserAdmin):
    """
    Custom User admin with additional authentication fields.
    """

    list_display = BaseUserAdmin.list_display + (
        'email_verified',
        'is_account_locked_status',
        'failed_login_attempts',
        'last_login_formatted',
    )

    list_filter = BaseUserAdmin.list_filter + (
        'email_verified',
        'password_changed_at',
        'locked_until',
    )

    readonly_fields = BaseUserAdmin.readonly_fields + (
        'email_verified_at',
        'password_changed_at',
        'locked_until',
        'terms_accepted_at',
        'privacy_policy_accepted_at',
    )

    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Email Verification'), {
            'fields': ('email_verified', 'email_verified_at')
        }),
        (_('Account Security'), {
            'fields': (
                'failed_login_attempts',
                'locked_until',
                'password_changed_at',
            )
        }),
        (_('Legal Acceptance'), {
            'fields': (
                'terms_accepted_at',
                'privacy_policy_accepted_at',
            ),
            'classes': ('collapse',)
        }),
    )

    def is_account_locked_status(self, obj):
        """Check if account is currently locked."""
        return obj.is_account_locked()
    is_account_locked_status.boolean = True
    is_account_locked_status.short_description = 'Account Locked'

    def last_login_formatted(self, obj):
        """Format last login time."""
        if obj.last_login:
            return obj.last_login.strftime('%Y-%m-%d %H:%M:%S')
        return 'Never'
    last_login_formatted.short_description = 'Last Login'
    last_login_formatted.admin_order_field = 'last_login'

    actions = ['unlock_accounts', 'verify_emails']

    def unlock_accounts(self, request, queryset):
        """Unlock selected user accounts."""
        count = 0
        for user in queryset:
            if user.is_account_locked():
                user.failed_login_attempts = 0
                user.locked_until = None
                user.save(update_fields=[
                          'failed_login_attempts', 'locked_until'])
                count += 1

        self.message_user(
            request,
            f'Successfully unlocked {count} account(s).'
        )
    unlock_accounts.short_description = 'Unlock selected accounts'

    def verify_emails(self, request, queryset):
        """Verify email addresses for selected users."""
        count = queryset.filter(email_verified=False).update(
            email_verified=True,
            email_verified_at=timezone.now()
        )

        self.message_user(
            request,
            f'Successfully verified {count} email address(es).'
        )
    verify_emails.short_description = 'Verify selected email addresses'


# ============================================================================
# Enhanced User Admin for Authentication & Authorization Section
# ============================================================================
#
# Note: UserProfileBasic admin is handled in the profiles app admin.py
# This provides User admin with profile integration for the auth section.
# ============================================================================

class UserProfileBasicInline(admin.StackedInline):
    """Inline admin interface for user basic profiles."""
    model = UserProfileBasic
    can_delete = False
    verbose_name_plural = 'Basic Profile'

    from profiles.admin import UserProfileBasicAdminForm
    form = UserProfileBasicAdminForm

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    fieldsets = (
        (_('Basic Profile Information'), {
            'fields': ('display_name', 'bio', 'timezone')
        }),
        (_('Privacy Settings'), {
            'fields': ('profile_visibility',)
        }),
        (_('Leadership Permissions'), {
            'fields': ('can_lead_group',),
            'description': _('Set leadership permissions for this user')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class EnhancedUserAdmin(BaseUserAdmin):
    """Enhanced user admin with profile inline and comprehensive features."""

    inlines = (UserProfileBasicInline,)

    list_display = (
        'username', 'email', 'display_name_from_profile',
        'email_verified', 'is_staff', 'is_active',
        'profile_completion_status', 'last_login_formatted'
    )

    list_filter = BaseUserAdmin.list_filter + (
        'email_verified',
        'password_changed_at',
        'locked_until',
    )

    search_fields = BaseUserAdmin.search_fields + (
        'basic_profile__display_name',
        'basic_profile__bio',
    )

    readonly_fields = BaseUserAdmin.readonly_fields + (
        'email_verified_at',
        'password_changed_at',
        'locked_until',
        'terms_accepted_at',
        'privacy_policy_accepted_at',
        'profile_info_summary',
    )

    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Email Verification'), {
            'fields': ('email_verified', 'email_verified_at')
        }),
        (_('Account Security'), {
            'fields': (
                'failed_login_attempts',
                'locked_until',
                'password_changed_at',
            )
        }),
        (_('Profile Summary'), {
            'fields': ('profile_info_summary',),
            'description': _('Basic profile information (edit in Profile section below)')
        }),
        (_('Legal Acceptance'), {
            'fields': (
                'terms_accepted_at',
                'privacy_policy_accepted_at',
            ),
            'classes': ('collapse',)
        }),
    )

    def display_name_from_profile(self, obj):
        """Display name from user's basic profile."""
        try:
            profile = obj.basic_profile
            return profile.display_name or f"User {obj.username}"
        except:
            return f"User {obj.username} (No Profile)"
    display_name_from_profile.short_description = _('Display Name')
    display_name_from_profile.admin_order_field = 'basic_profile__display_name'

    def profile_completion_status(self, obj):
        """Show profile completion status."""
        try:
            profile = obj.basic_profile
            completed_fields = 0
            total_fields = 3  # display_name, bio, timezone

            if profile.display_name:
                completed_fields += 1
            if profile.bio:
                completed_fields += 1
            if profile.timezone and profile.timezone != 'UTC':
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
        except:
            return format_html('<span style="color: red;">❌ No Profile</span>')
    profile_completion_status.short_description = _('Profile Completion')

    def profile_info_summary(self, obj):
        """Display comprehensive profile information summary."""
        try:
            profile = obj.basic_profile
            html = []

            # Basic info
            html.append(
                f"<strong>Display Name:</strong> {profile.display_name or '<em>Not Set</em>'}")

            if profile.bio:
                bio_preview = profile.bio[:100] + \
                    "..." if len(profile.bio) > 100 else profile.bio
                html.append(f"<strong>Bio:</strong> {bio_preview}")
            else:
                html.append("<strong>Bio:</strong> <em>Not Set</em>")

            html.append(f"<strong>Timezone:</strong> {profile.timezone}")
            html.append(
                f"<strong>Profile Visibility:</strong> {profile.get_profile_visibility_display()}")

            # Profile stats
            html.append(
                f"<strong>Profile Created:</strong> {profile.created_at.strftime('%Y-%m-%d %H:%M')}")
            html.append(
                f"<strong>Last Updated:</strong> {profile.updated_at.strftime('%Y-%m-%d %H:%M')}")

            return format_html("<br>".join(html))
        except Exception as e:
            return format_html(
                '<em>No basic profile found. <a href="#" onclick="alert(\'Profile will be created automatically when user logs in or updates profile.\')">Auto-created on first use</a></em>'
            )
    profile_info_summary.short_description = _('Profile Information')

    def is_account_locked_status(self, obj):
        """Check if account is currently locked."""
        return obj.is_account_locked()
    is_account_locked_status.boolean = True
    is_account_locked_status.short_description = 'Account Locked'

    def last_login_formatted(self, obj):
        """Format last login time."""
        if obj.last_login:
            return obj.last_login.strftime('%Y-%m-%d %H:%M:%S')
        return 'Never'
    last_login_formatted.short_description = 'Last Login'
    last_login_formatted.admin_order_field = 'last_login'

    actions = ['unlock_accounts', 'verify_emails', 'create_missing_profiles']

    def unlock_accounts(self, request, queryset):
        """Unlock selected user accounts."""
        count = 0
        for user in queryset:
            if user.is_account_locked():
                user.failed_login_attempts = 0
                user.locked_until = None
                user.save(update_fields=[
                          'failed_login_attempts', 'locked_until'])
                count += 1

        self.message_user(
            request,
            f'Successfully unlocked {count} account(s).'
        )
    unlock_accounts.short_description = 'Unlock selected accounts'

    def verify_emails(self, request, queryset):
        """Verify email addresses for selected users."""
        count = queryset.filter(email_verified=False).update(
            email_verified=True,
            email_verified_at=timezone.now()
        )
        self.message_user(
            request,
            f'Successfully verified {count} email address(es).'
        )
    verify_emails.short_description = 'Verify email addresses'

    def create_missing_profiles(self, request, queryset):
        """Create basic profiles for users who don't have them."""
        from profiles.models import UserProfileBasic
        count = 0
        for user in queryset:
            profile, created = UserProfileBasic.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': f'User {user.username}',
                    'timezone': 'UTC',
                }
            )
            if created:
                count += 1

        self.message_user(
            request,
            f'Successfully created {count} basic profile(s).'
        )
    create_missing_profiles.short_description = 'Create missing basic profiles'

    def get_queryset(self, request):
        """Optimize queryset with select_related for profile data."""
        return super().get_queryset(request).select_related('basic_profile')


# Register User admin in the standard Authentication and Authorization section
# This will make Users appear alongside Groups in the default auth section
admin.site.register(User, EnhancedUserAdmin)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for user sessions.
    """

    list_display = [
        'user_email',
        'device_name',
        'ip_address',
        'is_active',
        'is_verified',
        'created_at_formatted',
        'last_activity_formatted',
    ]

    list_filter = [
        'is_active',
        'is_verified',
        'created_at',
        'last_activity_at',
        'country',
    ]

    search_fields = [
        'user__email',
        'user__username',
        'ip_address',
        'user_agent',
        'device_fingerprint',
        'device_name',
    ]

    readonly_fields = [
        'user',
        'session_key',
        'refresh_token_jti',
        'device_fingerprint',
        'created_at',
        'last_activity_at',
        'last_rotation_at',
    ]

    date_hierarchy = 'created_at'

    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def created_at_formatted(self, obj):
        """Format creation time."""
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'

    def last_activity_formatted(self, obj):
        """Format last activity time."""
        if obj.last_activity_at:
            return obj.last_activity_at.strftime('%Y-%m-%d %H:%M:%S')
        return 'Never'
    last_activity_formatted.short_description = 'Last Activity'
    last_activity_formatted.admin_order_field = 'last_activity_at'

    actions = ['terminate_sessions']

    def terminate_sessions(self, request, queryset):
        """Terminate selected sessions."""
        count = queryset.filter(is_active=True).update(
            is_active=False,
            terminated_at=timezone.now(),
            termination_reason='admin_action'
        )

        self.message_user(
            request,
            f'Successfully terminated {count} session(s).'
        )
    terminate_sessions.short_description = 'Terminate selected sessions'


@admin.register(TokenBlacklist)
class TokenBlacklistAdmin(admin.ModelAdmin):
    """
    Admin interface for token blacklist.
    """

    list_display = [
        'user_email',
        'token_type',
        'reason',
        'blacklisted_at_formatted',
        'expires_at_formatted',
        'is_expired_status',
    ]

    list_filter = [
        'token_type',
        'reason',
        'blacklisted_at',
        'expires_at',
    ]

    search_fields = [
        'user__email',
        'user__username',
        'jti',
    ]

    readonly_fields = [
        'user',
        'jti',
        'token_type',
        'blacklisted_at',
        'expires_at',
    ]

    date_hierarchy = 'blacklisted_at'

    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def blacklisted_at_formatted(self, obj):
        """Format blacklisted time."""
        return obj.blacklisted_at.strftime('%Y-%m-%d %H:%M:%S')
    blacklisted_at_formatted.short_description = 'Blacklisted'
    blacklisted_at_formatted.admin_order_field = 'blacklisted_at'

    def expires_at_formatted(self, obj):
        """Format expiration time."""
        if obj.expires_at:
            return obj.expires_at.strftime('%Y-%m-%d %H:%M:%S')
        return 'Never'
    expires_at_formatted.short_description = 'Expires'
    expires_at_formatted.admin_order_field = 'expires_at'

    def is_expired_status(self, obj):
        """Check if token is expired."""
        return obj.is_expired()
    is_expired_status.boolean = True
    is_expired_status.short_description = 'Expired'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for audit logs - read-only for security.
    """

    list_display = [
        'user_display',
        'event_type',
        'success',
        'risk_level',
        'ip_address',
        'timestamp_formatted',
    ]

    list_filter = [
        'event_type',
        'success',
        'risk_level',
        'timestamp',
    ]

    search_fields = [
        'user__email',
        'user__username',
        'event_type',
        'description',
        'ip_address',
    ]

    readonly_fields = [
        'user',
        'event_type',
        'description',
        'ip_address',
        'user_agent',
        'session_id',
        'timestamp',
        'success',
        'risk_level',
        'metadata',
    ]

    date_hierarchy = 'timestamp'

    def user_display(self, obj):
        """Display user email or 'Anonymous' if no user."""
        if obj.user:
            return obj.user.email
        return format_html('<em>Anonymous</em>')
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__email'

    def timestamp_formatted(self, obj):
        """Format timestamp."""
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    timestamp_formatted.short_description = 'Timestamp'
    timestamp_formatted.admin_order_field = 'timestamp'

    def has_add_permission(self, request):
        """Audit logs should not be manually created."""
        return False

    def has_change_permission(self, request, obj=None):
        """Audit logs should not be modified."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit logs should not be deleted."""
        return request.user.is_superuser  # Only superusers can delete for cleanup


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """
    Admin interface for email verification tokens.
    """

    list_display = [
        'user_email',
        'email',
        'is_used',
        'is_expired_status',
        'created_at_formatted',
        'expires_at_formatted',
    ]

    list_filter = [
        'is_used',
        'created_at',
        'expires_at',
    ]

    search_fields = [
        'user__email',
        'email',
        'token',
    ]

    readonly_fields = [
        'user',
        'token',
        'email',
        'created_at',
        'expires_at',
        'used_at',
        'ip_address',
    ]

    date_hierarchy = 'created_at'

    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def created_at_formatted(self, obj):
        """Format creation time."""
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'

    def expires_at_formatted(self, obj):
        """Format expiration time."""
        return obj.expires_at.strftime('%Y-%m-%d %H:%M:%S')
    expires_at_formatted.short_description = 'Expires'
    expires_at_formatted.admin_order_field = 'expires_at'

    def is_expired_status(self, obj):
        """Check if token is expired."""
        return obj.is_expired()
    is_expired_status.boolean = True
    is_expired_status.short_description = 'Expired'


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """
    Admin interface for password reset tokens.
    """

    list_display = [
        'user_email',
        'is_used',
        'is_expired_status',
        'created_at_formatted',
        'expires_at_formatted',
    ]

    list_filter = [
        'is_used',
        'created_at',
        'expires_at',
    ]

    search_fields = [
        'user__email',
        'token',
    ]

    readonly_fields = [
        'user',
        'token',
        'created_at',
        'expires_at',
        'used_at',
        'ip_address',
        'user_agent',
    ]

    date_hierarchy = 'created_at'

    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def created_at_formatted(self, obj):
        """Format creation time."""
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'

    def expires_at_formatted(self, obj):
        """Format expiration time."""
        return obj.expires_at.strftime('%Y-%m-%d %H:%M:%S')
    expires_at_formatted.short_description = 'Expires'
    expires_at_formatted.admin_order_field = 'expires_at'

    def is_expired_status(self, obj):
        """Check if token is expired."""
        return obj.is_expired()
    is_expired_status.boolean = True
    is_expired_status.short_description = 'Expired'
