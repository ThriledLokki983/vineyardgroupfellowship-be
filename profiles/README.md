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
- `GET /api/v1/profiles/me/` - Get current user's profile
- `PUT /api/v1/profiles/me/` - Update current user's profile
- `PATCH /api/v1/profiles/me/` - Partial profile update
- `GET /api/v1/profiles/{user_id}/` - Get public profile (with privacy rules)

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

### Security Models

- **PasswordHistory** - Password reuse prevention
- **EmailVerificationToken** - Secure email verification
- **PasswordResetToken** - Secure password reset flow

### Profile Extensions (To Be Migrated)

- **SupporterQualifications** - Support provider credentials
- **RecoveryProfile** - Recovery journey tracking
- **PrivacySettings** - User privacy preferences

## Security Features

### ✅ Production-Ready Security

- **JWT with Rotation** - 15-minute access tokens, 14-day refresh tokens
- **Token Blacklisting** - Immediate token revocation capability
- **Account Lockout** - Brute force protection
- **Password Strength** - Comprehensive validation
- **Audit Logging** - Complete security event tracking
- **Rate Limiting** - Per-endpoint throttling
- **HTTPS Enforcement** - TLS/SSL requirements
- **Secure Headers** - CSP, HSTS, X-Frame-Options
- **CORS Configuration** - Controlled cross-origin access

### 🔐 Privacy-First Design

- **Minimal Data Collection** - Only essential authentication data
- **Email Normalization** - Consistent email handling
- **Timezone Support** - User timezone preferences
- **Optional Display Names** - Anonymous participation support
- **GDPR Compliance Ready** - Data export and deletion support

## API Endpoints

### Core Authentication

- `POST /api/v1/auth/register/` - User registration with email verification
- `POST /api/v1/auth/login/` - User authentication with JWT tokens
- `POST /api/v1/auth/logout/` - Session termination and token cleanup
- `POST /api/v1/auth/refresh/` - JWT token refresh with rotation

### Password Management

- `POST /api/v1/auth/password/change/` - Authenticated password change
- `POST /api/v1/auth/password/reset/` - Password reset request
- `POST /api/v1/auth/password/reset/confirm/` - Password reset confirmation

### Email Verification

- `POST /api/v1/auth/email/verify/` - Email verification with token
- `POST /api/v1/auth/email/verify/resend/` - Resend verification email

### Session Management

- `GET /api/v1/auth/sessions/` - List user sessions
- `DELETE /api/v1/auth/sessions/{id}/` - Terminate specific session
- `POST /api/v1/auth/sessions/terminate-all/` - Terminate all sessions

### Health & Monitoring

- `GET /api/v1/auth/health/` - Authentication service health

## Middleware Stack

### Security Middleware

1. **CorrelationIdMiddleware** - Request tracking
2. **CorsMiddleware** - Cross-origin protection
3. **SecurityMiddleware** - HTTPS enforcement
4. **CsrfViewMiddleware** - CSRF protection
5. **AuthenticationMiddleware** - User authentication
6. **OTPMiddleware** - Two-factor authentication
7. **ErrorHandlingMiddleware** - Consistent error responses

### Monitoring Middleware

- **PerformanceMonitoringMiddleware** - Request metrics
- **DatabaseQueryMonitoringMiddleware** - Query optimization

## Configuration

### Environment Variables

```bash
# Database
DB_NAME=Vineyard Group Fellowship
DB_USER=Vineyard Group Fellowship_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=5432

# Security
SECRET_KEY=your-secret-key
DJANGO_SETTINGS_MODULE=Vineyard Group Fellowship.settings

# Email
SENDGRID_API_KEY=your-sendgrid-key
DEFAULT_FROM_EMAIL=noreply@Vineyard Group Fellowship.com

# Redis
REDIS_URL=redis://localhost:6379/0

# Feature Flags
ENABLE_COOKIE_REFRESH_TOKEN=True
```

### JWT Configuration

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_COOKIE': 'refresh_token',
    'AUTH_COOKIE_HTTP_ONLY': True,
}
```

## File Structure

```
authentication/
├── models.py              # Core auth models (1,256 lines)
├── serializers.py         # DRF serializers (661 lines)
├── views.py              # View module exports
├── services.py           # Business logic services
├── urls.py               # URL routing
├── admin.py              # Django admin interface
├── utils/                # Authentication utilities
│   ├── auth.py           # Email verification & password utils
│   ├── sessions.py       # Session management
│   ├── cookies.py        # Cookie handling
│   └── email.py          # Email service integration
├── view_modules/         # Organized view modules
│   ├── authentication.py # Registration, login, logout
│   ├── password.py       # Password management
│   ├── email.py          # Email verification
│   ├── tokens.py         # JWT token management
│   └── health.py         # Health checks
├── url_modules/          # URL organization
│   ├── auth.py           # Core auth URLs
│   ├── session.py        # Session management URLs
│   └── health.py         # Health check URLs
├── management/           # Django commands
├── migrations/           # Database migrations
└── tests/               # Comprehensive test suite
    ├── test_models.py
    ├── test_views.py
    ├── test_serializers.py
    ├── test_integration.py
    └── factories.py
```

## Usage Examples

### Registration Flow

```python
# 1. Register user
POST /api/v1/auth/register/
{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "first_name": "John",
    "last_name": "Doe"
}

# 2. Verify email
POST /api/v1/auth/email/verify/
{
    "token": "verification_token_from_email"
}

# 3. Login
POST /api/v1/auth/login/
{
    "email": "user@example.com",
    "password": "SecurePassword123!"
}
```

### Authentication Headers

```javascript
// Access token in Authorization header
headers: {
    'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
    'Content-Type': 'application/json'
}

// Refresh token in HttpOnly cookie (automatic)
// Cookie: refresh_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Migration Status

### ⚠️ Planned Refactoring

The authentication app currently contains mixed concerns that will be separated:

**Keep in Authentication:**

- Core authentication logic
- JWT token management
- Session management
- Password management
- Email verification
- Security auditing

**Move to Profiles App:**

- UserProfile model (non-auth fields)
- SupporterQualifications
- Profile completeness tracking
- Photo management
- Privacy settings

## Testing

### Test Coverage

- **Unit Tests** - Model validation, serializer logic
- **Integration Tests** - API endpoint functionality
- **Security Tests** - Rate limiting, token security
- **Performance Tests** - Database query optimization

### Run Tests

```bash
# Run all authentication tests
pytest authentication/tests/

# Run with coverage
pytest --cov=authentication authentication/tests/

# Run specific test categories
pytest -m security authentication/tests/
pytest -m integration authentication/tests/
```

## Performance Considerations

### Database Optimization

- **Connection Pooling** - Persistent database connections
- **Indexed Fields** - Optimized queries on email, tokens
- **Query Optimization** - select_related and prefetch_related usage

### Caching Strategy

- **Redis Sessions** - Fast session storage
- **Token Blacklist** - Redis-backed token revocation
- **Rate Limiting** - Redis-backed throttling

### Monitoring

- **Query Analysis** - DatabaseQueryMonitoringMiddleware
- **Performance Metrics** - Request/response timing
- **Error Tracking** - Sentry integration

## Security Best Practices

### Token Management

- Short-lived access tokens (15 minutes)
- Secure refresh token rotation
- Immediate token blacklisting capability
- HttpOnly cookie storage for refresh tokens

### Password Security

- Argon2 password hashing
- 12+ character minimum length
- Complexity requirements
- Password history tracking
- Breach detection ready

### Rate Limiting

- Progressive lockout for failed attempts
- Per-endpoint rate limiting
- IP-based and user-based throttling
- Configurable rate limits

### Audit & Monitoring

- Comprehensive security event logging
- Failed login attempt tracking
- Session anomaly detection
- Real-time security monitoring

I've updated the authentication app README with a comprehensive overview of all
the tools and technologies used in the current authentication system.

## Key Updates Made:

### 🛠️ **Complete Technology Stack**

- **Core Framework**: Django 5.2.7 + DRF 3.14.0
- **Authentication**: JWT with SimpleJWT, Redis sessions, OTP support
- **Security**: CORS, CSRF, rate limiting, password hashing, audit logging
- **Database**: PostgreSQL with connection pooling
- **Monitoring**: Sentry, structured logging, performance tracking

### 🔐 **Security Tools Detailed**

- **JWT Implementation**: Token rotation, blacklisting, HttpOnly cookies
- **Rate Limiting**: Per-endpoint throttling (25 login attempts/hour)
- **Password Security**: Argon2 hashing, 12+ chars, breach detection ready
- **Protection Layers**: CSP, HSTS, security headers, CORS configuration

### 📁 **Architecture Overview**

- **Modular Design**: Organized view modules, URL modules, utilities
- **Service Layer**: Business logic separation
- **Comprehensive Testing**: pytest with security, integration, performance
  tests
- **Production Ready**: Health checks, monitoring, error handling

### 🚀 **Production Features**

- **Performance**: Redis caching, query optimization, connection pooling
- **Monitoring**: Real-time metrics, audit trails, error tracking
- **Scalability**: Stateless JWT, horizontal scaling ready
- **Privacy**: GDPR compliance ready, minimal data collection

The README now serves as a complete technical reference for understanding how
the authentication system works, what tools it uses, and how to configure and
maintain it.
