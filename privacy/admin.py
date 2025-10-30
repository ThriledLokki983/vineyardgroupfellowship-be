"""
Django admin configuration for privacy models.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import PrivacyProfile, ConsentLog, DataProcessingRecord


@admin.register(PrivacyProfile)
class PrivacyProfileAdmin(admin.ModelAdmin):
    """Admin interface for privacy profiles (extracted from UserProfile)."""

    list_display = [
        'user', 'privacy_policy_accepted', 'data_processing_consent', 'profile_visibility',
        'deletion_requested', 'created_at'
    ]
    list_filter = [
        'privacy_policy_accepted', 'terms_of_service_accepted', 'data_processing_consent',
        'marketing_consent', 'profile_visibility', 'deletion_requested', 'created_at'
    ]
    search_fields = ['user__username', 'user__email']
    readonly_fields = [
        'privacy_policy_accepted_at', 'terms_of_service_accepted_at', 'data_processing_consent_at',
        'marketing_consent_at', 'deletion_requested_at', 'deletion_scheduled_for',
        'data_export_requested_at', 'consent_withdrawn_at', 'created_at', 'updated_at'
    ]

    fieldsets = (
        (_('User & Basic Settings'), {
            'fields': ('user', 'profile_visibility', 'recovery_info_visibility', 'contact_preferences')
        }),
        (_('Legal Consent'), {
            'fields': (
                'privacy_policy_accepted', 'privacy_policy_accepted_at', 'privacy_policy_version',
                'terms_of_service_accepted', 'terms_of_service_accepted_at', 'terms_of_service_version'
            )
        }),
        (_('Data Processing Consent'), {
            'fields': (
                'data_processing_consent', 'data_processing_consent_at',
                'marketing_consent', 'marketing_consent_at',
                'research_participation_consent', 'research_participation_consent_at'
            )
        }),
        (_('Data Retention'), {
            'fields': ('data_retention_preference', 'auto_delete_inactive_data')
        }),
        (_('Account Deletion'), {
            'fields': (
                'deletion_requested', 'deletion_requested_at', 'deletion_scheduled_for',
                'anonymize_posts_on_deletion', 'anonymize_recovery_data'
            ),
            'classes': ('collapse',)
        }),
        (_('Data Export & Consent Withdrawal'), {
            'fields': (
                'data_export_requested', 'data_export_requested_at',
                'consent_withdrawn_at', 'consent_withdrawal_reason'
            ),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user')


@admin.register(ConsentLog)
class ConsentLogAdmin(admin.ModelAdmin):
    """Admin interface for consent audit logs."""

    list_display = [
        'user', 'consent_type', 'action', 'consent_given', 'version', 'created_at'
    ]
    list_filter = [
        'consent_type', 'action', 'consent_given', 'created_at'
    ]
    search_fields = ['user__username', 'user__email', 'consent_type', 'reason']
    readonly_fields = [
        'user', 'consent_type', 'action', 'consent_given', 'version',
        'ip_address', 'user_agent', 'reason', 'expires_at', 'created_at'
    ]

    fieldsets = (
        (_('Consent Information'), {
            'fields': ('user', 'consent_type', 'action', 'consent_given', 'version')
        }),
        (_('Context'), {
            'fields': ('reason', 'expires_at')
        }),
        (_('Technical Details'), {
            'fields': ('ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """Consent logs should not be manually created."""
        return False

    def has_change_permission(self, request, obj=None):
        """Consent logs should be immutable."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Consent logs should not be deleted for audit purposes."""
        return False


@admin.register(DataProcessingRecord)
class DataProcessingRecordAdmin(admin.ModelAdmin):
    """Admin interface for data processing transparency records."""

    list_display = [
        'user', 'purpose', 'legal_basis', 'is_active', 'started_at', 'retention_expires_display'
    ]
    list_filter = [
        'purpose', 'legal_basis', 'is_active', 'started_at'
    ]
    search_fields = ['user__username', 'user__email', 'purpose', 'data_categories']
    readonly_fields = [
        'started_at', 'ended_at', 'retention_expires_display'
    ]

    fieldsets = (
        (_('Processing Information'), {
            'fields': ('user', 'purpose', 'data_categories', 'legal_basis')
        }),
        (_('Retention & Status'), {
            'fields': ('retention_period_days', 'retention_expires_display', 'is_active')
        }),
        (_('Timeline'), {
            'fields': ('started_at', 'ended_at')
        }),
        (_('Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def retention_expires_display(self, obj):
        """Display when retention period expires."""
        expiry = obj.retention_expires_at
        if expiry:
            return expiry.strftime('%Y-%m-%d')
        return "No expiry set"
    retention_expires_display.short_description = "Retention Expires"
# Currently, all privacy-related models are managed through other appsx