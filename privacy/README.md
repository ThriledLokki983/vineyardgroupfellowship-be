# Privacy App

## Purpose

GDPR compliance, consent management, and privacy controls for the Vineyard Group Fellowship
platform. Handles all legal requirements for data protection and user privacy
rights.

## Responsibilities

- **Consent Management**: Track privacy policy, terms of service, and data
  processing consent
- **GDPR Compliance**: Data export, deletion requests, and right to be forgotten
- **Privacy Preferences**: Profile visibility, contact preferences, and data
  retention settings
- **Audit Logging**: Immutable consent logs for legal compliance
- **Data Processing Records**: Transparency about data usage and retention

## Key Models

### **PrivacyProfile**

Core privacy and consent information extracted from the monolithic
authentication.UserProfile:

- Legal consent tracking (privacy policy, terms of service, data processing)
- Privacy preferences (profile visibility, contact preferences)
- Data retention preferences and auto-deletion settings
- Account deletion requests and GDPR rights management
- Anonymization preferences for posts and recovery data

### **ConsentLog**

Immutable audit trail for all consent-related actions:

- Detailed logging of consent given/withdrawn
- Version tracking for legal documents
- IP address and user agent logging for verification
- Expiration tracking for time-limited consent

### **DataProcessingRecord**

Transparency records for GDPR Article 13/14 compliance:

- Purpose and legal basis for data processing
- Data categories and retention periods
- Processing activity start/end dates
- Legal basis documentation (consent, contract, etc.)

## Origin - Model Split from Authentication

🔄 **Phase 1 Refactoring**: This app was created to extract privacy and
GDPR-related functionality from the monolithic `authentication.UserProfile`
model.

**Fields Moved from UserProfile**:

- `privacy_policy_accepted` → `PrivacyProfile.privacy_policy_accepted`
- `privacy_policy_accepted_at` → `PrivacyProfile.privacy_policy_accepted_at`
- `privacy_policy_version` → `PrivacyProfile.privacy_policy_version`
- `terms_of_service_accepted` → `PrivacyProfile.terms_of_service_accepted`
- `data_processing_consent` → `PrivacyProfile.data_processing_consent`
- `marketing_consent` → `PrivacyProfile.marketing_consent`
- `profile_visibility` → `PrivacyProfile.profile_visibility`
- `contact_preferences` → `PrivacyProfile.contact_preferences`
- `deletion_requested` → `PrivacyProfile.deletion_requested`
- All GDPR and consent-related fields

## GDPR Compliance Features

### **User Rights Implementation**

- ✅ **Right to Information**: Data processing records show what data is
  processed and why
- ✅ **Right of Access**: Data export functionality for user data portability
- ✅ **Right to Rectification**: User can update privacy preferences and consent
- ✅ **Right to Erasure**: Account deletion with configurable delay period
- ✅ **Right to Restrict Processing**: Consent withdrawal stops non-essential
  processing
- ✅ **Right to Data Portability**: JSON export of all user data
- ✅ **Right to Object**: Granular consent controls for different processing
  purposes

### **Consent Management**

- **Granular Consent**: Separate tracking for different types of consent
- **Version Control**: Track which version of policies user consented to
- **Withdrawal Tracking**: Log when and why consent was withdrawn
- **Expiration Handling**: Automatic consent expiration for time-limited
  agreements

### **Data Retention**

- **Configurable Retention**: User can choose data retention periods
- **Auto-Deletion**: Automatic deletion after retention period expires
- **Anonymization Options**: Convert data to anonymous research data instead of
  deletion

## API Endpoints (Planned)

- `GET /api/v1/privacy/profile/` - Get privacy settings
- `PATCH /api/v1/privacy/profile/` - Update privacy preferences
- `POST /api/v1/privacy/consent/` - Give/withdraw specific consent
- `GET /api/v1/privacy/consent/log/` - View consent history
- `POST /api/v1/privacy/export/` - Request data export
- `POST /api/v1/privacy/delete/` - Request account deletion
- `DELETE /api/v1/privacy/delete/` - Cancel deletion request
- `GET /api/v1/privacy/processing/` - View data processing activities

## Business Logic

### Consent Workflows

- **Registration Flow**: Collect required consents during signup
- **Policy Updates**: Handle consent re-collection when policies change
- **Consent Withdrawal**: Graceful handling of consent withdrawal
- **Granular Control**: Allow users to consent to specific processing activities

### Privacy Controls

- **Visibility Settings**: Control who can see profile and recovery information
- **Contact Preferences**: Manage communication frequency and channels
- **Data Minimization**: Only collect and process necessary data

### GDPR Compliance

- **30-Day Deletion**: Standard 30-day delay for account deletion requests
- **Data Export**: Complete user data export in machine-readable format
- **Audit Trail**: Immutable logs for all privacy-related actions
- **Legal Basis**: Document legal basis for all data processing activities

## Privacy Settings Hierarchy

### **Profile Visibility Levels**

1. **Private**: Only visible to the user themselves
2. **Friends**: Visible to accepted connections
3. **Community**: Visible to verified community members
4. **Public**: Visible to everyone (not recommended for recovery platform)

### **Recovery Info Visibility**

1. **Private**: Recovery information never shared
2. **Friends**: Shared with trusted connections only
3. **Supporters**: Shared with verified support providers
4. **Community**: Shared within recovery community

### **Contact Preferences**

1. **No Contact**: Emergency notifications only
2. **Email Only**: Critical platform updates via email
3. **Limited**: Important updates and security notifications
4. **Normal**: Regular platform communications
5. **All**: All notifications and marketing communications

## Security & Compliance

### **Data Protection**

- All privacy data encrypted at rest
- Consent logs are immutable (append-only)
- IP address logging for consent verification
- Secure data export with encryption

### **Legal Requirements**

- GDPR Article 6 (Lawful Basis) compliance
- GDPR Article 7 (Consent) requirements
- GDPR Article 13/14 (Information) transparency
- GDPR Article 17 (Right to Erasure) implementation

### **Audit Requirements**

- Immutable consent logs for legal disputes
- Data processing activity logging
- Privacy setting change tracking
- Retention policy enforcement

## Integration Points

### With Authentication App

- Links to User model for privacy profile
- Replaces privacy fields from monolithic UserProfile
- Consent checks during authentication flows

### With All Apps

- Privacy controls affect data visibility across platform
- GDPR export includes data from all apps
- Deletion requests trigger cascading anonymization

### With Core App

- Privacy utilities for checking user permissions
- GDPR compliance helpers for data export
- Audit logging integration

## File Structure

```
privacy/
├── models.py          # PrivacyProfile, ConsentLog, DataProcessingRecord
├── serializers.py     # Privacy data serialization
├── views.py          # Privacy API endpoints
├── urls.py           # Privacy URL patterns
├── admin.py          # Django admin for privacy management
├── permissions.py    # Privacy-specific permissions
├── utils/
│   ├── gdpr.py       # GDPR compliance utilities
│   ├── consent.py    # Consent management helpers
│   └── export.py     # Data export functionality
└── README.md         # This file
```

## Usage Examples

### Create Privacy Profile

```python
from privacy.models import PrivacyProfile

profile = PrivacyProfile.objects.create(
    user=user,
    profile_visibility='community',
    recovery_info_visibility='private',
    contact_preferences='normal'
)

# Accept privacy policy
profile.accept_privacy_policy('1.0')
profile.give_data_processing_consent()
```

### Log Consent Actions

```python
from privacy.models import ConsentLog

# Log consent given
ConsentLog.log_consent(
    user=user,
    consent_type='privacy_policy',
    given=True,
    version='1.0',
    ip_address=request.META.get('REMOTE_ADDR')
)
```

### Request Account Deletion

```python
# Request deletion with 30-day delay
profile.request_deletion(delay_days=30)

# Cancel deletion request
profile.cancel_deletion_request()
```

### Data Processing Transparency

```python
from privacy.models import DataProcessingRecord

# Record data processing activity
record = DataProcessingRecord.objects.create(
    user=user,
    purpose='recovery_support',
    data_categories='["recovery_stage", "sobriety_date", "goals"]',
    legal_basis='consent',
    retention_period_days=1095  # 3 years
)
```

## Testing Requirements

- Test consent workflow completeness
- Verify GDPR compliance for all user rights
- Test data export functionality
- Validate deletion request handling
- Test privacy visibility controls
- Verify audit log immutability

## Performance Considerations

- Index on user fields for fast profile lookups
- Efficient queries for consent status checks
- Optimize privacy visibility filtering
- Cache privacy settings for frequent access
- Batch process deletion requests

## Migration Notes

⚠️ **Data Migration Required**: When deploying, existing
`authentication.UserProfile` privacy data needs to be migrated to
`PrivacyProfile`.

**Migration Strategy**:

1. Create new `PrivacyProfile` records for all users
2. Copy privacy-related fields from `UserProfile`
3. Create initial `ConsentLog` entries for existing consents
4. Validate data integrity and consent completeness
5. Remove old privacy fields from `UserProfile` (Phase 2)

## Compliance Checklist

### GDPR Requirements

- [ ] Lawful basis documented for all processing
- [ ] Consent collection and withdrawal mechanisms
- [ ] Data subject rights implementation
- [ ] Data protection impact assessment
- [ ] Privacy by design implementation
- [ ] Data breach notification procedures

### Platform-Specific Requirements

- [ ] Crisis situation data handling
- [ ] Minor protection (18+ age verification)
- [ ] Sensitive recovery data protection
- [ ] Cross-border data transfer safeguards
- [ ] Third-party data sharing controls

## Future Enhancements

- Cookie consent management
- Advanced anonymization algorithms
- Real-time consent monitoring dashboard
- Automated policy update notifications
- Enhanced data portability formats (XML, CSV)
- Integration with external consent management platforms

This app ensures Vineyard Group Fellowship meets all legal requirements for data protection
while providing users with comprehensive control over their privacy and data
usage. consent_date = models.DateTimeField() privacy_policy_version =
models.CharField(max_length=20)

class PrivacySettings(models.Model): """User privacy preferences and
controls.""" user = models.OneToOneField(User) profile_visibility =
models.CharField(max_length=20) allow_direct_messages = models.BooleanField()
marketing_consent = models.BooleanField() analytics_consent =
models.BooleanField()

class DataRetentionPreference(models.Model): """User preferences for data
retention.""" user = models.OneToOneField(User) retention_period_days =
models.IntegerField() last_updated = models.DateTimeField()

```

## Current Status

🟡 **STATUS UNKNOWN**: Need to analyze implementation details

### Analysis Needed

1. **Model Implementation**: What privacy models exist?
2. **GDPR Compliance**: How complete is the implementation?
3. **Data Export**: What data is included in exports?
4. **Deletion Process**: How thorough is account deletion?

## Security & Compliance Features

- **Audit Logging**: All privacy actions should be logged
- **Data Encryption**: Sensitive privacy data should be encrypted
- **Access Controls**: Only user can access their privacy data
- **Anonymization**: Proper data anonymization on account deletion

## Dependencies

- Core authentication models
- All apps that store user data (for export/deletion)
- Audit logging system
- Email system (for confirmation emails)

## GDPR Requirements

### Data Export (Article 20)

Must export all user data including:

- Account information
- Profile data
- Recovery tracking data
- Communication history
- Privacy settings
- Audit logs (user's own actions)

### Account Deletion (Article 17)

Must delete or anonymize:

- Personal identifiable information
- Profile data and photos
- Messages and communications
- But preserve: Anonymous analytics, Legal compliance data

### Consent Management

- Track consent for different data processing purposes
- Version control for privacy policies
- Easy consent withdrawal mechanisms
- Clear consent history for auditing

## File Structure

```

privacy/ ├── models.py # Privacy and consent models ├── serializers.py # GDPR
export/import serializers ├── views.py # Privacy API endpoints ├── utils/ #
Privacy utilities ├── admin.py # Django admin for privacy management └──
README.md # This file

````

## Integration Points

### With Authentication App

- User consent tracking
- Privacy policy acceptance
- Account deletion coordination

### With Profiles App

- Profile visibility controls
- Photo privacy settings
- Display name privacy

### With Recovery Data

- Recovery data export
- Sensitive recovery information protection
- Consent for sharing recovery progress

## Testing Requirements

- Test complete data export functionality
- Verify proper account deletion
- Test consent withdrawal flows
- Validate privacy setting enforcement
- GDPR compliance testing

## Performance Considerations

- Data export may be slow for users with lots of data
- Account deletion should be async for large accounts
- Privacy setting changes should be fast
- Consider caching privacy settings

## Usage Examples

### Data Export

```python
# Export all user data
from privacy.views import DataExportView

export_data = DataExportView().get_user_data(user)
# Returns comprehensive JSON with all user data
````

### Account Deletion

```python
# Delete user account
from privacy.services import AccountDeletionService

deletion_service = AccountDeletionService(user)
deletion_service.delete_account(confirm=True)
# Anonymizes/deletes all user data
```

## Compliance Notes

- **Data Processing Basis**: Need clear legal basis for all data processing
- **Consent Granularity**: Allow granular consent for different features
- **Right to Rectification**: Users should be able to correct their data
- **Data Portability**: Export format should be machine-readable

## Monitoring & Alerting

- Monitor data export request volume
- Alert on bulk account deletions
- Track consent withdrawal rates
- Monitor privacy setting usage

## Production Considerations

- **Performance**: Large data exports need optimization
- **Storage**: Temporary export files need secure cleanup
- **Email**: Confirmation emails for sensitive privacy actions
- **Compliance**: Regular GDPR compliance audits

This app is critical for legal compliance and user trust in the Vineyard Group Fellowship
platform.
