"""
Serializers for the privacy app.
Handles GDPR compliance and data privacy functionality.
"""

from typing import Dict, Any, List, Optional
import logging

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError

from rest_framework import serializers

# Import models from authentication app (they stay there)
from authentication.models import UserProfile, AuditLog

logger = logging.getLogger(__name__)
User = get_user_model()


class GDPRDataExportSerializer(serializers.Serializer):
    """
    GDPR Article 20 - Right to Data Portability serializer.

    Features:
    - Data export request validation
    - Export format specification
    - Privacy notice acknowledgment
    - Audit logging
    """

    export_format = serializers.ChoiceField(
        choices=[('json', 'JSON'), ('csv', 'CSV')],
        default='json',
        help_text="Format for data export"
    )
    include_sessions = serializers.BooleanField(
        default=True,
        help_text="Include session history in export"
    )
    include_audit_logs = serializers.BooleanField(
        default=True,
        help_text="Include activity audit logs in export"
    )
    privacy_notice_acknowledged = serializers.BooleanField(
        required=True,
        help_text="Acknowledgment that privacy notice has been read"
    )

    def validate_privacy_notice_acknowledged(self, value):
        """Ensure privacy notice is acknowledged."""
        if not value:
            raise serializers.ValidationError(
                _("You must acknowledge the privacy notice to proceed with data export.")
            )
        return value

    def create(self, validated_data):
        """Create data export request with audit logging."""
        request = self.context.get('request')

        # Log the export request
        AuditLog.objects.create(
            user=request.user,
            action='gdpr_data_export_requested',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'export_format': validated_data['export_format'],
                'include_sessions': validated_data['include_sessions'],
                'include_audit_logs': validated_data['include_audit_logs'],
                'privacy_notice_acknowledged': validated_data['privacy_notice_acknowledged']
            },
            risk_level='low'
        )

        return validated_data


class GDPRDataErasureSerializer(serializers.Serializer):
    """
    GDPR Article 17 - Right to Erasure (Right to be Forgotten) serializer.

    Features:
    - Account deletion request validation
    - Erasure reason specification
    - Confirmation requirements
    - Audit trail preservation options
    """

    erasure_reason = serializers.ChoiceField(
        choices=[
            ('no_longer_needed', 'Data no longer needed for original purpose'),
            ('withdraw_consent', 'Withdrawing consent'),
            ('object_processing', 'Objecting to processing'),
            ('unlawful_processing', 'Data processed unlawfully'),
            ('legal_obligation', 'Legal obligation to erase'),
            ('other', 'Other reason')
        ],
        required=True,
        help_text="Reason for requesting data erasure"
    )
    erasure_reason_details = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Additional details about erasure reason"
    )
    retain_audit_logs = serializers.BooleanField(
        default=True,
        help_text="Whether to retain audit logs for legal compliance"
    )
    confirmation_phrase = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Type 'DELETE MY ACCOUNT' to confirm"
    )
    final_confirmation = serializers.BooleanField(
        required=True,
        help_text="Final confirmation of account deletion"
    )

    def validate_confirmation_phrase(self, value):
        """Validate confirmation phrase."""
        if value.upper() != 'DELETE MY ACCOUNT':
            raise serializers.ValidationError(
                _("You must type 'DELETE MY ACCOUNT' to confirm.")
            )
        return value

    def validate_final_confirmation(self, value):
        """Ensure final confirmation is provided."""
        if not value:
            raise serializers.ValidationError(
                _("You must provide final confirmation to proceed with account deletion.")
            )
        return value

    def create(self, validated_data):
        """Create data erasure request with audit logging."""
        request = self.context.get('request')

        # Log the erasure request
        AuditLog.objects.create(
            user=request.user,
            action='gdpr_data_erasure_requested',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'erasure_reason': validated_data['erasure_reason'],
                'erasure_reason_details': validated_data.get('erasure_reason_details', ''),
                'retain_audit_logs': validated_data['retain_audit_logs'],
                'confirmation_provided': True
            },
            risk_level='high'  # Account deletion is high risk
        )

        return validated_data


class GDPRConsentSerializer(serializers.Serializer):
    """
    GDPR Article 7 - Consent Management serializer.

    Features:
    - Consent management for data processing
    - Granular consent options
    - Consent withdrawal capabilities
    - Legal basis tracking
    """

    consent_type = serializers.ChoiceField(
        choices=[
            ('data_processing', 'General data processing'),
            ('marketing', 'Marketing communications'),
            ('analytics', 'Analytics and performance'),
            ('third_party', 'Third-party data sharing'),
            ('cookies', 'Cookie usage'),
            ('profiling', 'Automated profiling')
        ],
        required=True,
        help_text="Type of consent being managed"
    )
    consent_status = serializers.BooleanField(
        required=True,
        help_text="Whether consent is granted (True) or withdrawn (False)"
    )
    legal_basis = serializers.ChoiceField(
        choices=[
            ('consent', 'Consent'),
            ('contract', 'Contract performance'),
            ('legal_obligation', 'Legal obligation'),
            ('vital_interests', 'Vital interests'),
            ('public_task', 'Public task'),
            ('legitimate_interests', 'Legitimate interests')
        ],
        default='consent',
        help_text="Legal basis for processing"
    )
    purpose_description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Description of processing purpose"
    )

    def create(self, validated_data):
        """Create consent record with audit logging."""
        request = self.context.get('request')

        # Log the consent change
        AuditLog.objects.create(
            user=request.user,
            action='gdpr_consent_updated',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'consent_type': validated_data['consent_type'],
                'consent_status': validated_data['consent_status'],
                'legal_basis': validated_data['legal_basis'],
                'purpose_description': validated_data.get('purpose_description', ''),
                'action': 'granted' if validated_data['consent_status'] else 'withdrawn'
            },
            risk_level='medium'
        )

        return validated_data


class GDPRPrivacyDashboardSerializer(serializers.Serializer):
    """
    GDPR Privacy Dashboard data serializer.

    Features:
    - Privacy settings overview
    - Data processing summary
    - Consent status tracking
    - Rights exercise history
    """

    privacy_settings = serializers.DictField(read_only=True)
    data_processing_purposes = serializers.ListField(read_only=True)
    consent_status = serializers.DictField(read_only=True)
    rights_exercise_history = serializers.ListField(read_only=True)
    data_retention_info = serializers.DictField(read_only=True)
    third_party_sharing = serializers.DictField(read_only=True)
    security_measures = serializers.DictField(read_only=True)


class GDPRDataRetentionSerializer(serializers.Serializer):
    """
    GDPR Data Retention Policy serializer.

    Features:
    - Data retention period management
    - Automatic cleanup configuration
    - Retention policy compliance
    - Data lifecycle tracking
    """

    data_category = serializers.ChoiceField(
        choices=[
            ('profile_data', 'Profile information'),
            ('session_logs', 'Session logs'),
            ('audit_logs', 'Audit logs'),
            ('communication_logs', 'Communication logs'),
            ('support_tickets', 'Support tickets'),
            ('analytics_data', 'Analytics data')
        ],
        required=True,
        help_text="Category of data for retention policy"
    )
    retention_period_months = serializers.IntegerField(
        min_value=1,
        max_value=120,
        required=True,
        help_text="Retention period in months"
    )
    auto_cleanup_enabled = serializers.BooleanField(
        default=True,
        help_text="Whether to automatically cleanup expired data"
    )
    cleanup_notification = serializers.BooleanField(
        default=True,
        help_text="Whether to notify user before cleanup"
    )

    def validate_retention_period_months(self, value):
        """Validate retention period is within legal limits."""
        # Most jurisdictions require reasonable retention periods
        if value > 84:  # 7 years
            raise serializers.ValidationError(
                _("Retention period cannot exceed 7 years (84 months).")
            )
        return value

    def create(self, validated_data):
        """Create retention policy with audit logging."""
        request = self.context.get('request')

        # Log the retention policy change
        AuditLog.objects.create(
            user=request.user,
            action='gdpr_retention_policy_updated',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'data_category': validated_data['data_category'],
                'retention_period_months': validated_data['retention_period_months'],
                'auto_cleanup_enabled': validated_data['auto_cleanup_enabled'],
                'cleanup_notification': validated_data['cleanup_notification']
            },
            risk_level='low'
        )

        return validated_data


class GDPRDataCleanupSerializer(serializers.Serializer):
    """
    GDPR Data Cleanup Operation serializer.

    Features:
    - Manual data cleanup requests
    - Cleanup scope specification
    - Confirmation requirements
    - Cleanup impact assessment
    """

    cleanup_scope = serializers.MultipleChoiceField(
        choices=[
            ('expired_sessions', 'Expired session data'),
            ('old_audit_logs', 'Old audit logs (>2 years)'),
            ('temporary_files', 'Temporary files'),
            ('cached_data', 'Cached data'),
            ('analytics_data', 'Old analytics data'),
            ('support_data', 'Resolved support tickets')
        ],
        required=True,
        help_text="Scope of data to cleanup"
    )
    confirm_cleanup = serializers.BooleanField(
        required=True,
        help_text="Confirmation that cleanup should proceed"
    )
    preserve_legal_hold = serializers.BooleanField(
        default=True,
        help_text="Whether to preserve data under legal hold"
    )
    cleanup_reason = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="Reason for manual cleanup"
    )

    def validate_confirm_cleanup(self, value):
        """Ensure cleanup is confirmed."""
        if not value:
            raise serializers.ValidationError(
                _("You must confirm the cleanup operation to proceed.")
            )
        return value

    def create(self, validated_data):
        """Create cleanup request with audit logging."""
        request = self.context.get('request')

        # Log the cleanup request
        AuditLog.objects.create(
            user=request.user,
            action='gdpr_data_cleanup_requested',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'cleanup_scope': validated_data['cleanup_scope'],
                'preserve_legal_hold': validated_data['preserve_legal_hold'],
                'cleanup_reason': validated_data.get('cleanup_reason', ''),
                'confirmed': validated_data['confirm_cleanup']
            },
            risk_level='medium'
        )

        return validated_data