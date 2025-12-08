"""
Development settings for Vineyard Group Fellowship project.

This file contains settings specific to local development.
"""

from .base import *

# ============================================================================
# DEBUG & DEVELOPMENT
# ============================================================================

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '10.35.14.78']

# ============================================================================
# DATABASE - Development
# ============================================================================

# PostgreSQL configuration (required for production parity)
# No SQLite fallback to ensure development-production consistency
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default=5432, cast=int),
        'CONN_MAX_AGE': 600,  # Connection pooling for better performance
        'OPTIONS': {
            'connect_timeout': 60,
        },
    }
}

# Enable PostgreSQL specific features (gis is already in base.py)
INSTALLED_APPS += ['django.contrib.postgres']

# ============================================================================
# EMAIL BACKEND - Development
# ============================================================================

# Choose email backend based on environment configuration
# Option 1: SendGrid Web API (production-like, requires SENDGRID_API_KEY)
# Option 2: MailHog SMTP (local email testing)
# Option 3: Console (prints emails to console)

SENDGRID_API_KEY = config('SENDGRID_API_KEY', default='')

if SENDGRID_API_KEY:
    # Use SendGrid Web API (same as production)
    # Custom SendGrid backend enabled
    EMAIL_BACKEND = 'core.email_backends.SendGridWebAPIBackend'
    DEFAULT_FROM_EMAIL = config(
        'DEFAULT_FROM_EMAIL', default='Vineyard Group Fellowship <info@vineyardgroupfellowship.org>')
    SERVER_EMAIL = config(
        'SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)
    SUPPORT_EMAIL = config(
        'SUPPORT_EMAIL', default=DEFAULT_FROM_EMAIL)
    NOREPLY_EMAIL = config(
        'NOREPLY_EMAIL', default=DEFAULT_FROM_EMAIL)
elif config('USE_MAILHOG', default=False, cast=bool):
    # Use MailHog for local email testing
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 1025
    EMAIL_USE_TLS = False
    DEFAULT_FROM_EMAIL = 'noreply@Vineyard Group Fellowship.local'
    SERVER_EMAIL = DEFAULT_FROM_EMAIL
    SUPPORT_EMAIL = DEFAULT_FROM_EMAIL
    NOREPLY_EMAIL = DEFAULT_FROM_EMAIL
else:
    # Default: Print emails to console (no external service needed)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'noreply@Vineyard Group Fellowship.local'
    SERVER_EMAIL = DEFAULT_FROM_EMAIL
    SUPPORT_EMAIL = DEFAULT_FROM_EMAIL
    NOREPLY_EMAIL = DEFAULT_FROM_EMAIL

# ============================================================================
# CORS & CSRF - Development
# ============================================================================

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Keep secure even in development

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8080',
    'http://127.0.0.1:8080',
]

CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = 'Lax'

# ============================================================================
# SESSION CONFIGURATION - Development
# ============================================================================

SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = 'Lax'

# ============================================================================
# REFRESH TOKEN COOKIE - Development (HTTP)
# ============================================================================

# Allow cookies over HTTP in development
REFRESH_TOKEN_COOKIE_SECURE = False  # Allow HTTP in development

# ============================================================================
# SECURITY - Development (Relaxed)
# ============================================================================

# Relax security for development
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# ============================================================================
# STATIC FILES - Development
# ============================================================================

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# ============================================================================
# CACHE - Development
# ============================================================================

# Use Redis if CACHE_URL is provided (Docker), otherwise use LocMem
CACHE_URL = config('CACHE_URL', default=None)

if CACHE_URL:
    # Use Django's built-in Redis cache backend
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': CACHE_URL,
        }
    }
else:
    # Fallback to in-memory cache for local development without Docker
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# ============================================================================
# LOGGING - Development
# ============================================================================

LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['vineyard_group_fellowship']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'INFO'

# Add Django SQL queries logging in development
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'DEBUG' if config('LOG_SQL', default=False, cast=bool) else 'INFO',
    'propagate': False,
}

# ============================================================================
# DEVELOPMENT TOOLS
# ============================================================================

# Add development-specific apps
INSTALLED_APPS += [
    # 'django_extensions',  # Uncomment if installed
    # 'debug_toolbar',      # Uncomment if installed
]

# Django Debug Toolbar (if installed)
if 'debug_toolbar' in INSTALLED_APPS:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Performance Monitoring Middleware (Development)
MIDDLEWARE.append(
    'core.middleware.performance.PerformanceMonitoringMiddleware')
MIDDLEWARE.append('core.middleware.performance.QueryCountWarningMiddleware')

# ============================================================================
# API THROTTLING - Development (Relaxed)
# ============================================================================

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '1000/hour',
    'user': '10000/hour',
    'auth': '100/hour',  # General authentication operations (login, logout)
    'login': '100/hour',
    'password_reset': '20/hour',
    'password_reset_confirm': '50/hour',  # Password reset confirmation
    'registration': '20/hour',  # Added for registration endpoint
    'token_refresh': '60/hour',  # Token refresh rate
    'email_verification': '50/hour',  # Email verification attempts
    'email_verification_confirm': '50/hour',  # Email verification confirmation
    'email_verification_resend': '20/hour',  # Resend verification email
    'onboarding': '100/hour',  # Relaxed for development
    'device_management': '200/hour',  # Device/session management
    'content_moderation': '500/hour',  # Content creation/moderation
}

# ============================================================================
# JWT - Development (Longer tokens)
# ============================================================================

SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),  # Longer for development
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),  # Longer for development
})

# ============================================================================
# DEVELOPMENT ENVIRONMENT VARIABLES
# ============================================================================

# Site configuration
SITE_NAME = 'Vineyard Group Fellowship (Dev)'
SITE_DOMAIN = 'localhost:8001'
FRONTEND_URL = 'http://localhost:3000'
BACKEND_URL = 'http://localhost:8001'

# Development flags
ENABLE_GEOIP_TIMEZONE = False
GEOIP_PATH = None

print("🔧 Development settings loaded")
print(f"📧 Email backend: MailHog (localhost:1025)")
print(f"🗄️  Database: PostgreSQL (required)")
print(f"🌐 CORS origins: {CORS_ALLOWED_ORIGINS}")

# ============================================================================
# PROFILE PHOTO SETTINGS - Development
# ============================================================================

# Disable moderation for development to allow immediate photo viewing
PROFILE_PHOTO_SETTINGS = {
    'REQUIRE_MODERATION': False,  # Auto-approve photos in development
    'AUTO_APPROVE_SIZE_LIMIT': 2 * 1024 * 1024,  # 2MB limit for auto-approval
    'ALLOWED_TYPES': [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/webp',
        'image/gif'
    ],
}
