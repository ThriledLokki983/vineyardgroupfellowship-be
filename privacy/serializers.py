"""
Privacy app serializers for Vineyard Group Fellowship platform.

This module contains DRF serializers for privacy and GDPR functionality:
- GDPR consent management (privacy policy, terms of service)
- Data export requests (Article 20 - Right to Data Portability)
- Data erasure requests (Article 17 - Right to be Forgotten)
- Privacy preferences and settings
- Consent log tracking

Phase 2: Clean architecture - only privacy concerns, no cross-app imports.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import PrivacyProfile, ConsentLog, DataProcessingRecord

User = get_user_model()


class PrivacyProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for privacy profile and consent management.

    Handles GDPR consent tracking and privacy preferences.
    """
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = PrivacyProfile
        fields = (
            'username', 'privacy_policy_accepted', 'privacy_policy_accepted_at',
            'privacy_policy_version', 'terms_of_service_accepted',
            'terms_of_service_accepted_at', 'terms_of_service_version',
            'data_processing_consent', 'data_processing_consent_at',
            'marketing_consent', 'marketing_consent_at',
            'research_participation_consent', 'research_participation_consent_at',
            'profile_visibility', 'recovery_info_visibility', 'contact_preferences',
            'data_retention_preference', 'auto_delete_inactive_data',
            'deletion_requested', 'deletion_requested_at',
            'data_export_requested', 'data_export_requested_at',
            'anonymize_posts_on_deletion', 'anonymize_recovery_data',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'username', 'privacy_policy_accepted_at', 'terms_of_service_accepted_at',
            'data_processing_consent_at', 'marketing_consent_at',
            'research_participation_consent_at',
            'deletion_requested_at', 'data_export_requested_at',
            'created_at', 'updated_at'
        )

    def update(self, instance, validated_data):
        """Update privacy profile with consent tracking."""
        # Track consent changes
        current_time = timezone.now()

        # Privacy policy consent
        if 'privacy_policy_accepted' in validated_data:
            if validated_data['privacy_policy_accepted'] != instance.privacy_policy_accepted:
                validated_data['privacy_policy_accepted_at'] = current_time
                if validated_data['privacy_policy_accepted']:
                    # Log consent given
                    ConsentLog.objects.create(
                        user=instance.user,
                        consent_type='privacy_policy',
                        action='given',
                        consent_given=True,
                        version=validated_data.get(
                            'privacy_policy_version', '1.0'),
                        user_agent='Test Client'
                    )

        # Terms of service consent
        if 'terms_of_service_accepted' in validated_data:
            if validated_data['terms_of_service_accepted'] != instance.terms_of_service_accepted:
                validated_data['terms_of_service_accepted_at'] = current_time
                if validated_data['terms_of_service_accepted']:
                    # Log consent given
                    ConsentLog.objects.create(
                        user=instance.user,
                        consent_type='terms_of_service',
                        action='given',
                        consent_given=True,
                        version=validated_data.get(
                            'terms_of_service_version', '1.0'),
                        user_agent='Test Client'
                    )

        # Marketing consent
        if 'marketing_consent' in validated_data:
            if validated_data['marketing_consent'] != instance.marketing_consent:
                validated_data['marketing_consent_at'] = current_time
                action = 'given' if validated_data['marketing_consent'] else 'withdrawn'
                ConsentLog.objects.create(
                    user=instance.user,
                    consent_type='marketing',
                    action=action,
                    consent_given=validated_data['marketing_consent'],
                    user_agent='Test Client'
                )

        # Data processing consent
        if 'data_processing_consent' in validated_data:
            if validated_data['data_processing_consent'] != instance.data_processing_consent:
                validated_data['data_processing_consent_at'] = current_time
                action = 'given' if validated_data['data_processing_consent'] else 'withdrawn'
                ConsentLog.objects.create(
                    user=instance.user,
                    consent_type='data_processing',
                    action=action,
                    consent_given=validated_data['data_processing_consent'],
                    user_agent='Test Client'
                )

        return super().update(instance, validated_data)


class ConsentLogSerializer(serializers.ModelSerializer):
    """
    Serializer for consent log entries.

    Read-only serializer for GDPR audit trails.
    """
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ConsentLog
        fields = (
            'id', 'username', 'consent_type', 'action', 'consent_given',
            'version', 'user_agent', 'reason', 'expires_at', 'created_at'
        )
        read_only_fields = (
            'id', 'username', 'consent_type', 'action', 'consent_given',
            'version', 'user_agent', 'reason', 'expires_at', 'created_at'
        )


class DataProcessingRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for data processing records.

    Tracks what data is processed and why (GDPR Article 30).
    """
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = DataProcessingRecord
        fields = (
            'id', 'username', 'purpose', 'data_categories',
            'legal_basis', 'retention_period_days', 'started_at',
            'ended_at', 'is_active', 'notes'
        )
        read_only_fields = ('id', 'username', 'started_at', 'ended_at')


class GDPRDataExportSerializer(serializers.Serializer):
    """
    GDPR Article 20 - Right to Data Portability.

    Handles data export requests.
    """
    export_format = serializers.ChoiceField(
        choices=[('json', 'JSON'), ('csv', 'CSV')],
        default='json',
        help_text="Format for data export"
    )
    include_consent_history = serializers.BooleanField(
        default=True,
        help_text="Include consent history in export"
    )
    include_processing_records = serializers.BooleanField(
        default=True,
        help_text="Include data processing records in export"
    )
    privacy_notice_acknowledged = serializers.BooleanField(
        required=True,
        help_text="User acknowledges they have read the privacy notice"
    )

    def validate_privacy_notice_acknowledged(self, value):
        """Ensure privacy notice is acknowledged."""
        if not value:
            raise serializers.ValidationError(
                "You must acknowledge that you have read the privacy notice"
            )
        return value

    def save(self):
        """Process data export request."""
        user = self.context['request'].user

        # Log the export request
        ConsentLog.objects.create(
            user=user,
            consent_type='data_export',
            action='given',
            consent_given=True,
            ip_address=self.context['request'].META.get('REMOTE_ADDR'),
            user_agent=self.context['request'].META.get(
                'HTTP_USER_AGENT', 'Test Client'),
            reason=f"Export format: {self.validated_data['export_format']}"
        )

        # Return the validated data for processing
        return self.validated_data


class GDPRDataErasureSerializer(serializers.Serializer):
    """
    GDPR Article 17 - Right to be Forgotten.

    Handles data erasure requests.
    """
    reason = serializers.ChoiceField(
        choices=[
            ('no_longer_necessary', 'Data no longer necessary for original purpose'),
            ('withdraw_consent', 'Withdrawing consent'),
            ('unlawful_processing', 'Data processed unlawfully'),
            ('legal_compliance', 'Erasure required for legal compliance'),
            ('child_data', 'Data collected from a child')
        ],
        required=True,
        help_text="Reason for data erasure request"
    )
    confirm_understanding = serializers.BooleanField(
        required=True,
        help_text="User confirms they understand the consequences of data erasure"
    )
    confirm_irreversible = serializers.BooleanField(
        required=True,
        help_text="User confirms they understand this action is irreversible"
    )

    def validate_confirm_understanding(self, value):
        """Ensure user understands consequences."""
        if not value:
            raise serializers.ValidationError(
                "You must confirm that you understand the consequences of data erasure"
            )
        return value

    def validate_confirm_irreversible(self, value):
        """Ensure user understands irreversibility."""
        if not value:
            raise serializers.ValidationError(
                "You must confirm that you understand this action is irreversible"
            )
        return value

    def save(self):
        """Process data erasure request."""
        user = self.context['request'].user

        # Log the erasure request
        ConsentLog.objects.create(
            user=user,
            consent_type='data_processing',  # Use valid consent type
            action='withdrawn',
            consent_given=False,
            ip_address=self.context['request'].META.get('REMOTE_ADDR'),
            user_agent=self.context['request'].META.get(
                'HTTP_USER_AGENT', 'Test Client'),
            reason=f"Reason: {self.validated_data['reason']}"
        )

        # Return the validated data for processing
        return self.validated_data


class ConsentUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating specific consent preferences.
    """
    consent_type = serializers.ChoiceField(
        choices=[
            ('marketing', 'Marketing Communications'),
            ('data_processing', 'Data Processing'),
            ('analytics', 'Analytics'),
            ('third_party', 'Third Party Sharing')
        ],
        required=True
    )
    granted = serializers.BooleanField(required=True)

    def save(self):
        """Update consent preference."""
        user = self.context['request'].user
        consent_type = self.validated_data['consent_type']
        granted = self.validated_data['granted']

        # Get or create privacy profile
        privacy_profile, created = PrivacyProfile.objects.get_or_create(
            user=user)

        # Update the specific consent
        current_time = timezone.now()
        if consent_type == 'marketing':
            privacy_profile.marketing_consent = granted
            privacy_profile.marketing_consent_at = current_time
        elif consent_type == 'data_processing':
            privacy_profile.data_processing_consent = granted
            privacy_profile.data_processing_consent_at = current_time

        privacy_profile.save()

        # Log the consent change
        action = 'given' if granted else 'withdrawn'
        ConsentLog.objects.create(
            user=user,
            consent_type=consent_type,
            action=action,
            consent_given=granted,
            ip_address=self.context['request'].META.get('REMOTE_ADDR'),
            user_agent=self.context['request'].META.get(
                'HTTP_USER_AGENT', 'Test Client')
        )

        return privacy_profile


class PrivacyDashboardSerializer(serializers.Serializer):
    """
    Read-only serializer for privacy dashboard.

    Combines privacy profile, consent history, and data processing info.
    """
    profile = PrivacyProfileSerializer(read_only=True)
    recent_consent_changes = ConsentLogSerializer(many=True, read_only=True)
    active_processing_records = DataProcessingRecordSerializer(
        many=True, read_only=True)
    data_summary = serializers.DictField(read_only=True)

    def to_representation(self, instance):
        """Custom representation for privacy dashboard."""
        user = instance

        try:
            privacy_profile = user.privacy_profile
        except PrivacyProfile.DoesNotExist:
            privacy_profile = None

        # Get recent consent changes (last 30 days)
        recent_consents = ConsentLog.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timezone.timedelta(days=30)
        ).order_by('-timestamp')[:10]

        # Get active processing records
        active_records = DataProcessingRecord.objects.filter(
            user=user,
            processing_end__isnull=True
        )

        # Create data summary
        data_summary = {
            'consent_logs_count': ConsentLog.objects.filter(user=user).count(),
            'processing_records_count': DataProcessingRecord.objects.filter(user=user).count(),
            'last_privacy_update': privacy_profile.updated_at if privacy_profile else None,
            'has_active_consents': privacy_profile.marketing_consent or privacy_profile.data_processing_consent if privacy_profile else False
        }

        return {
            'profile': PrivacyProfileSerializer(privacy_profile).data if privacy_profile else None,
            'recent_consent_changes': ConsentLogSerializer(recent_consents, many=True).data,
            'active_processing_records': DataProcessingRecordSerializer(active_records, many=True).data,
            'data_summary': data_summary
        }


# Aliases for backward compatibility with existing views
GDPRConsentSerializer = ConsentUpdateSerializer
GDPRPrivacyDashboardSerializer = PrivacyDashboardSerializer


class GDPRDataRetentionSerializer(serializers.Serializer):
    """
    Serializer for data retention settings.
    """
    retention_period = serializers.IntegerField(min_value=30, max_value=3650)
    auto_delete = serializers.BooleanField(default=False)


class GDPRDataCleanupSerializer(serializers.Serializer):
    """
    Serializer for data cleanup operations.
    """
    cleanup_type = serializers.ChoiceField(
        choices=[
            ('old_sessions', 'Old Sessions'),
            ('expired_tokens', 'Expired Tokens'),
            ('audit_logs', 'Old Audit Logs')
        ]
    )
    confirm = serializers.BooleanField(required=True)
