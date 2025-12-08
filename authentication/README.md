# Authentication App

> **Vineyard Group Fellowship Platform** - Production-grade authentication system with JWT tokens, comprehensive session management, audit logging, and privacy-first design.

## 📋 Table of Contents

- [Purpose](#purpose)
- [Architecture Overview](#architecture-overview)
- [Core Technologies & Tools](#core-technologies--tools)
  - [Django Framework Stack](#django-framework-stack)
  - [Authentication & Security](#authentication--security)
  - [Security & Protection](#security--protection)
  - [Session & Device Management](#session--device-management)
  - [Email & Communications](#email--communications)
  - [Password Security](#password-security)
  - [API & Documentation](#api--documentation)
  - [Monitoring & Logging](#monitoring--logging)
- [Key Models](#key-models)
  - [User Model](#user-model)
  - [UserSession Model](#usersession-model)
  - [AuditLog Model](#auditlog-model)
  - [PasswordHistory Model](#passwordhistory-model)
  - [EmailVerificationToken Model](#emailverificationtoken-model)
- [Security Features](#security-features)
- [API Endpoints](#api-endpoints)
  - [Authentication](#authentication)
  - [Token Management](#token-management)
  - [Password Management](#password-management)
  - [Email Verification](#email-verification)
  - [Session Management](#session-management)
  - [CSRF Protection](#csrf-protection)
  - [Health & Monitoring](#health--monitoring)
- [Middleware Stack](#middleware-stack)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [JWT Configuration](#jwt-configuration)
  - [Rate Limiting Configuration](#rate-limiting-configuration)
- [File Structure](#file-structure)
- [Usage Examples](#usage-examples)
- [API Client Examples](#api-client-examples)
  - [JavaScript/TypeScript](#javascripttypescript-react-react-native)
  - [Python Client](#python-client)
- [Best Practices](#best-practices)
  - [Frontend Integration](#frontend-integration)
  - [Security Recommendations](#security-recommendations)
  - [Mobile App Considerations](#mobile-app-considerations)
- [Development Setup](#development-setup)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Deployment](#deployment)
- [Monitoring & Observability](#monitoring--observability)
- [Migration Status](#migration-status)

---

## Purpose

Core authentication and user management functionality for the Vineyard Group Fellowship platform. Provides production-grade security with JWT-based authentication, comprehensive session management, audit logging, and privacy-first design principles.

## Architecture Overview

The authentication system uses a **modular, service-oriented architecture** with clear separation of concerns:

- **View Modules** - Organized by functionality (authentication, tokens, password, email, sessions)
- **Service Layer** - Business logic isolation (ExchangeTokenService, AuthenticationService)
- **Utility Functions** - Reusable components (cookies, email, sessions, auth helpers)
- **Models** - Data layer with security features (User, UserSession, AuditLog, TokenBlacklist)
- **Serializers** - API validation and transformation layer

## Core Technologies & Tools

### Django Framework Stack

- **Django 5.2.7** - Core web framework with async support
- **Django REST Framework 3.15.2** - RESTful API framework
- **PostgreSQL with PostGIS** - Primary database with spatial extensions
- **Redis 5.0.1** - Caching, session storage, and rate limiting

### Authentication & Security

- **JWT (JSON Web Tokens)** - Stateless authentication with rotation
  - `djangorestframework-simplejwt==5.3.1` - JWT implementation
  - `PyJWT==2.10.1` - JWT encoding/decoding library
  - **Access Token**: 15-minute lifetime, memory-only storage
  - **Refresh Token**: 14-day lifetime, httpOnly cookie storage
  - Token rotation on refresh (old tokens blacklisted)
  - Immediate token revocation capability
- **Django OTP 1.3.0** - Two-factor authentication framework
- **Cryptography 46.0.2** - Secure token generation and field encryption
- **Argon2-CFFI** - Password hashing (Django's recommended hasher)

### Security & Protection

- **CORS Protection** - `django-cors-headers==4.3.1`
  - Cross-origin resource sharing configuration
  - Whitelist-based origin validation
  - Secure credentials handling
  - Pre-flight request support
- **CSRF Protection** - Django built-in with custom views
  - Token-based CSRF protection for state-changing requests
  - SPA-compatible configuration (dedicated `/auth/csrf/` endpoint)
  - Cookie and header-based validation
  - Rotation on authentication state changes
- **Rate Limiting** - `django-ratelimit==4.1.0`
  - **Registration**: 5 attempts per hour per IP
  - **Login**: 25 attempts per hour per IP
  - **Password Reset**: 5 attempts per hour per IP
  - **Token Refresh**: 60 attempts per hour per user
  - **Email Verification**: 10 attempts per hour per IP
  - Redis-backed rate limit storage
  - Progressive lockout (account locked after 5 failed logins for 30 minutes)
- **Content Security Policy** - `django-csp==3.8`
- **Security Headers** - X-Frame-Options, HSTS, X-Content-Type-Options, etc.

### Session & Device Management

- **Redis-backed Sessions** - Fast, distributed session storage with persistence
- **Device Fingerprinting** - `user-agents==2.2.0` and `ua-parser==1.0.1`
  - Browser and OS detection
  - Device type identification (mobile, tablet, desktop)
  - User-provided device names ("iPhone", "Work Laptop")
  - Generated device fingerprints for security tracking
- **Session Analytics** - Comprehensive login tracking and device management
  - Session creation and termination logging
  - Last activity timestamps
  - Token rotation tracking
  - Geographic data (city, country) - privacy-conscious
- **Concurrent Session Control** - Multi-device session management
  - Individual session termination
  - Terminate all sessions capability
  - Session expiry management (7-14 days based on "Remember Me")
  - Automatic cleanup of expired sessions

### Email & Communications

- **SendGrid Integration** - `sendgrid==6.11.0` for production email delivery
- **Django Anymail 10.3** - `django-anymail==10.3` unified email backend
- **Async Email Processing** - Non-blocking email sending via threading
  - Prevents HTTP timeout issues on slow SMTP connections
  - Critical for Railway deployment (30s timeout limit)
  - Celery task queue support for breach checking and bulk emails
- **Template-based Emails** - HTML and text email templates
  - Email verification with secure single-use tokens
  - Password reset with time-limited tokens
  - Account notifications and security alerts
- **Email Normalization** - Gmail-specific handling (dot and plus-addressing)
- **Fallback Configuration** - MailHog for development testing

### Password Security

- **Argon2 Password Hashing** - Industry-standard, memory-hard algorithm
- **Password Strength Validation** - Multi-layer validation system
  - Minimum 8 characters (configurable)
  - Must contain uppercase and lowercase letters
  - Must contain at least one number
  - Must contain special characters
  - Cannot be similar to user information
  - Cannot be a common password
- **Password History Tracking** - Prevent password reuse (PasswordHistory model)
- **Breach Detection** - Async HaveIBeenPwned integration (Celery task)
  - Non-blocking password breach checking during registration
  - Graceful fallback if Celery unavailable
- **Account Lockout** - Progressive security measures
  - 5 failed attempts = 30-minute account lock
  - Failed attempt counter reset on successful login
  - Manual unlock capability via admin
- **Password Reset Flow** - Secure token-based password recovery
  - Time-limited reset tokens (1 hour expiry)
  - Single-use tokens with database tracking
  - Email-based verification

### API & Documentation

- **OpenAPI 3.0** - `drf-spectacular==0.27.2` for schema generation
- **Nested Routing** - `drf-nested-routers==0.93.5` for organized URL patterns
- **Auto-generated Documentation** - Interactive Swagger/ReDoc interface
- **Problem+JSON (RFC 7807)** - Standardized error responses
  - Consistent error format across all endpoints
  - Machine-readable error details
  - Human-friendly error messages
  - Validation error field mapping
- **Custom API Decorators** - `@authentication_schema` for endpoint documentation
- **Organized URL Modules** - Modular URL configuration by feature area

### Monitoring & Logging

- **Sentry Integration** - `sentry-sdk[django]==2.19.2` (Python 3.13 compatible)
  - Real-time error tracking and alerting
  - Performance monitoring and tracing
  - User context tracking for debugging
  - Breadcrumb logging for issue diagnosis
- **Structured Logging** - `structlog==23.2.0`
  - JSON-formatted logs for machine parsing
  - Contextual logging with user IDs, IPs, and actions
  - Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Audit Logging** - Comprehensive security event tracking (AuditLog model)
  - Authentication events (login, logout, registration)
  - Security events (failed logins, account lockouts)
  - Session management (creation, termination, rotation)
  - Token operations (refresh, exchange, blacklist)
  - Risk level classification (low, medium, high, critical)
  - Metadata storage for forensic analysis
- **Performance Monitoring** - Request/response tracking via middleware
- **Health Checks** - Database, cache, and service connectivity endpoints

### Development & Testing

- **pytest** - Testing framework with Django integration
- **Factory Boy** - Test data generation
- **Coverage** - Code coverage reporting
- **MyPy** - Type checking with Django stubs
- **Bandit** - Security linting
- **pip-audit** - Dependency vulnerability scanning

## Key Models

### Core Authentication Models

- **User** (Custom AbstractUser)
  - **Primary Key**: UUID for security and scalability
  - **Authentication**: Email-based (USERNAME_FIELD = 'email')
  - **Fields**: email, username, email_verified, email_verified_at, password_changed_at
  - **Security**: failed_login_attempts, locked_until, terms_accepted_at, privacy_policy_accepted_at
  - **Indexes**: email, username, email_verified, created_at
  - **Methods**: is_account_locked(), lock_account(), unlock_account(), record_failed_login(), record_successful_login()

- **UserSession** - Comprehensive session and device tracking
  - **Fields**: user, session_key, refresh_token_jti, device_name, device_fingerprint, user_agent, ip_address
  - **Geographic**: city, country (privacy-conscious, optional)
  - **Status**: is_active, is_verified (2FA), created_at, last_activity_at, last_rotation_at, expires_at
  - **Indexes**: user+is_active, session_key, refresh_token_jti, device_fingerprint, expires_at
  - **Methods**: is_expired(), is_near_expiry(), needs_rotation(), mark_rotation(), deactivate(), extend_expiry()
  - **Lifecycle**: cleanup_expired() for automatic session pruning

- **TokenBlacklist** - JWT token revocation system
  - **Purpose**: Immediate token invalidation for security
  - **Fields**: jti (JWT ID), token, user, expires_at, blacklisted_at, reason
  - **Use Cases**: Logout, password change, compromised token, admin action
  - **Indexes**: jti (unique), expires_at for cleanup
  - **Methods**: is_token_blacklisted(), blacklist_token(), cleanup_expired()

- **AuditLog** - Security and compliance audit trail
  - **Events**: login, logout, registration, password_change, token_refresh, session_terminated, etc.
  - **Context**: user, event_type, description, ip_address, user_agent, success, risk_level
  - **Metadata**: JSON field for flexible event-specific data
  - **Retention**: Configurable retention policy
  - **Methods**: log_event() class method for consistent logging

### Security Models

- **PasswordHistory** - Password reuse prevention
  - **Purpose**: Prevent users from reusing recent passwords
  - **Fields**: user, password_hash, created_at
  - **Validation**: Configurable history limit (default: 5 previous passwords)
  - **Cleanup**: Automatic removal of old history entries

- **EmailVerificationToken** - Secure email verification
  - **Token Type**: Cryptographically secure random tokens (32 bytes)
  - **Expiry**: 24-hour lifetime (configurable)
  - **Single Use**: Token invalidated after verification
  - **Fields**: user, token, created_at, expires_at, verified_at
  - **Methods**: is_valid(), verify(), resend()

- **PasswordResetToken** - Secure password reset flow
  - **Token Type**: Django's PasswordResetTokenGenerator (tamper-proof)
  - **Expiry**: 1-hour lifetime
  - **Single Use**: Token invalidated after use
  - **Fields**: user, token, created_at, used_at
  - **Security**: User's password_changed_at included in token generation

## Security Features

### ✅ Production-Ready Security

- **JWT with Automatic Rotation** 
  - **Access Token**: 15-minute lifetime, memory-only storage (XSS protection)
  - **Refresh Token**: 14-day lifetime, httpOnly cookie (XSS-safe, survives reload)
  - Token rotation on every refresh (old tokens blacklisted)
  - Blacklist enforcement via TokenBlacklist model
  - Proactive refresh scheduling (1 minute before expiry)

- **Token Blacklisting** - Immediate token revocation capability
  - Logout: All user tokens blacklisted
  - Password change: All existing tokens invalidated
  - Compromised token: Individual token revocation
  - Admin action: Manual token blacklist
  - Automatic cleanup of expired blacklist entries

- **Account Lockout** - Progressive brute force protection
  - 5 failed login attempts = 30-minute lock
  - Automatic unlock after lockout period
  - Manual unlock via admin interface
  - Failed attempt counter tracks consecutive failures
  - Successful login resets counter

- **Password Strength** - Multi-layer validation system
  - Django's built-in validators + custom validators
  - Minimum length, complexity requirements
  - Common password detection
  - User attribute similarity checking
  - Async breach detection (HaveIBeenPwned API)

- **Comprehensive Audit Logging** - Complete security event tracking
  - All authentication events logged
  - IP address and user agent tracking
  - Risk level classification (low/medium/high/critical)
  - Metadata storage for forensic analysis
  - Retention policy configuration

- **Rate Limiting** - Granular per-endpoint throttling
  - Redis-backed rate limit storage
  - IP-based and user-based limits
  - Different limits for different actions
  - Automatic rate limit reset
  - 429 error responses with retry headers

- **HTTPS Enforcement** - TLS/SSL requirements
  - SECURE_SSL_REDIRECT in production
  - SECURE_PROXY_SSL_HEADER for Railway/Heroku
  - HTTP Strict Transport Security (HSTS)
  - Secure cookie flags (Secure, HttpOnly, SameSite)

- **Secure Headers** - Multiple security headers configured
  - Content-Security-Policy (CSP)
  - X-Frame-Options (clickjacking protection)
  - X-Content-Type-Options (MIME sniffing protection)
  - X-XSS-Protection (legacy XSS protection)
  - Referrer-Policy (referrer information control)

- **CORS Configuration** - Controlled cross-origin access
  - Whitelist-based origin validation
  - Credentials allowed for authenticated requests
  - Preflight request handling
  - Configurable allowed methods and headers

### 🔐 Privacy-First Design

- **Minimal Data Collection** - Only essential authentication data stored
  - No unnecessary personal information
  - Optional geographic data (city, country)
  - User-controlled profile visibility
  
- **Email Normalization** - Consistent, privacy-respecting email handling
  - Gmail dot and plus-addressing normalization
  - Prevents duplicate account creation
  - Case-insensitive email comparison
  
- **Timezone Support** - User timezone preferences for accurate timestamps
  
- **Optional Display Names** - Anonymous participation support
  - Users can choose display names instead of real names
  - Username requirement but flexible display options
  
- **GDPR Compliance Ready** - Data export and deletion support
  - User data export capability
  - Right to be forgotten implementation
  - Clear consent tracking (terms, privacy policy)
  - Consent timestamps stored
  
- **Secure Token Exchange** - Exchange tokens for email verification
  - Short-lived, single-use tokens (60 seconds)
  - Prevents JWT tokens in URLs/browser history
  - Cache-based token storage for automatic expiry

### 🛡️ Additional Security Measures

- **CSRF Protection** - Token-based CSRF protection
  - SPA-compatible with dedicated `/auth/csrf/` endpoint
  - Rotation on authentication state changes
  - Cookie and header-based validation
  
- **Session Security** - Comprehensive session management
  - Device fingerprinting for anomaly detection
  - Multi-device session support
  - Individual and bulk session termination
  - Session expiry and rotation tracking
  
- **Dependency Security** - Regular security audits
  - `pip-audit` for vulnerability scanning
  - `bandit` for code security linting
  - Regular dependency updates
  - Security-focused code reviews

## API Endpoints

### Core Authentication

#### **POST** `/api/v1/auth/register/`
**User Registration with Email Verification**
- **Rate Limit**: 5 attempts per hour per IP
- **Permissions**: AllowAny
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "username": "john_doe",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "terms_accepted": true,
    "privacy_policy_accepted": true
  }
  ```
- **Response** (201 Created):
  ```json
  {
    "message": "Registration successful. Please check your email to verify your account.",
    "user_id": "uuid",
    "email": "user@example.com"
  }
  ```
- **Features**:
  - Creates User and UserProfile records
  - Sends email verification link
  - Queues async password breach check (Celery)
  - Audit log for registration attempts

#### **POST** `/api/v1/auth/login/`
**User Authentication with JWT Tokens**
- **Rate Limit**: 25 attempts per hour per IP
- **Permissions**: AllowAny
- **Request Body**:
  ```json
  {
    "email_or_username": "user@example.com",
    "password": "SecurePass123!",
    "remember_me": false,
    "device_name": "iPhone 15 Pro"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "expires_in": 900,
    "token_type": "Bearer",
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "username": "john_doe",
      "first_name": "John",
      "last_name": "Doe",
      "email_verified": true
    }
  }
  ```
- **Response Headers**:
  ```
  Set-Cookie: refresh_token=eyJ...; HttpOnly; Secure; SameSite=Lax; Max-Age=1209600
  ```
- **Features**:
  - Creates UserSession with device tracking
  - Sets httpOnly refresh token cookie
  - Resets failed login attempts on success
  - Audit log for login events
  - Supports email or username authentication

#### **POST** `/api/v1/auth/logout/`
**Session Termination and Token Cleanup**
- **Rate Limit**: None (authenticated)
- **Permissions**: IsAuthenticated
- **Request**: No body required
- **Response** (200 OK):
  ```json
  {
    "message": "Logged out successfully"
  }
  ```
- **Features**:
  - Blacklists current refresh token
  - Clears refresh token cookie
  - Deactivates current session
  - Audit log for logout event

### Token Management

#### **POST** `/api/v1/auth/token/refresh/`
**JWT Token Refresh with Rotation**
- **Rate Limit**: 60 attempts per hour per user
- **Permissions**: AllowAny (requires refresh token in cookie)
- **Request**: No body required (reads from httpOnly cookie)
- **Response** (200 OK):
  ```json
  {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
  ```
- **Response Headers** (if rotation enabled):
  ```
  Set-Cookie: refresh_token=eyJ...; HttpOnly; Secure; SameSite=Lax; Max-Age=1209600
  ```
- **Features**:
  - Reads refresh token from httpOnly cookie
  - Token rotation (old token blacklisted, new token issued)
  - Updates session rotation timestamp
  - Verifies user is still active
  - Audit log for token refresh

#### **POST** `/api/v1/auth/exchange-token/`
**Exchange Temporary Token for JWT**
- **Rate Limit**: 10 attempts per hour per IP
- **Permissions**: AllowAny
- **Purpose**: Secure email verification flow (prevents JWT in URLs)
- **Request Body**:
  ```json
  {
    "exchange_token": "secure_temporary_token"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user_id": "uuid",
    "email": "user@example.com",
    "expires_in": 900,
    "first_login": true,
    "message": "Token exchange successful"
  }
  ```
- **Features**:
  - Single-use tokens (60-second expiry)
  - Creates new UserSession
  - Sets httpOnly refresh token cookie
  - Cache-based token storage
  - Audit log for token exchange

#### **POST** `/api/v1/auth/token/verify/`
**Verify JWT Access Token**
- **Rate Limit**: 100 attempts per hour per IP
- **Permissions**: AllowAny
- **Request Body**:
  ```json
  {
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
  ```
- **Response** (200 OK): `{}`
- **Response** (401 Unauthorized): Invalid/expired token

### Password Management

#### **POST** `/api/v1/auth/password/change/`
**Authenticated Password Change**
- **Rate Limit**: 10 attempts per hour per user
- **Permissions**: IsAuthenticated
- **Request Body**:
  ```json
  {
    "old_password": "CurrentPass123!",
    "new_password": "NewSecurePass456!",
    "new_password_confirm": "NewSecurePass456!"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "message": "Password changed successfully"
  }
  ```
- **Features**:
  - Validates old password
  - Validates new password strength
  - Checks password history (prevents reuse)
  - Blacklists all existing tokens
  - Terminates all other sessions
  - Updates password_changed_at timestamp
  - Audit log for password change

#### **POST** `/api/v1/auth/password/reset/`
**Password Reset Request**
- **Rate Limit**: 5 attempts per hour per IP
- **Permissions**: AllowAny
- **Request Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "message": "Password reset email sent if account exists"
  }
  ```
- **Features**:
  - Sends password reset email with token
  - Token expires in 1 hour
  - Email enumeration protection (always success response)
  - Audit log for reset requests

#### **POST** `/api/v1/auth/password/reset/confirm/`
**Password Reset Confirmation**
- **Rate Limit**: 10 attempts per hour per IP
- **Permissions**: AllowAny
- **Request Body**:
  ```json
  {
    "token": "reset_token_from_email",
    "new_password": "NewSecurePass456!",
    "new_password_confirm": "NewSecurePass456!"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "message": "Password reset successfully"
  }
  ```
- **Features**:
  - Validates reset token
  - Validates new password strength
  - Checks password history
  - Blacklists all existing tokens
  - Terminates all sessions
  - Audit log for password reset

### Email Verification

#### **POST** `/api/v1/auth/email/verify/`
**Email Verification with Token**
- **Rate Limit**: 10 attempts per hour per IP
- **Permissions**: AllowAny
- **Request Body**:
  ```json
  {
    "token": "verification_token_from_email"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "message": "Email verified successfully"
  }
  ```
- **Features**:
  - Validates verification token
  - Sets email_verified = True
  - Sets email_verified_at timestamp
  - Single-use token
  - Audit log for verification

#### **POST** `/api/v1/auth/email/resend/`
**Resend Verification Email**
- **Rate Limit**: 5 attempts per hour per IP
- **Permissions**: AllowAny
- **Request Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "message": "Verification email sent if account exists"
  }
  ```
- **Features**:
  - Generates new verification token
  - Sends verification email
  - Email enumeration protection
  - Audit log for resend requests

### Session Management

#### **GET** `/api/v1/auth/sessions/`
**List User Sessions**
- **Rate Limit**: 30 attempts per hour per user
- **Permissions**: IsAuthenticated
- **Response** (200 OK):
  ```json
  {
    "sessions": [
      {
        "id": "uuid",
        "device_name": "iPhone 15 Pro",
        "device_fingerprint": "...",
        "user_agent": "Mozilla/5.0...",
        "ip_address": "192.168.1.1",
        "city": "San Francisco",
        "country": "United States",
        "is_active": true,
        "is_current": true,
        "created_at": "2025-11-01T10:00:00Z",
        "last_activity_at": "2025-11-27T15:30:00Z",
        "expires_at": "2025-12-11T10:00:00Z"
      }
    ]
  }
  ```

#### **DELETE** `/api/v1/auth/sessions/{session_id}/`
**Terminate Specific Session**
- **Rate Limit**: 30 attempts per hour per user
- **Permissions**: IsAuthenticated (own sessions only)
- **Response** (200 OK):
  ```json
  {
    "message": "Session terminated successfully"
  }
  ```
- **Features**:
  - Deactivates session
  - Blacklists associated refresh token
  - Audit log for session termination

#### **POST** `/api/v1/auth/sessions/terminate-all/`
**Terminate All Sessions**
- **Rate Limit**: 10 attempts per hour per user
- **Permissions**: IsAuthenticated
- **Response** (200 OK):
  ```json
  {
    "message": "All sessions terminated successfully",
    "terminated_count": 3
  }
  ```
- **Features**:
  - Deactivates all user sessions except current
  - Blacklists all refresh tokens
  - Audit log for bulk termination

### CSRF Protection

#### **GET** `/api/v1/auth/csrf/`
**Get CSRF Token**
- **Rate Limit**: 100 attempts per hour per IP
- **Permissions**: AllowAny
- **Response** (200 OK):
  ```json
  {
    "csrfToken": "csrf_token_value"
  }
  ```
- **Response Headers**:
  ```
  Set-Cookie: csrftoken=...; Path=/; SameSite=Lax
  ```
- **Purpose**: SPA-compatible CSRF token endpoint

### Health & Monitoring

#### **GET** `/api/v1/auth/health/`
**Authentication Service Health Check**
- **Rate Limit**: None
- **Permissions**: AllowAny
- **Response** (200 OK):
  ```json
  {
    "status": "healthy",
    "database": "connected",
    "cache": "connected",
    "timestamp": "2025-11-27T15:30:00Z"
  }
  ```

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
# Database (PostgreSQL with PostGIS)
DB_NAME=vineyard_group_fellowship
DB_USER=vineyard_group_fellowship
DB_PASSWORD=secure_password_here
DB_HOST=localhost
DB_PORT=5432
PGHOST=localhost  # Railway alternative
PGDATABASE=vineyard_group_fellowship  # Railway alternative

# Security
SECRET_KEY=your-very-secure-secret-key-here
DJANGO_SETTINGS_MODULE=vineyard_group_fellowship.settings
DJANGO_ENVIRONMENT=development  # or production

# Email (SendGrid)
SENDGRID_API_KEY=SG.your-sendgrid-api-key
DEFAULT_FROM_EMAIL=Vineyard Group Fellowship <info@vineyardgroupfellowship.org>
SERVER_EMAIL=Vineyard Group Fellowship System <info@vineyardgroupfellowship.org>
SUPPORT_EMAIL=info@vineyardgroupfellowship.org
NOREPLY_EMAIL=noreply@vineyardgroupfellowship.org

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=redis_password  # If using password auth

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8002
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8002

# Feature Flags
ENABLE_COOKIE_REFRESH_TOKEN=True

# Monitoring (Optional)
SENTRY_DSN=your-sentry-dsn-here

# Deployment (Production)
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DEBUG=False
SECURE_SSL_REDIRECT=True
```

### JWT Configuration

Located in `vineyard_group_fellowship/settings/base.py`:

```python
SIMPLE_JWT = {
    # Token Lifetimes
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # Short-lived for security
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),    # Remember me: 14 days
    
    # Token Rotation & Blacklisting
    'ROTATE_REFRESH_TOKENS': True,          # New refresh token on each refresh
    'BLACKLIST_AFTER_ROTATION': True,       # Blacklist old token after rotation
    'UPDATE_LAST_LOGIN': True,              # Update user's last_login field
    
    # Algorithm & Signing
    'ALGORITHM': 'HS256',                   # HMAC with SHA-256
    'SIGNING_KEY': SECRET_KEY,              # Use Django's SECRET_KEY
    'ISSUER': 'vineyard_group_fellowship',  # JWT issuer claim
    
    # Authentication Header
    'AUTH_HEADER_TYPES': ('Bearer',),       # Authorization: Bearer <token>
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    
    # Token Claims
    'USER_ID_FIELD': 'id',                  # User model primary key field
    'USER_ID_CLAIM': 'user_id',             # JWT claim name for user ID
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',       # JWT claim for token type
    'JTI_CLAIM': 'jti',                     # JWT ID claim (for blacklisting)
    
    # HttpOnly Cookie Configuration
    'AUTH_COOKIE': 'refresh_token',         # Cookie name
    'AUTH_COOKIE_HTTP_ONLY': True,          # XSS protection
    'AUTH_COOKIE_PATH': '/',                # Cookie path
    'AUTH_COOKIE_SAMESITE': 'Lax',         # CSRF protection
}

# Additional Cookie Settings
REFRESH_TOKEN_COOKIE_NAME = 'refresh_token'
REFRESH_TOKEN_COOKIE_MAX_AGE = 14 * 24 * 60 * 60  # 14 days
REFRESH_TOKEN_COOKIE_HTTPONLY = True
REFRESH_TOKEN_COOKIE_SECURE = True  # HTTPS only in production
REFRESH_TOKEN_COOKIE_PATH = '/'
REFRESH_TOKEN_COOKIE_SAMESITE = 'Lax'
```

### Rate Limiting Configuration

Configured via Django Ratelimit decorators:

```python
# Registration: 5 per hour per IP
@ratelimit(key='ip', rate='5/h', method='POST')

# Login: 25 per hour per IP
@ratelimit(key='ip', rate='25/h', method='POST')

# Password Reset: 5 per hour per IP
@ratelimit(key='ip', rate='5/h', method='POST')

# Token Refresh: 60 per hour per user
@ratelimit(key='user_or_ip', rate='60/h', method='POST')

# Email Verification: 10 per hour per IP
@ratelimit(key='ip', rate='10/h', method='POST')
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

## Development Setup

### Prerequisites

```bash
# Python 3.13+
python --version

# PostgreSQL 14+ with PostGIS
psql --version

# Redis 5.0+
redis-cli --version
```

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your local settings

# 3. Run migrations
python manage.py migrate

# 4. Create superuser
python manage.py createsuperuser

# 5. Start development server (port 8002)
python manage.py runserver 8002

# 6. Start Celery worker (separate terminal)
celery -A vineyard_group_fellowship worker -l info

# 7. Start Celery Beat (separate terminal)
celery -A vineyard_group_fellowship beat -l info
```

### Docker Development

```bash
# Build and start all services
docker compose up --build

# Run migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser

# View logs
docker compose logs -f web
docker compose logs -f celery
docker compose logs -f celery-beat

# Stop services
docker compose down
```

### Testing Setup

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=authentication --cov-report=html

# Run specific test categories
pytest -m security
pytest -m integration
pytest authentication/tests/test_views.py

# Generate coverage report
open htmlcov/index.html
```

## Troubleshooting

### Common Issues

#### Issue: Token Refresh Fails

**Symptoms**: 401 Unauthorized on `/api/v1/auth/token/refresh/`

**Causes**:
- Missing `refresh_token` cookie
- Token expired (>14 days)
- Token blacklisted

**Solutions**:
```python
# Check if cookie is being sent
# In browser DevTools > Network > Request Headers
Cookie: refresh_token=...

# Check token expiration
from rest_framework_simplejwt.tokens import RefreshToken
token = RefreshToken(refresh_token_string)
print(token['exp'])  # Expiration timestamp

# Clear blacklisted tokens (development only)
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
BlacklistedToken.objects.all().delete()
```

#### Issue: Rate Limiting Blocks Development

**Symptoms**: 429 Too Many Requests during testing

**Solutions**:
```python
# Option 1: Disable rate limiting in settings/local.py
RATELIMIT_ENABLE = False

# Option 2: Clear Redis cache
redis-cli FLUSHDB

# Option 3: Increase rate limits for development
@ratelimit(key='ip', rate='100/h', method='POST')  # Instead of 25/h
```

#### Issue: Email Verification Not Working

**Symptoms**: Verification emails not received

**Causes**:
- SendGrid API key not configured
- Celery worker not running
- Email in spam folder

**Solutions**:
```bash
# Check Celery worker is running
celery -A vineyard_group_fellowship inspect active

# Check email task queue
celery -A vineyard_group_fellowship inspect scheduled

# Use MailHog for local development (Docker)
# Check http://localhost:8025 for caught emails

# Verify SendGrid API key
python manage.py shell
>>> from authentication.services import EmailService
>>> EmailService.send_verification_email(user)
```

#### Issue: Database Connection Errors

**Symptoms**: `django.db.utils.OperationalError`

**Solutions**:
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check connection settings
echo $DB_HOST
echo $DB_PORT
echo $DB_NAME

# Test database connection
python manage.py dbshell

# Docker: Restart database container
docker compose restart postgres
```

#### Issue: Redis Connection Errors

**Symptoms**: `redis.exceptions.ConnectionError`

**Solutions**:
```bash
# Check Redis is running
redis-cli ping
# Expected: PONG

# Check Redis connection
redis-cli -h localhost -p 6379

# Docker: Restart Redis container
docker compose restart redis

# Check Redis configuration in settings
python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'value')
>>> cache.get('test')
```

#### Issue: CORS Errors in Frontend

**Symptoms**: `Access-Control-Allow-Origin` errors in browser console

**Solutions**:
```python
# Update CORS settings in .env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Verify settings loaded correctly
python manage.py shell
>>> from django.conf import settings
>>> print(settings.CORS_ALLOWED_ORIGINS)

# Clear browser cache and cookies
# Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
```

### Debug Mode

Enable detailed error messages:

```python
# settings/local.py
DEBUG = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'authentication': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Performance Debugging

```python
# Enable query logging
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'DEBUG',
}

# Use Django Debug Toolbar
pip install django-debug-toolbar

# Add to INSTALLED_APPS
INSTALLED_APPS += ['debug_toolbar']

# Add middleware
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
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

## API Client Examples

### JavaScript/TypeScript (React, React Native)

```typescript
// api/authClient.ts
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8002/api/v1/auth';

class AuthClient {
  private accessToken: string | null = null;

  // Register new user
  async register(data: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
  }) {
    const response = await axios.post(`${API_BASE_URL}/register/`, data);
    return response.data;
  }

  // Login
  async login(email: string, password: string) {
    const response = await axios.post(
      `${API_BASE_URL}/login/`,
      { email, password },
      { withCredentials: true } // Include cookies
    );
    
    // Store access token in memory
    this.accessToken = response.data.access;
    return response.data;
  }

  // Refresh access token
  async refreshToken() {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/token/refresh/`,
        {},
        { withCredentials: true } // Send refresh token cookie
      );
      
      this.accessToken = response.data.access;
      return response.data.access;
    } catch (error) {
      // Refresh token expired, redirect to login
      this.accessToken = null;
      throw error;
    }
  }

  // Get authorization header
  getAuthHeader() {
    return this.accessToken ? `Bearer ${this.accessToken}` : null;
  }

  // Logout
  async logout() {
    try {
      await axios.post(
        `${API_BASE_URL}/logout/`,
        {},
        {
          headers: { Authorization: this.getAuthHeader() },
          withCredentials: true
        }
      );
    } finally {
      this.accessToken = null;
    }
  }

  // Password reset request
  async requestPasswordReset(email: string) {
    const response = await axios.post(`${API_BASE_URL}/password/reset/`, { email });
    return response.data;
  }

  // Password reset confirm
  async confirmPasswordReset(token: string, newPassword: string) {
    const response = await axios.post(`${API_BASE_URL}/password/reset/confirm/`, {
      token,
      new_password: newPassword
    });
    return response.data;
  }

  // Email verification
  async verifyEmail(token: string) {
    const response = await axios.post(`${API_BASE_URL}/email/verify/`, { token });
    return response.data;
  }

  // Get user sessions
  async getSessions() {
    const response = await axios.get(`${API_BASE_URL}/sessions/`, {
      headers: { Authorization: this.getAuthHeader() }
    });
    return response.data.sessions;
  }

  // Terminate session
  async terminateSession(sessionId: string) {
    const response = await axios.delete(`${API_BASE_URL}/sessions/${sessionId}/`, {
      headers: { Authorization: this.getAuthHeader() }
    });
    return response.data;
  }
}

export const authClient = new AuthClient();
```

### Axios Interceptor for Token Refresh

```typescript
// api/interceptors.ts
import axios from 'axios';
import { authClient } from './authClient';

// Add request interceptor to include access token
axios.interceptors.request.use(
  (config) => {
    const authHeader = authClient.getAuthHeader();
    if (authHeader && config.headers) {
      config.headers.Authorization = authHeader;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor to handle token refresh
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retried, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Refresh the access token
        await authClient.refreshToken();
        
        // Retry original request with new token
        originalRequest.headers.Authorization = authClient.getAuthHeader();
        return axios(originalRequest);
      } catch (refreshError) {
        // Refresh failed, redirect to login
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
```

### Python Client

```python
# auth_client.py
import requests
from typing import Optional, Dict

class AuthClient:
    def __init__(self, base_url: str = "http://localhost:8002/api/v1/auth"):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token: Optional[str] = None

    def register(self, email: str, password: str, first_name: str, last_name: str) -> Dict:
        """Register a new user."""
        response = self.session.post(
            f"{self.base_url}/register/",
            json={
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name,
            }
        )
        response.raise_for_status()
        return response.json()

    def login(self, email: str, password: str) -> Dict:
        """Login and store access token."""
        response = self.session.post(
            f"{self.base_url}/login/",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data["access"]
        # Refresh token stored in session cookies automatically
        return data

    def refresh_token(self) -> str:
        """Refresh access token using refresh token from cookies."""
        response = self.session.post(f"{self.base_url}/token/refresh/")
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data["access"]
        return self.access_token

    def logout(self) -> Dict:
        """Logout and clear tokens."""
        response = self.session.post(
            f"{self.base_url}/logout/",
            headers=self._get_headers()
        )
        response.raise_for_status()
        
        self.access_token = None
        return response.json()

    def get_sessions(self) -> list:
        """Get all active sessions."""
        response = self.session.get(
            f"{self.base_url}/sessions/",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()["sessions"]

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}

# Usage
client = AuthClient()
client.register("user@example.com", "Password123!", "John", "Doe")
client.login("user@example.com", "Password123!")
sessions = client.get_sessions()
```

## Best Practices

### Frontend Integration

#### Token Storage

```typescript
// ✅ RECOMMENDED: Memory-only storage for access tokens
class TokenManager {
  private accessToken: string | null = null;

  setAccessToken(token: string) {
    this.accessToken = token;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  clearAccessToken() {
    this.accessToken = null;
  }
}

// ❌ AVOID: Storing tokens in localStorage (XSS vulnerability)
localStorage.setItem('accessToken', token); // DON'T DO THIS
```

#### Cookie Handling

```typescript
// ✅ Let the browser handle httpOnly cookies automatically
axios.post('/api/v1/auth/login/', data, {
  withCredentials: true  // Essential for cookie-based auth
});

// ❌ Never try to manually access httpOnly cookies
document.cookie.split('; ').find(row => row.startsWith('refresh_token=')); // Won't work
```

#### Error Handling

```typescript
// ✅ Handle authentication errors gracefully
try {
  await authClient.login(email, password);
} catch (error) {
  if (error.response?.status === 401) {
    // Invalid credentials
    showError("Invalid email or password");
  } else if (error.response?.status === 429) {
    // Rate limited
    showError("Too many attempts. Please try again later.");
  } else if (error.response?.status === 403) {
    // Account locked or email not verified
    showError(error.response.data.error);
  } else {
    // Generic error
    showError("An error occurred. Please try again.");
  }
}
```

### Security Recommendations

#### Password Requirements

```typescript
// Enforce on frontend (backend validates too)
const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$/;

function validatePassword(password: string): boolean {
  return PASSWORD_REGEX.test(password);
}
```

#### CSRF Protection

```typescript
// Get CSRF token on app initialization
async function initializeApp() {
  const response = await axios.get('/api/v1/auth/csrf/');
  const csrfToken = response.data.csrfToken;
  
  // Set CSRF token for all requests
  axios.defaults.headers.common['X-CSRFToken'] = csrfToken;
}
```

#### Session Management

```typescript
// Periodically refresh token to maintain session
setInterval(async () => {
  try {
    await authClient.refreshToken();
  } catch (error) {
    // Refresh failed, redirect to login
    window.location.href = '/login';
  }
}, 14 * 60 * 1000); // Refresh every 14 minutes (before 15min expiry)
```

### Mobile App Considerations

```typescript
// Use secure storage instead of cookies
import * as SecureStore from 'expo-secure-store';

class MobileAuthClient {
  async login(email: string, password: string) {
    const response = await fetch(`${API_URL}/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    
    // Store tokens securely
    await SecureStore.setItemAsync('accessToken', data.access);
    await SecureStore.setItemAsync('refreshToken', data.refresh);
    
    return data;
  }

  async getAccessToken(): Promise<string | null> {
    return await SecureStore.getItemAsync('accessToken');
  }

  async refreshToken(): Promise<string> {
    const refreshToken = await SecureStore.getItemAsync('refreshToken');
    
    const response = await fetch(`${API_URL}/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken })
    });
    
    const data = await response.json();
    await SecureStore.setItemAsync('accessToken', data.access);
    
    return data.access;
  }
}
```

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

# Run specific test file
pytest authentication/tests/test_views.py

# Run tests with verbose output
pytest -v authentication/tests/

# Generate HTML coverage report
pytest --cov=authentication --cov-report=html authentication/tests/
open htmlcov/index.html
```

### Example Tests

```python
# authentication/tests/test_views.py
import pytest
from rest_framework.test import APIClient
from authentication.tests.factories import UserFactory

@pytest.mark.django_db
class TestLoginEndpoint:
    def test_successful_login(self):
        """Test user can login with valid credentials."""
        user = UserFactory(email="test@example.com")
        user.set_password("Password123!")
        user.save()
        
        client = APIClient()
        response = client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'Password123!'
        })
        
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh_token' in response.cookies

    def test_login_rate_limiting(self):
        """Test login endpoint is rate limited."""
        client = APIClient()
        
        # Make 26 failed login attempts (limit is 25/hour)
        for _ in range(26):
            response = client.post('/api/v1/auth/login/', {
                'email': 'test@example.com',
                'password': 'wrong'
            })
        
        # 26th request should be rate limited
        assert response.status_code == 429
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

## Deployment

### Production Checklist

```bash
# ✅ Security Configuration
- [ ] DEBUG = False
- [ ] Strong SECRET_KEY (min 50 characters)
- [ ] ALLOWED_HOSTS configured
- [ ] SECURE_SSL_REDIRECT = True
- [ ] SECURE_HSTS_SECONDS = 31536000
- [ ] SESSION_COOKIE_SECURE = True
- [ ] CSRF_COOKIE_SECURE = True
- [ ] SECURE_BROWSER_XSS_FILTER = True
- [ ] SECURE_CONTENT_TYPE_NOSNIFF = True

# ✅ Database Configuration
- [ ] PostgreSQL connection pooling (PGBouncer)
- [ ] Database backup strategy
- [ ] Read replicas for scaling
- [ ] Connection limits configured

# ✅ Redis Configuration
- [ ] Redis password authentication
- [ ] Persistent storage enabled
- [ ] Memory limits configured
- [ ] Backup strategy in place

# ✅ Email Configuration
- [ ] SendGrid API key configured
- [ ] Email templates tested
- [ ] Bounce handling configured
- [ ] Unsubscribe links implemented

# ✅ Monitoring
- [ ] Sentry error tracking
- [ ] Performance monitoring
- [ ] Log aggregation
- [ ] Health check endpoints
- [ ] Uptime monitoring

# ✅ Rate Limiting
- [ ] Redis backend configured
- [ ] Rate limits tested
- [ ] IP whitelisting for internal tools

# ✅ Celery
- [ ] Worker process monitoring
- [ ] Beat scheduler running
- [ ] Task retry configuration
- [ ] Dead letter queue handling
```

### Environment-Specific Settings

```python
# settings/production.py
from .base import *

# Security
DEBUG = False
SECRET_KEY = env('SECRET_KEY')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# HTTPS
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'sentry': {
            'class': 'sentry_sdk.integrations.logging.EventHandler',
            'level': 'ERROR',
        },
    },
    'loggers': {
        'authentication': {
            'handlers': ['console', 'sentry'],
            'level': 'INFO',
        },
        'django.security': {
            'handlers': ['console', 'sentry'],
            'level': 'WARNING',
        },
    },
}
```

### Docker Production Build

```dockerfile
# Dockerfile (Production)
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8002", "--workers", "4", "--timeout", "60", "vineyard_group_fellowship.wsgi:application"]
```

### Railway Deployment

```json
// railway.json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python manage.py migrate && gunicorn vineyard_group_fellowship.wsgi:application --bind 0.0.0.0:$PORT",
    "healthcheckPath": "/api/v1/auth/health/",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

```toml
# nixpacks.toml
[phases.setup]
nixPkgs = ["python313", "postgresql", "gdal"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[phases.build]
cmds = ["python manage.py collectstatic --noinput"]

[start]
cmd = "python manage.py migrate && gunicorn vineyard_group_fellowship.wsgi:application --bind 0.0.0.0:$PORT"
```

## Monitoring & Observability

### Sentry Integration

```python
# settings/base.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

sentry_sdk.init(
    dsn=env('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
        RedisIntegration(),
    ],
    traces_sample_rate=0.1,  # 10% of transactions
    profiles_sample_rate=0.1,  # 10% of profiles
    send_default_pii=False,  # Don't send PII
    environment=env('DJANGO_ENVIRONMENT', default='development'),
    
    # Custom error filtering
    before_send=lambda event, hint: event if event.get('level') != 'info' else None,
)
```

### Health Check Monitoring

```python
# authentication/view_modules/health.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from django.core.cache import cache
import redis

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Comprehensive health check for monitoring."""
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = 'connected'
    except Exception as e:
        health_status['checks']['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Redis/Cache check
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health_status['checks']['cache'] = 'connected'
        else:
            health_status['checks']['cache'] = 'error: write/read failed'
            health_status['status'] = 'degraded'
    except Exception as e:
        health_status['checks']['cache'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Celery check (optional)
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        workers = inspect.active()
        health_status['checks']['celery'] = 'workers active' if workers else 'no workers'
    except Exception as e:
        health_status['checks']['celery'] = f'error: {str(e)}'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return Response(health_status, status=status_code)
```

### Audit Log Analysis

```python
# Query failed login attempts
from authentication.models import AuditLog
from django.utils import timezone
from datetime import timedelta

# Failed logins in last hour
recent_failures = AuditLog.objects.filter(
    event_type='login_failed',
    timestamp__gte=timezone.now() - timedelta(hours=1)
).values('ip_address').annotate(
    count=models.Count('id')
).order_by('-count')

# Suspicious activity (multiple failed logins from same IP)
suspicious_ips = recent_failures.filter(count__gte=10)

# Account lockout events
lockouts = AuditLog.objects.filter(
    event_type='account_locked',
    timestamp__gte=timezone.now() - timedelta(days=1)
).count()
```

### Performance Monitoring

```python
# middleware/performance.py
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('authentication')

class PerformanceMonitoringMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()
    
    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            
            # Log slow requests (>1 second)
            if duration > 1.0:
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.2f}s"
                )
            
            # Add performance header
            response['X-Response-Time'] = f"{duration:.3f}s"
        
        return response
```

### Key Metrics to Monitor

```python
# Prometheus metrics (optional)
from prometheus_client import Counter, Histogram

# Authentication metrics
login_attempts_total = Counter(
    'auth_login_attempts_total',
    'Total login attempts',
    ['status']  # success, failed
)

login_duration = Histogram(
    'auth_login_duration_seconds',
    'Login request duration'
)

password_reset_requests = Counter(
    'auth_password_reset_requests_total',
    'Total password reset requests'
)

active_sessions = Gauge(
    'auth_active_sessions_total',
    'Total active user sessions'
)
```

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

### Security Headers

```python
# Implemented via Django SecurityMiddleware
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "data:")
```

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
