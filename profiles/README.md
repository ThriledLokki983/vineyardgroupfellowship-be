# Profiles App

## Purpose

User profile management and customization for the Vineyard Group Fellowship platform.
This app handles all non-authentication user data including profile information,
photos, privacy settings, and profile completeness tracking.

## Core Functionality

### Profile Management
- **UserProfile** - Extended user information beyond authentication
- **Profile Photos** - Optimized image storage with thumbnails
- **Privacy Settings** - Granular privacy controls
- **Profile Completeness** - Tracking and recommendations

### Key Features
- **Photo Processing** - Automatic thumbnail generation and optimization
- **Privacy Controls** - Fine-grained visibility settings
- **Profile Completion** - Gamified profile building with badges
- **Moderation Support** - Content moderation for photos and profiles

## Models

### UserProfileBasic
Core profile information separated from authentication:
- Display name and bio
- Timezone settings
- Profile visibility controls
- Basic profile metadata

### ProfilePhoto
Optimized photo storage system:
- File-based storage (replaces base64)
- Automatic thumbnail generation (150x150)
- EXIF orientation handling
- Smart cropping and optimization
- Moderation workflow support

### ProfileCompletenessTracker
Gamified profile completion system:
- Overall completion percentage
- Section-specific scores
- Achievement badges
- Completion level tracking

## API Endpoints

### Profile Management
- `GET /api/v1/profiles/me/` - Get current user's profile (includes onboarding state)
- `PUT /api/v1/profiles/me/` - Update current user's profile
- `PATCH /api/v1/profiles/me/` - Partial profile update
- `GET /api/v1/profiles/{user_id}/` - Get public profile (with privacy rules)

**Profile Response includes nested onboarding state:**
```json
{
  "display_name": "John Doe",
  "bio": "Fellowship member",
  "timezone": "America/New_York",
  "profile_visibility": "community",
  "leadership_info": {},
  "email": "user@example.com",
  "date_joined": "2025-01-15T10:30:00Z",
  "onboarding": {
    "completed": false,
    "current_step": "community_preferences",
    "progress_percentage": 45
  },
  "photo_url": "https://example.com/media/profile_photos/abc123.jpg",
  "photo_thumbnail_url": "https://example.com/media/profile_photos/abc123_thumb.jpg",
  "photo_visibility": "community",
  "can_upload_photo": true,
  ...
}
```

### Photo Management
- `GET /api/v1/profiles/me/photo/` - Get profile photo info
- `POST /api/v1/profiles/me/photo/` - Upload profile photo
- `PUT /api/v1/profiles/me/photo/` - Replace profile photo
- `DELETE /api/v1/profiles/me/photo/` - Delete profile photo

### Privacy Settings
- `GET /api/v1/profiles/me/privacy/` - Get privacy settings
- `PUT /api/v1/profiles/me/privacy/` - Update privacy settings

### Profile Completeness
- `GET /api/v1/profiles/me/completeness/` - Get completion status
- `POST /api/v1/profiles/me/completeness/refresh/` - Recalculate completion

## Security & Privacy

### Privacy Levels
- **Private** - Only visible to user
- **Community** - Visible to community members
- **Public** - Visible to everyone

### Photo Moderation
- Automatic moderation workflow
- Pending/Approved/Rejected states
- Admin moderation interface

### Data Protection
- GDPR compliance ready
- Data export/deletion support
- Privacy-first design

## Technical Features

### Photo Processing
- PIL/Pillow for image processing
- Automatic thumbnail generation
- EXIF orientation correction
- Smart cropping algorithms
- Multiple size variants

### Performance Optimization
- Separate photo model for performance
- Efficient database queries
- Optimized image storage
- Caching-friendly design

### Extensibility
- Modular design for future features
- Plugin-ready architecture
- Event-driven updates
- Service layer separation

## Device & Session Management

### Device Tracking
The profiles app includes comprehensive device and session management integrated with the authentication system:

- **DeviceManagement** - Track user devices and sessions
- **Session Analytics** - Login history and device fingerprinting
- **Security Monitoring** - Detect suspicious sessions and devices
- **Multi-device Support** - Manage concurrent sessions across devices

### Device Endpoints (via DeviceManagementViewSet)
- `GET /api/v1/profiles/devices/` - List all user devices
- `GET /api/v1/profiles/devices/{id}/` - Get specific device details
- `DELETE /api/v1/profiles/devices/{id}/` - Remove/revoke device access
- `POST /api/v1/profiles/devices/{id}/terminate-session/` - Terminate device session

### Session Endpoints (via SessionManagementViewSet)
- `GET /api/v1/profiles/sessions/` - List active sessions
- `GET /api/v1/profiles/sessions/{id}/` - Get session details
- `DELETE /api/v1/profiles/sessions/{id}/` - Terminate specific session
- `POST /api/v1/profiles/sessions/terminate-all/` - Terminate all sessions
- `POST /api/v1/profiles/sessions/terminate-others/` - Terminate all except current

## File Structure

```
profiles/
├── models.py              # Profile models
├── serializers.py         # DRF serializers
├── views.py              # API views and viewsets
├── services.py           # Business logic services
├── urls.py               # URL routing
├── admin.py              # Django admin interface
├── management/           # Django commands
├── migrations/           # Database migrations
└── tests/               # Comprehensive test suite
    ├── test_models.py
    ├── test_views.py
    ├── test_serializers.py
    └── factories.py
```

## Usage Examples

### Update Profile

```python
# Get current profile
GET /api/v1/profiles/me/
# Response:
{
    "id": "uuid",
    "display_name": "John Doe",
    "bio": "Community member since 2024",
    "timezone": "America/New_York",
    "profile_visibility": "community",
    "has_photo": true,
    "completeness": 75
}

# Update profile
PATCH /api/v1/profiles/me/
{
    "display_name": "John D.",
    "bio": "Updated bio",
    "timezone": "America/Los_Angeles"
}
```

### Upload Profile Photo

```python
# Upload new photo
POST /api/v1/profiles/me/photo/
Content-Type: multipart/form-data

photo: [binary image data]

# Response:
{
    "photo_url": "https://example.com/media/profile_photos/uuid.jpg",
    "thumbnail_url": "https://example.com/media/profile_photos/uuid_thumb.jpg",
    "moderation_status": "pending"
}
```

### Privacy Settings

```python
# Update privacy settings
PUT /api/v1/profiles/me/privacy/
{
    "profile_visibility": "private",
    "show_email": false,
    "show_timezone": false,
    "allow_contact": true
}
```

### Device Management

```python
# List all devices
GET /api/v1/profiles/devices/
# Response:
[
    {
        "id": "uuid",
        "device_name": "iPhone 14",
        "last_active": "2024-01-15T10:30:00Z",
        "is_current": true,
        "trusted": true
    },
    {
        "id": "uuid",
        "device_name": "Chrome on MacOS",
        "last_active": "2024-01-14T15:20:00Z",
        "is_current": false,
        "trusted": true
    }
]

# Terminate specific device
DELETE /api/v1/profiles/devices/{device_id}/
```

## Integration with Other Apps

### Authentication App
- Shares User model reference
- Session management integration
- Device fingerprinting coordination

### Privacy App
- Privacy settings enforcement
- GDPR data export support
- Data deletion workflows

### Onboarding App
- Profile completeness tracking
- Onboarding progress integration
- Initial profile setup

## Testing

### Test Coverage

- **Unit Tests** - Model validation, photo processing
- **Integration Tests** - API endpoint functionality
- **Photo Tests** - Image upload, thumbnail generation
- **Privacy Tests** - Visibility rules, permission checks

### Run Tests

```bash
# Run all profile tests
pytest profiles/tests/

# Run with coverage
pytest --cov=profiles profiles/tests/

# Run specific test categories
pytest -m photos profiles/tests/
pytest -m privacy profiles/tests/
```

## Performance Considerations

### Photo Processing
- Asynchronous thumbnail generation
- Optimized image storage
- CDN-ready file structure
- Efficient EXIF handling

### Database Optimization
- Separate photo model for performance
- Indexed fields for common queries
- Efficient relationship queries
- Caching-friendly design

### Caching Strategy
- Profile data caching
- Photo URL caching
- Completeness score caching
- Privacy settings caching

## Configuration

### Settings

```python
# Media files
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Profile photo settings
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp']
THUMBNAIL_SIZE = (150, 150)

# Privacy defaults
DEFAULT_PROFILE_VISIBILITY = 'community'
REQUIRE_EMAIL_VERIFICATION = True
```

## Security & Privacy Best Practices

### Photo Security
- File type validation
- Size limit enforcement
- Malware scanning ready
- Moderation workflow

### Privacy Protection
- Granular visibility controls
- Privacy-by-default design
- GDPR compliance ready
- User data export/deletion

### Access Control
- Permission-based access
- Privacy rule enforcement
- Rate limiting on uploads
- Audit logging

## Future Enhancements

### Planned Features
- Advanced photo editing
- Multiple profile photos
- Custom privacy rules
- Profile badges and achievements
- Social connections
- Profile analytics

### Migration Notes
- SupporterQualifications model to be migrated from authentication app
- RecoveryProfile integration planned
- Enhanced completeness tracking
- Gamification features
