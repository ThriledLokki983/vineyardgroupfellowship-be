from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()


class PrivacyProfile(models.Model):
    """
    Privacy and consent management for users.

    Extracted from authentication.UserProfile to handle GDPR compliance,
    consent tracking, and privacy preferences in a dedicated app.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='privacy_profile'
    )

    # === GDPR & Legal Consent ===
    privacy_policy_accepted = models.BooleanField(
        default=False,
        help_text="User has accepted the current privacy policy"
    )
    privacy_policy_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user accepted privacy policy"
    )
    privacy_policy_version = models.CharField(
        max_length=10,
        blank=True,
        help_text="Version of privacy policy accepted (e.g., '1.2')"
    )

    terms_of_service_accepted = models.BooleanField(
        default=False,
        help_text="User has accepted the current terms of service"
    )
    terms_of_service_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user accepted terms of service"
    )
    terms_of_service_version = models.CharField(
        max_length=10,
        blank=True,
        help_text="Version of terms of service accepted"
    )

    # === Data Processing Consent ===
    data_processing_consent = models.BooleanField(
        default=False,
        help_text="Consent for processing personal data"
    )
    data_processing_consent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When data processing consent was given"
    )

    marketing_consent = models.BooleanField(
        default=False,
        help_text="Consent for marketing communications"
    )
    marketing_consent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When marketing consent was given"
    )

    research_participation_consent = models.BooleanField(
        default=False,
        help_text="Consent for participation in research studies"
    )
    research_participation_consent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When research consent was given"
    )

    # === Privacy Preferences ===
    profile_visibility = models.CharField(
        max_length=20,
        choices=[
            ('private', 'Private - Only visible to me'),
            ('friends', 'Friends - Visible to my connections'),
            ('community', 'Community - Visible to community members'),
            ('public', 'Public - Visible to everyone'),
        ],
        default='community',
        help_text="Who can see user's profile information"
    )

    recovery_info_visibility = models.CharField(
        max_length=20,
        choices=[
            ('private', 'Private - Only visible to me'),
            ('friends', 'Friends - Visible to my connections'),
            ('supporters', 'Supporters - Visible to verified supporters'),
            ('community', 'Community - Visible to community members'),
        ],
        default='private',
        help_text="Who can see recovery information and progress"
    )

    contact_preferences = models.CharField(
        max_length=20,
        choices=[
            ('no_contact', 'No Contact - Don\'t contact me'),
            ('email_only', 'Email Only - Emergency notifications only'),
            ('limited', 'Limited - Important updates only'),
            ('normal', 'Normal - Regular communications'),
            ('all', 'All - All communications and updates'),
        ],
        default='normal',
        help_text="Communication preferences for platform notifications"
    )

    # === Data Retention Preferences ===
    data_retention_preference = models.CharField(
        max_length=20,
        choices=[
            ('minimal', 'Minimal - 1 year retention'),
            ('standard', 'Standard - 3 years retention'),
            ('extended', 'Extended - 7 years retention'),
            ('permanent', 'Permanent - Keep until deletion request'),
        ],
        default='standard',
        help_text="How long to retain user data"
    )

    auto_delete_inactive_data = models.BooleanField(
        default=True,
        help_text="Automatically delete data after retention period"
    )

    # === Account Deletion & GDPR Rights ===
    deletion_requested = models.BooleanField(
        default=False,
        help_text="User has requested account deletion"
    )
    deletion_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When account deletion was requested"
    )
    deletion_scheduled_for = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When account will be automatically deleted"
    )

    data_export_requested = models.BooleanField(
        default=False,
        help_text="User has requested data export"
    )
    data_export_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When data export was requested"
    )

    # === Anonymization Preferences ===
    anonymize_posts_on_deletion = models.BooleanField(
        default=True,
        help_text="Anonymize posts instead of deleting them"
    )
    anonymize_recovery_data = models.BooleanField(
        default=False,
        help_text="Allow anonymized recovery data for research"
    )

    # === Audit Trail ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # === Consent Withdrawal Tracking ===
    consent_withdrawn_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user withdrew consent for data processing"
    )
    consent_withdrawal_reason = models.TextField(
        blank=True,
        help_text="Reason for withdrawing consent"
    )

    class Meta:
        db_table = 'privacy_profile'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['privacy_policy_accepted']),
            models.Index(fields=['deletion_requested']),
            models.Index(fields=['deletion_scheduled_for']),
        ]

    def __str__(self):
        return f"Privacy Profile for {self.user.username}"

    def accept_privacy_policy(self, version):
        """Accept privacy policy with version tracking."""
        self.privacy_policy_accepted = True
        self.privacy_policy_accepted_at = timezone.now()
        self.privacy_policy_version = version
        self.save()

    def accept_terms_of_service(self, version):
        """Accept terms of service with version tracking."""
        self.terms_of_service_accepted = True
        self.terms_of_service_accepted_at = timezone.now()
        self.terms_of_service_version = version
        self.save()

    def give_data_processing_consent(self):
        """Give consent for data processing."""
        self.data_processing_consent = True
        self.data_processing_consent_at = timezone.now()
        self.save()

    def withdraw_consent(self, reason=""):
        """Withdraw consent for data processing."""
        self.data_processing_consent = False
        self.consent_withdrawn_at = timezone.now()
        self.consent_withdrawal_reason = reason
        self.save()

    def request_deletion(self, delay_days=30):
        """Request account deletion with delay period."""
        self.deletion_requested = True
        self.deletion_requested_at = timezone.now()
        self.deletion_scheduled_for = timezone.now() + timezone.timedelta(days=delay_days)
        self.save()

    def cancel_deletion_request(self):
        """Cancel pending deletion request."""
        self.deletion_requested = False
        self.deletion_requested_at = None
        self.deletion_scheduled_for = None
        self.save()

    def request_data_export(self):
        """Request data export for GDPR compliance."""
        self.data_export_requested = True
        self.data_export_requested_at = timezone.now()
        self.save()

    @property
    def has_valid_consent(self):
        """Check if user has valid consent for data processing."""
        return (
            self.privacy_policy_accepted and
            self.terms_of_service_accepted and
            self.data_processing_consent and
            not self.consent_withdrawn_at
        )

    @property
    def is_pending_deletion(self):
        """Check if account is pending deletion."""
        return (
            self.deletion_requested and
            self.deletion_scheduled_for and
            self.deletion_scheduled_for > timezone.now()
        )

    @property
    def should_auto_delete(self):
        """Check if account should be automatically deleted."""
        return (
            self.deletion_scheduled_for and
            self.deletion_scheduled_for <= timezone.now()
        )

    def clean(self):
        """Validate privacy profile data."""
        super().clean()

        # Ensure consent timestamps are present when consent is given
        if self.privacy_policy_accepted and not self.privacy_policy_accepted_at:
            raise ValidationError("Privacy policy acceptance timestamp required")

        if self.terms_of_service_accepted and not self.terms_of_service_accepted_at:
            raise ValidationError("Terms of service acceptance timestamp required")

        if self.data_processing_consent and not self.data_processing_consent_at:
            raise ValidationError("Data processing consent timestamp required")


class ConsentLog(models.Model):
    """
    Detailed audit log for all consent-related actions.

    Maintains immutable record of consent changes for GDPR compliance
    and legal requirements.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='consent_logs'
    )

    CONSENT_TYPES = [
        ('privacy_policy', 'Privacy Policy'),
        ('terms_of_service', 'Terms of Service'),
        ('data_processing', 'Data Processing'),
        ('marketing', 'Marketing Communications'),
        ('research', 'Research Participation'),
        ('cookies', 'Cookie Usage'),
        ('analytics', 'Analytics Tracking'),
    ]

    consent_type = models.CharField(
        max_length=20,
        choices=CONSENT_TYPES,
        help_text="Type of consent being tracked"
    )

    ACTION_TYPES = [
        ('given', 'Consent Given'),
        ('withdrawn', 'Consent Withdrawn'),
        ('updated', 'Consent Updated'),
        ('expired', 'Consent Expired'),
    ]

    action = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        help_text="Action taken on consent"
    )

    consent_given = models.BooleanField(
        help_text="Whether consent was given (True) or withdrawn (False)"
    )

    version = models.CharField(
        max_length=10,
        blank=True,
        help_text="Version of document/policy consented to"
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address when consent was given/withdrawn"
    )

    user_agent = models.TextField(
        blank=True,
        help_text="Browser/device information when consent was recorded"
    )

    reason = models.TextField(
        blank=True,
        help_text="Reason for consent withdrawal or update"
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this consent expires (if applicable)"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this consent action was recorded"
    )

    class Meta:
        db_table = 'privacy_consent_log'
        indexes = [
            models.Index(fields=['user', 'consent_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.consent_type} - {self.action} - {self.created_at}"

    @classmethod
    def log_consent(cls, user, consent_type, given, version="", ip_address=None, user_agent="", reason=""):
        """Log a consent action."""
        return cls.objects.create(
            user=user,
            consent_type=consent_type,
            action='given' if given else 'withdrawn',
            consent_given=given,
            version=version,
            ip_address=ip_address,
            user_agent=user_agent,
            reason=reason
        )


class DataProcessingRecord(models.Model):
    """
    Record of data processing activities for transparency and GDPR compliance.

    Tracks what data is processed, why, and for how long.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='data_processing_records'
    )

    PROCESSING_PURPOSES = [
        ('account_management', 'Account Management'),
        ('service_provision', 'Service Provision'),
        ('communication', 'Communication'),
        ('analytics', 'Analytics'),
        ('marketing', 'Marketing'),
        ('research', 'Research'),
        ('legal_compliance', 'Legal Compliance'),
        ('security', 'Security'),
        ('recovery_support', 'Recovery Support'),
    ]

    purpose = models.CharField(
        max_length=30,
        choices=PROCESSING_PURPOSES,
        help_text="Purpose for processing this data"
    )

    data_categories = models.TextField(
        help_text="Categories of data being processed (JSON list)"
    )

    legal_basis = models.CharField(
        max_length=50,
        choices=[
            ('consent', 'Consent'),
            ('contract', 'Contract Performance'),
            ('legal_obligation', 'Legal Obligation'),
            ('vital_interests', 'Vital Interests'),
            ('public_task', 'Public Task'),
            ('legitimate_interests', 'Legitimate Interests'),
        ],
        help_text="Legal basis for processing under GDPR"
    )

    retention_period_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="How long this data will be retained (days)"
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When processing started"
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When processing ended"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether processing is currently active"
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this processing activity"
    )

    class Meta:
        db_table = 'privacy_data_processing_record'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['purpose']),
            models.Index(fields=['started_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.purpose} - {'Active' if self.is_active else 'Ended'}"

    def end_processing(self, reason=""):
        """End data processing activity."""
        self.is_active = False
        self.ended_at = timezone.now()
        if reason:
            self.notes = f"{self.notes}\nEnded: {reason}".strip()
        self.save()

    @property
    def retention_expires_at(self):
        """When retention period expires."""
        if self.retention_period_days:
            return self.started_at + timezone.timedelta(days=self.retention_period_days)
        return None

    @property
    def is_retention_expired(self):
        """Check if retention period has expired."""
        expiry = self.retention_expires_at
        return expiry and expiry <= timezone.now()
