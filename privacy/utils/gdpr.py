"""
GDPR Compliance Utilities for Vineyard Group Fellowship Authentication

This module provides comprehensive GDPR compliance features including:
- Data export (Right to Data Portability            'failed_login_attempts': AuditLog.objects.filter(
                user=self.user,
                action='login_failed',
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count(),ata erasure (Right to be Forgotten)
- Consent management
- Privacy controls
- Data retention policies
- Audit logging for privacy actions

Created: October 2025
"""

import json
import zipfile
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from io import BytesIO
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.serializers import serialize
from django.apps import apps

from authentication.models import User, AuditLog, PasswordHistory
from profiles.models import UserProfileBasic
from privacy.models import PrivacyProfile, ConsentLog

User = get_user_model()


class GDPRDataExporter:
    """
    Handles GDPR Article 20 - Right to Data Portability

    Exports all user data in machine-readable JSON format with:
    - User account information
    - Profile data and preferences
    - Session history
    - Activity logs
    - Privacy settings
    """

    def __init__(self, user: User):
        self.user = user
        self.export_timestamp = timezone.now()

    def export_user_data(self) -> Dict[str, Any]:
        """
        Export comprehensive user data for GDPR compliance.

        Returns:
            Dict containing all user data in structured format
        """
        data = {
            'export_metadata': {
                'exported_at': self.export_timestamp.isoformat(),
                'export_format': 'JSON',
                'gdpr_article': 'Article 20 - Right to Data Portability',
                'user_id': str(self.user.id),
                'username': self.user.username,
            },
            'account_data': self._export_account_data(),
            'profile_data': self._export_profile_data(),
            'session_data': self._export_session_data(),
            'privacy_data': self._export_privacy_data(),
            'activity_data': self._export_activity_data(),
            'security_data': self._export_security_data(),
        }

        return data

    def _export_account_data(self) -> Dict[str, Any]:
        """Export basic account information."""
        return {
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'date_joined': self.user.date_joined.isoformat(),
            'last_login': self.user.last_login.isoformat() if self.user.last_login else None,
            'is_active': self.user.is_active,
            'email_verified': self.user.email_verified,
            'email_verified_at': self.user.email_verified_at.isoformat() if self.user.email_verified_at else None,
        }

    def _export_profile_data(self) -> Dict[str, Any]:
        """Export user profile and preferences."""
        try:
            profile = self.user.basic_profile
            return {
                'display_name': profile.display_name,
                'bio': profile.bio,
                'timezone': profile.timezone,
                'profile_visibility': profile.profile_visibility,
                'show_activity_status': profile.show_activity_status,
                'allow_direct_messages': profile.allow_direct_messages,
                'email_notifications': profile.email_notifications,
                'push_notifications': profile.push_notifications,
                'community_notifications': profile.community_notifications,
                'emergency_notifications': profile.emergency_notifications,
                'created_at': profile.created_at.isoformat(),
                'updated_at': profile.updated_at.isoformat(),
            }
        except UserProfileBasic.DoesNotExist:
            return {}

    def _export_session_data(self) -> List[Dict[str, Any]]:
        """Export session history and device information."""
        sessions = UserSession.objects.filter(
            user=self.user).order_by('-created_at')
        return [
            {
                'session_id': str(session.id),
                'device_name': session.device_name,
                'ip_address': session.ip_address,
                'user_agent': session.user_agent,
                'location': session.city,
                'is_active': session.is_active,
                'created_at': session.created_at.isoformat(),
                'last_activity': session.last_activity_at.isoformat(),
                'expires_at': session.expires_at.isoformat() if session.expires_at else None,
            }
            for session in sessions
        ]

    def _export_privacy_data(self) -> Dict[str, Any]:
        """Export privacy settings and consent records."""
        try:
            privacy_profile = PrivacyProfile.objects.get(user=self.user)
            return {
                'marketing_consent': privacy_profile.marketing_consent,
                'analytics_consent': getattr(privacy_profile, 'analytics_consent', False),
                'marketing_consent_date': privacy_profile.marketing_consent_at.isoformat() if privacy_profile.marketing_consent_at else None,
                'analytics_consent_date': getattr(privacy_profile, 'analytics_consent_at', None),
                'data_retention_preference': privacy_profile.data_retention_preference,
                'last_privacy_update': privacy_profile.updated_at.isoformat() if hasattr(privacy_profile, 'updated_at') and privacy_profile.updated_at else None,
                'privacy_policy_version': privacy_profile.privacy_policy_version,
                'terms_accepted_date': privacy_profile.terms_of_service_accepted_at.isoformat() if privacy_profile.terms_of_service_accepted_at else None,
            }
        except PrivacyProfile.DoesNotExist:
            return {}

    def _export_activity_data(self) -> List[Dict[str, Any]]:
        """Export user activity and audit logs."""
        logs = AuditLog.objects.filter(user=self.user).order_by(
            '-created_at')[:1000]  # Last 1000 activities
        return [
            {
                'action': log.action,
                'timestamp': log.created_at.isoformat(),
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'details': log.details,
                'session_key': log.session_key,
            }
            for log in logs
        ]

    def _export_security_data(self) -> Dict[str, Any]:
        """Export security-related information."""
        password_history = PasswordHistory.objects.filter(
            user=self.user).order_by('-created_at')[:10]

        return {
            'password_history': [
                {
                    'created_at': ph.created_at.isoformat(),
                    'password_strength': ph.password_strength,
                    'was_breached': ph.was_breached,
                }
                for ph in password_history
            ],
            'two_factor_enabled': getattr(self.user, 'totpdevice_set', None) is not None,
            'failed_login_attempts': AuditLog.objects.filter(
                user=self.user,
                action='login_failed',
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
        }

    def create_export_file(self) -> BytesIO:
        """
        Create a ZIP file containing the user's data export.

        Returns:
            BytesIO object containing the ZIP file
        """
        data = self.export_user_data()

        # Create ZIP file in memory
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add main data export
            zip_file.writestr(
                'user_data_export.json',
                json.dumps(data, indent=2, ensure_ascii=False)
            )

            # Add export summary
            summary = {
                'export_summary': {
                    'user': self.user.username,
                    'exported_at': self.export_timestamp.isoformat(),
                    'total_sessions': len(data['session_data']),
                    'total_activities': len(data['activity_data']),
                    'data_categories': list(data.keys()),
                }
            }
            zip_file.writestr(
                'export_summary.json',
                json.dumps(summary, indent=2, ensure_ascii=False)
            )

            # Add privacy notice
            privacy_notice = """
GDPR Data Export - Privacy Notice

This export contains all personal data we hold about you in accordance with
Article 20 of the General Data Protection Regulation (GDPR) - Right to Data Portability.

The data is provided in machine-readable JSON format and includes:
- Account information and profile data
- Session history and device information
- Privacy settings and consent records
- Activity logs and security information

This export was generated on: {export_time}

For questions about this export or your privacy rights, please contact our
Data Protection Officer at: privacy@Vineyard Group Fellowship.app

Your rights under GDPR include:
- Right of access (Article 15)
- Right to rectification (Article 16)
- Right to erasure (Article 17)
- Right to restrict processing (Article 18)
- Right to data portability (Article 20)
- Right to object (Article 21)
            """.format(export_time=self.export_timestamp.isoformat())

            zip_file.writestr('PRIVACY_NOTICE.txt', privacy_notice)

        zip_buffer.seek(0)
        return zip_buffer


class GDPRDataEraser:
    """
    Handles GDPR Article 17 - Right to Erasure (Right to be Forgotten)

    Provides comprehensive data deletion with:
    - User data anonymization
    - Related data cleanup
    - Audit trail preservation
    - Cascading deletion handling
    """

    def __init__(self, user: User):
        self.user = user
        self.erasure_timestamp = timezone.now()
        self.anonymized_id = f"deleted_{self.user.id}_{int(self.erasure_timestamp.timestamp())}"

    def initiate_erasure(self, reason: str = "User request", retain_audit: bool = True) -> Dict[str, Any]:
        """
        Initiate comprehensive data erasure process.

        Args:
            reason: Reason for erasure (for audit purposes)
            retain_audit: Whether to retain anonymized audit logs

        Returns:
            Dict containing erasure summary
        """
        with transaction.atomic():
            # Create erasure audit log first
            self._create_erasure_audit(reason)

            # Perform data erasure
            erasure_summary = {
                'user_id': str(self.user.id),
                'username': self.user.username,
                'erasure_initiated_at': self.erasure_timestamp.isoformat(),
                'reason': reason,
                'retain_audit_logs': retain_audit,
                'anonymized_id': self.anonymized_id,
                'erased_data': {},
            }

            # Erase profile data
            erasure_summary['erased_data']['profile'] = self._erase_profile_data()

            # Erase session data
            erasure_summary['erased_data']['sessions'] = self._erase_session_data()

            # Erase sensitive data
            erasure_summary['erased_data']['sensitive_data'] = self._erase_sensitive_data(
            )

            # Erase security data
            erasure_summary['erased_data']['security'] = self._erase_security_data()

            # Handle audit logs
            if retain_audit:
                erasure_summary['erased_data']['audit_logs'] = self._anonymize_audit_logs(
                )
            else:
                erasure_summary['erased_data']['audit_logs'] = self._erase_audit_logs(
                )

            # Finally, anonymize user account
            erasure_summary['erased_data']['account'] = self._anonymize_user_account()

            return erasure_summary

    def _create_erasure_audit(self, reason: str):
        """Create audit log for erasure initiation."""
        AuditLog.objects.create(
            user=self.user,
            action='gdpr_erasure_initiated',
            ip_address='127.0.0.1',  # System initiated
            user_agent='GDPR Compliance System',
            details={
                'reason': reason,
                'erasure_timestamp': self.erasure_timestamp.isoformat(),
                'anonymized_id': self.anonymized_id,
                'gdpr_article': 'Article 17 - Right to Erasure',
            }
        )

    def _erase_profile_data(self) -> Dict[str, Any]:
        """Erase user profile data."""
        try:
            profile = self.user.basic_profile

            erased_fields = {
                'display_name': profile.display_name,
                'bio': profile.bio,
            }

            # Clear profile data
            profile.display_name = ""
            profile.bio = ""
            profile.profile_visibility = 'private'
            profile.save()

            return {'status': 'erased', 'fields_cleared': list(erased_fields.keys())}
        except UserProfileBasic.DoesNotExist:
            return {'status': 'no_profile_found'}

    def _erase_session_data(self) -> Dict[str, Any]:
        """Erase user session data."""
        sessions = UserSession.objects.filter(user=self.user)
        session_count = sessions.count()

        # Delete all sessions
        sessions.delete()

        return {'status': 'erased', 'sessions_deleted': session_count}

    def _erase_sensitive_data(self) -> Dict[str, Any]:
        """Erase sensitive user data."""
        try:
            privacy_profile = PrivacyProfile.objects.get(user=self.user)
            privacy_profile.delete()
            return {'status': 'erased'}
        except PrivacyProfile.DoesNotExist:
            return {'status': 'no_sensitive_data_found'}

    def _erase_security_data(self) -> Dict[str, Any]:
        """Erase security-related data."""
        password_history = PasswordHistory.objects.filter(user=self.user)
        history_count = password_history.count()

        # Delete password history
        password_history.delete()

        return {'status': 'erased', 'password_history_deleted': history_count}

    def _anonymize_audit_logs(self) -> Dict[str, Any]:
        """Anonymize audit logs while retaining for compliance."""
        logs = AuditLog.objects.filter(user=self.user)
        log_count = logs.count()

        # Update logs to remove user reference but keep anonymized record
        logs.update(
            user=None,
            details=f"[ANONYMIZED] Original user: {self.anonymized_id}"
        )

        return {'status': 'anonymized', 'logs_anonymized': log_count}

    def _erase_audit_logs(self) -> Dict[str, Any]:
        """Completely erase audit logs."""
        logs = AuditLog.objects.filter(user=self.user)
        log_count = logs.count()

        logs.delete()

        return {'status': 'erased', 'logs_deleted': log_count}

    def _anonymize_user_account(self) -> Dict[str, Any]:
        """Anonymize the user account itself."""
        original_data = {
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
        }

        # Anonymize account data
        self.user.username = self.anonymized_id
        self.user.email = f"{self.anonymized_id}@deleted.local"
        self.user.first_name = ""
        self.user.last_name = ""
        self.user.is_active = False
        self.user.save()

        return {'status': 'anonymized', 'original_username': original_data['username']}


class GDPRConsentManager:
    """
    Manages GDPR consent and privacy preferences.

    Handles:
    - Consent recording and withdrawal
    - Privacy policy version tracking
    - Lawful basis documentation
    - Consent analytics
    """

    def __init__(self, user: User):
        self.user = user

    def record_consent(self, consent_type: str, granted: bool, lawful_basis: str = None) -> Dict[str, Any]:
        """
        Record user consent for specific data processing.

        Args:
            consent_type: Type of consent (marketing, analytics, etc.)
            granted: Whether consent was granted
            lawful_basis: Legal basis for processing

        Returns:
            Dict containing consent record details
        """
        privacy_profile, created = PrivacyProfile.objects.get_or_create(
            user=self.user
        )

        # Create consent log entry
        ConsentLog.objects.create(
            user=self.user,
            consent_type=consent_type,
            action='given' if granted else 'withdrawn',
            consent_given=granted,
            version=self._get_current_privacy_version(),
            notes=f"Consent {('granted' if granted else 'withdrawn')} via API"
        )

        consent_record = {
            'consent_type': consent_type,
            'granted': granted,
            'recorded_at': timezone.now().isoformat(),
            'lawful_basis': lawful_basis or 'consent',
            'privacy_policy_version': self._get_current_privacy_version(),
        }

        # Update specific consent fields
        if consent_type == 'marketing':
            privacy_profile.marketing_consent = granted
            privacy_profile.marketing_consent_at = timezone.now()
        elif consent_type == 'analytics':
            # Note: analytics_consent not in PrivacyProfile model, treating as general data processing
            privacy_profile.data_processing_consent = granted
            privacy_profile.data_processing_consent_at = timezone.now()

        privacy_profile.save()

        # Create audit log
        AuditLog.objects.create(
            user=self.user,
            action=f'consent_{consent_type}_{"granted" if granted else "withdrawn"}',
            details=consent_record
        )

        return consent_record

    def withdraw_all_consent(self) -> Dict[str, Any]:
        """Withdraw all user consent."""
        try:
            privacy_profile = PrivacyProfile.objects.get(user=self.user)

            withdrawn_consents = []
            if privacy_profile.marketing_consent:
                withdrawn_consents.append('marketing')
                privacy_profile.marketing_consent = False
                privacy_profile.marketing_consent_at = timezone.now()

            if privacy_profile.data_processing_consent:
                withdrawn_consents.append('data_processing')
                privacy_profile.data_processing_consent = False
                privacy_profile.data_processing_consent_at = timezone.now()

            privacy_profile.save()

            # Create consent log entries for each withdrawal
            for consent_type in withdrawn_consents:
                ConsentLog.objects.create(
                    user=self.user,
                    consent_type=consent_type,
                    action='withdrawn',
                    consent_given=False,
                    notes="All consent withdrawn via API"
                )

            # Create audit log
            AuditLog.objects.create(
                user=self.user,
                action='consent_all_withdrawn',
                details={
                    'withdrawn_consents': withdrawn_consents,
                    'withdrawal_timestamp': timezone.now().isoformat(),
                }
            )

            return {
                'status': 'success',
                'withdrawn_consents': withdrawn_consents,
                'withdrawal_timestamp': timezone.now().isoformat(),
            }

        except PrivacyProfile.DoesNotExist:
            return {'status': 'no_consent_data_found'}

    def get_consent_history(self) -> List[Dict[str, Any]]:
        """Get complete consent history for user."""
        consent_logs = AuditLog.objects.filter(
            user=self.user,
            action__contains='consent'
        ).order_by('-created_at')

        return [
            {
                'action': log.action,
                'timestamp': log.created_at.isoformat(),
                'details': log.details,
            }
            for log in consent_logs
        ]

    def _get_current_privacy_version(self) -> str:
        """Get current privacy policy version."""
        return getattr(settings, 'PRIVACY_POLICY_VERSION', '1.0')


class GDPRDataRetentionManager:
    """
    Manages data retention policies and automatic cleanup.

    Features:
    - Configurable retention periods
    - Automatic data cleanup
    - Retention policy enforcement
    - Compliance reporting
    """

    # Default retention periods (in days)
    DEFAULT_RETENTION_PERIODS = {
        'user_sessions': 365,       # 1 year
        'audit_logs': 730,          # 2 years
        'password_history': 365,    # 1 year
        'inactive_accounts': 1095,  # 3 years
    }

    def __init__(self):
        self.retention_periods = getattr(
            settings,
            'GDPR_RETENTION_PERIODS',
            self.DEFAULT_RETENTION_PERIODS
        )

    def cleanup_expired_data(self) -> Dict[str, Any]:
        """
        Clean up expired data according to retention policies.

        Returns:
            Dict containing cleanup summary
        """
        cleanup_summary = {
            'cleanup_timestamp': timezone.now().isoformat(),
            'retention_periods': self.retention_periods,
            'cleaned_data': {},
        }

        # Clean up old sessions
        cleanup_summary['cleaned_data']['sessions'] = self._cleanup_old_sessions()

        # Clean up old audit logs
        cleanup_summary['cleaned_data']['audit_logs'] = self._cleanup_old_audit_logs()

        # Clean up old password history
        cleanup_summary['cleaned_data']['password_history'] = self._cleanup_old_password_history()

        # Clean up inactive accounts
        cleanup_summary['cleaned_data']['inactive_accounts'] = self._cleanup_inactive_accounts()

        return cleanup_summary

    def _cleanup_old_sessions(self) -> Dict[str, Any]:
        """Clean up expired user sessions."""
        cutoff_date = timezone.now() - \
            timedelta(days=self.retention_periods['user_sessions'])

        old_sessions = UserSession.objects.filter(
            last_activity_at__lt=cutoff_date,
            is_active=False
        )

        session_count = old_sessions.count()
        old_sessions.delete()

        return {
            'deleted_count': session_count,
            'cutoff_date': cutoff_date.isoformat(),
        }

    def _cleanup_old_audit_logs(self) -> Dict[str, Any]:
        """Clean up old audit logs."""
        cutoff_date = timezone.now() - \
            timedelta(days=self.retention_periods['audit_logs'])

        old_logs = AuditLog.objects.filter(created_at__lt=cutoff_date)

        log_count = old_logs.count()
        old_logs.delete()

        return {
            'deleted_count': log_count,
            'cutoff_date': cutoff_date.isoformat(),
        }

    def _cleanup_old_password_history(self) -> Dict[str, Any]:
        """Clean up old password history."""
        cutoff_date = timezone.now() - \
            timedelta(days=self.retention_periods['password_history'])

        old_passwords = PasswordHistory.objects.filter(
            created_at__lt=cutoff_date)

        password_count = old_passwords.count()
        old_passwords.delete()

        return {
            'deleted_count': password_count,
            'cutoff_date': cutoff_date.isoformat(),
        }

    def _cleanup_inactive_accounts(self) -> Dict[str, Any]:
        """Clean up inactive user accounts."""
        cutoff_date = timezone.now() - \
            timedelta(days=self.retention_periods['inactive_accounts'])

        inactive_users = User.objects.filter(
            last_login__lt=cutoff_date,
            is_active=False
        )

        user_count = inactive_users.count()

        # For inactive accounts, we anonymize rather than delete
        anonymized_count = 0
        for user in inactive_users:
            eraser = GDPRDataEraser(user)
            eraser.initiate_erasure(
                reason="Automatic cleanup - inactive account")
            anonymized_count += 1

        return {
            'anonymized_count': anonymized_count,
            'cutoff_date': cutoff_date.isoformat(),
        }
