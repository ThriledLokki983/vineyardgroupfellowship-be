"""
Production settings for Vineyard Group Fellowship project.

This file contains settings specific to production deployment.
Security and performance optimized.
"""

from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

# ============================================================================
# SECRET KEY VALIDATION
# ============================================================================

# Validate SECRET_KEY in production
if SECRET_KEY.startswith('django-insecure-'):
    raise ValueError(
        "Production SECRET_KEY must not use the default insecure key. "
        "Please set a proper SECRET_KEY environment variable."
    )

if len(SECRET_KEY) < 32:
    raise ValueError(
        "Production SECRET_KEY must be at least 32 characters long for security. "
        f"Current length: {len(SECRET_KEY)}"
    )

# Additional security check for character diversity
unique_chars = len(set(SECRET_KEY))
if unique_chars < 10:
    raise ValueError(
        f"Production SECRET_KEY has insufficient character diversity ({unique_chars} unique characters). "
        "Please use a more complex secret key."
    )

# Silence Django's built-in SECRET_KEY warning since we have our own validation
SILENCED_SYSTEM_CHECKS = [
    # SECRET_KEY length/complexity warning (we have custom validation)
    'security.W009',
]

# ============================================================================
# MIDDLEWARE - Production
# ============================================================================

# Insert WhiteNoise middleware after SecurityMiddleware for production
MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,
    'whitenoise.middleware.WhiteNoiseMiddleware',
)

# Add media security middleware for production media serving
MIDDLEWARE.insert(
    MIDDLEWARE.index('whitenoise.middleware.WhiteNoiseMiddleware') + 1,
    'core.middleware.media.MediaSecurityMiddleware',
)

# ============================================================================
# PRODUCTION SECURITY
# ============================================================================

DEBUG = False

# Use ALLOWED_HOSTS from environment variable if provided, otherwise use defaults
ALLOWED_HOSTS_ENV = config('ALLOWED_HOSTS', default='')

if ALLOWED_HOSTS_ENV:
    # Parse manually to handle single values like '*' correctly
    if ALLOWED_HOSTS_ENV == '*':
        ALLOWED_HOSTS = ['*']
    else:
        # Split by comma and strip whitespace
        ALLOWED_HOSTS = [host.strip()
                         for host in ALLOWED_HOSTS_ENV.split(',') if host.strip()]
else:
    # Fallback to hardcoded values
    ALLOWED_HOSTS = [
        config('RAILWAY_PUBLIC_DOMAIN', default=''),
        config('CUSTOM_DOMAIN', default=''),
        'healthcheck.railway.app',  # Railway health check hostname
        'api.vineyardgroupfellowship.org',  # Primary API domain
        'vineyardgroupfellowship.org',  # Primary frontend domain
        'www.vineyardgroupfellowship.org',  # www subdomain
        'vineyard-group-fellowship.org',  # Legacy domain
        'www.vineyard-group-fellowship.org',  # Legacy www subdomain
        'api.vineyardgroupfellowship.org',  # Legacy API subdomain
        'vineyard-group-fellowship.site',  # Alternative domain
        'www.vineyard-group-fellowship.site',  # Alternative www subdomain
        '.railway.app',    # Railway subdomains
        '.up.railway.app',  # Railway public domains
        # Your specific Railway domain
        'vineyard-group-fellowship-production.up.railway.app',
        'localhost',       # For local Docker testing
        '127.0.0.1',      # For local Docker testing
    ]

# Remove empty strings
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]

# ============================================================================
# DATABASE - Production (PostgreSQL)
# ============================================================================

# Railway provides DATABASE_URL, but also support individual variables
DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    # Parse DATABASE_URL (Railway style)
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=60,
        )
    }
    # Add SSL options for Railway PostgreSQL
    DATABASES['default']['OPTIONS'] = {
        'sslmode': 'prefer',  # Less strict than 'require'
    }
else:
    # Fallback to individual variables (Railway style)
    # Railway provides these as PGHOST, PGDATABASE, etc.
    db_name = config('POSTGRES_DB', default=config(
        'PGDATABASE', default=config('DB_NAME', default='dummy')))
    db_user = config('POSTGRES_USER', default=config(
        'PGUSER', default=config('DB_USER', default='dummy')))
    db_password = config('POSTGRES_PASSWORD', default=config(
        'PGPASSWORD', default=config('DB_PASSWORD', default='dummy')))
    db_host = config('POSTGRES_HOST', default=config(
        'PGHOST', default=config('DB_HOST', default='dummy')))
    db_port = config('POSTGRES_PORT', default=config(
        'PGPORT', default=config('DB_PORT', default=5432)), cast=int)

    # Check if we have valid database configuration
    if db_host == 'dummy' or db_name == 'dummy':
        raise ValueError(
            "Database configuration is incomplete. Please set either:\n"
            "1. DATABASE_URL environment variable, or\n"
            "2. PGHOST, PGDATABASE, PGUSER, PGPASSWORD environment variables (Railway style), or\n"
            "3. DB_HOST, DB_NAME, DB_USER, DB_PASSWORD environment variables\n"
            f"Current values: HOST={db_host}, NAME={db_name}"
        )

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port,
            'CONN_MAX_AGE': 60,
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }

# ============================================================================
# EMAIL BACKEND - Production
# ============================================================================

# Use SendGrid Web API (SMTP is blocked on Railway)
# This uses our custom backend that calls SendGrid's HTTP API directly
EMAIL_BACKEND = 'core.email_backends.SendGridWebAPIBackend'

# SendGrid API Key (from environment variable)
SENDGRID_API_KEY = config('SENDGRID_API_KEY', default='')

# Email settings - Using domain-authenticated SendGrid email
DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL', default='Vineyard Group Fellowship <info@vineyardgroupfellowship.org>')
SERVER_EMAIL = config(
    'SERVER_EMAIL', default='Vineyard Group Fellowship System <info@vineyardgroupfellowship.org>')

# Additional email addresses for specific purposes
SUPPORT_EMAIL = config(
    'SUPPORT_EMAIL', default='info@vineyardgroupfellowship.org')
NOREPLY_EMAIL = config(
    'NOREPLY_EMAIL', default='noreply@vineyardgroupfellowship.org')

# Alternative: Use django-anymail (uncomment to switch)
# EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
# ANYMAIL = {
#     "SENDGRID_API_KEY": config('SENDGRID_API_KEY', default=''),
# }

# Legacy SMTP settings (kept for reference, but not used)
# EMAIL_HOST = config('EMAIL_HOST', default='smtp.sendgrid.net')
# EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
# EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
# EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='apikey')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
# EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=60, cast=int)

# ============================================================================
# SECURITY HEADERS - Production
# ============================================================================

# Allow SSL redirect to be disabled via environment variable for Railway health checks
# Railway health checks use HTTP internally, so we need to allow that
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# ============================================================================
# CSRF & CORS - Production
# ============================================================================

# Cross-Origin Configuration Summary:
# Frontend: https://vineyard-group-fellowship.org
# Backend:  https://api.vineyardgroupfellowship.org
#
# All cookies must use SameSite='None' + Secure=True for cross-origin requests
# to work properly between different domains.

# Configure for your production frontend domain
CORS_ALLOWED_ORIGINS = [
    "https://vineyardgroupfellowship.org",       # Primary frontend domain
    "https://www.vineyardgroupfellowship.org",   # www subdomain
    "https://vineyard-group-fellowship.org",     # Legacy domain
    "https://www.vineyard-group-fellowship.org",  # Legacy www subdomain
    # Removed backend URL - backends don't need CORS to themselves
    "https://vineyard-group-fellowship.site",    # Alternative domain
    "https://www.vineyard-group-fellowship.site",  # Alternative www subdomain
    # Backend Railway domain (if needed for admin)
    "https://vineyard-group-fellowship-production.up.railway.app",
    # Frontend Railway domain
    "https://Vineyard Group Fellowship-frontend-production.up.railway.app",
    "http://localhost:3000",  # Local frontend development
    "http://localhost:5173",  # Vite default port
    "http://127.0.0.1:3000",  # Local frontend (IP)
    "http://127.0.0.1:5173",  # Vite default port (IP)
    config('FRONTEND_URL', default=''),
]
CORS_ALLOWED_ORIGINS = [origin for origin in CORS_ALLOWED_ORIGINS if origin]

# CORS settings for cross-origin cookies
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Explicitly set to False for security

# CORS headers for media files
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'range',  # For video/audio streaming
    'cache-control',  # For media caching
]

CORS_EXPOSE_HEADERS = [
    'content-length',
    'content-range',
    'accept-ranges',
    'cache-control',
    'etag',
    'last-modified',
]

CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()

# Secure cookies
CSRF_COOKIE_SECURE = True
# Required for cross-origin requests (vineyard-group-fellowship.org -> api.vineyardgroupfellowship.org)
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_HTTPONLY = False  # Allow frontend JS to read CSRF token
CSRF_COOKIE_NAME = 'csrftoken'  # Standard Django CSRF cookie name
CSRF_COOKIE_DOMAIN = None  # Don't restrict domain for cross-origin setup
CSRF_USE_SESSIONS = False  # Use cookies, not sessions for CSRF

# ============================================================================
# SESSION CONFIGURATION - Production
# ============================================================================

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'None'  # Changed from 'Lax' for cross-origin support
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_DOMAIN = None  # Don't restrict domain for cross-origin

# ============================================================================
# REFRESH TOKEN COOKIE - Production (HTTPS Only)
# ============================================================================

# Enforce secure cookies in production (HTTPS only)
REFRESH_TOKEN_COOKIE_SECURE = True  # HTTPS only

# Cross-origin cookie settings for vineyard-group-fellowship.org -> api.vineyardgroupfellowship.org
REFRESH_TOKEN_COOKIE_SAMESITE = 'None'  # Required for cross-origin requests
REFRESH_TOKEN_COOKIE_DOMAIN = None  # Don't restrict domain for cross-origin

# ============================================================================
# STATIC FILES - Production
# ============================================================================

# Use WhiteNoise for static file serving
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# WhiteNoise configuration
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = False
WHITENOISE_MAX_AGE = 31536000  # 1 year

# ============================================================================
# CACHE - Production (Redis with Database fallback)
# ============================================================================

# Railway Redis configuration
REDIS_URL = config('REDIS_URL', default=None)

if REDIS_URL:
    # Use Django's built-in Redis cache backend (Django 4.0+)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
    # Use Redis for sessions
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Fallback to database cache when Redis is not available
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table',
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ============================================================================
# LOGGING - Production
# ============================================================================

LOGGING['root']['level'] = 'WARNING'
LOGGING['loggers']['vineyard_group_fellowship']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'WARNING'

# Add file logging in production
LOGGING['handlers']['file'] = {
    'level': 'ERROR',
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': '/tmp/django.log',
    'maxBytes': 1024*1024*10,  # 10 MB
    'backupCount': 5,
    'formatter': 'verbose',
}

LOGGING['loggers']['vineyard_group_fellowship']['handlers'].append('file')

# ============================================================================
# MONITORING - Sentry
# ============================================================================

SENTRY_DSN = config('SENTRY_DSN', default=None)

if SENTRY_DSN:
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
                signals_spans=True,
            ),
            sentry_logging,
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment=config('SENTRY_ENVIRONMENT', default='production'),
        release=config('RAILWAY_GIT_COMMIT_SHA', default='unknown'),
        before_send=lambda event, hint: event if not DEBUG else None,
    )

# ============================================================================
# API THROTTLING - Production (Strict)
# ============================================================================

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100/hour',
    'user': '1000/hour',
    'auth': '20/hour',  # General authentication operations (login, logout)
    'login': '10/hour',
    'password_reset': '5/hour',
    'password_reset_confirm': '10/hour',  # Password reset confirmation
    'registration': '5/hour',
    'token_refresh': '30/hour',  # Token refresh rate (production)
    'email_verification': '10/hour',  # Email verification attempts
    'email_verification_confirm': '10/hour',  # Email verification confirmation
    'email_verification_resend': '5/hour',  # Resend verification email
    'onboarding': '15/hour',  # Conservative for production
    'device_management': '50/hour',  # Device/session management
    'content_moderation': '100/hour',  # Content creation/moderation
}

# ============================================================================
# JWT - Production (Secure)
# ============================================================================

SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    # Override cookie settings for cross-origin support
    'AUTH_COOKIE_SAMESITE': 'None',  # Required for cross-origin
})

# ============================================================================
# PRODUCTION ENVIRONMENT VARIABLES
# ============================================================================

SITE_NAME = 'Vineyard Group Fellowship'
SITE_DOMAIN = config('CUSTOM_DOMAIN', default='vineyard-group-fellowship.org')
FRONTEND_URL = config(
    'FRONTEND_URL', default='https://vineyard-group-fellowship.org')
BACKEND_URL = config(
    'BACKEND_URL', default='https://api.vineyardgroupfellowship.org')

# Production flags
ENABLE_GEOIP_TIMEZONE = config(
    'ENABLE_GEOIP_TIMEZONE', default=True, cast=bool)
GEOIP_PATH = config('GEOIP_PATH', default=None)

# API Documentation
ENABLE_API_DOCS = config('ENABLE_API_DOCS', default=True, cast=bool)

# ============================================================================
# PERFORMANCE OPTIMIZATIONS
# ============================================================================

# Optimize database queries
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Template caching
if not DEBUG:
    TEMPLATES[0]['APP_DIRS'] = False  # Must be False when loaders is defined
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]

# ============================================================================
# HEALTH CHECKS
# ============================================================================

# Add health check URLs for Railway
HEALTH_CHECK_URL = '/health/'

# Don't log health check requests
LOGGING['loggers']['django.server'] = {
    'handlers': ['console'],
    'level': 'INFO',
    'propagate': False,
}

# ============================================================================
# MEDIA FILES - Production
# ============================================================================

# Production media serving configuration
# For Railway deployment, media files are served via volume mounts
# Future: Can be migrated to S3/CloudFlare for scaling

# Media file settings (inherited from base.py)
# MEDIA_URL = '/media/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Production-specific media configuration
MEDIA_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Enable production media serving (temporary until S3/CDN migration)
SERVE_MEDIA_IN_PRODUCTION = config(
    'SERVE_MEDIA_IN_PRODUCTION', default=True, cast=bool)

# Security headers for media files
MEDIA_FILE_SECURITY_HEADERS = {
    'Cache-Control': 'public, max-age=86400',  # 24 hours
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
}

# File upload limits (for photo uploads)
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# ============================================================================
# CDN/S3 FRAMEWORK (Future Scaling)
# ============================================================================

# Framework for S3/CloudFlare CDN integration
# Uncomment and configure when ready to scale beyond Railway volumes

# AWS S3 Configuration (disabled by default)
USE_S3_STORAGE = config('USE_S3_STORAGE', default=False, cast=bool)

if USE_S3_STORAGE:
    # AWS S3 settings
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = config(
        'AWS_STORAGE_BUCKET_NAME', default='Vineyard Group Fellowship-media')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = config('AWS_S3_CUSTOM_DOMAIN', default='')

    # S3 security and performance settings
    AWS_DEFAULT_ACL = 'private'  # Private by default for user photos
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',  # 24 hours
    }
    AWS_S3_FILE_OVERWRITE = False  # Don't overwrite existing files
    AWS_QUERYSTRING_AUTH = True  # Use signed URLs for private files
    AWS_QUERYSTRING_EXPIRE = 3600  # URLs expire after 1 hour

    # Use S3 for media files when enabled
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN or AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/'

# CloudFlare CDN Configuration (disabled by default)
USE_CLOUDFLARE_CDN = config('USE_CLOUDFLARE_CDN', default=False, cast=bool)

if USE_CLOUDFLARE_CDN:
    CLOUDFLARE_ZONE_ID = config('CLOUDFLARE_ZONE_ID', default='')
    CLOUDFLARE_API_TOKEN = config('CLOUDFLARE_API_TOKEN', default='')
    CLOUDFLARE_MEDIA_DOMAIN = config(
        'CLOUDFLARE_MEDIA_DOMAIN', default='media.Vineyard Group Fellowship.site')

    # Override media URL when CloudFlare is enabled
    if not USE_S3_STORAGE:  # Only if not using S3
        MEDIA_URL = f'https://{CLOUDFLARE_MEDIA_DOMAIN}/media/'

print("🚀 Production settings loaded")
print(f"🌐 Allowed hosts: {ALLOWED_HOSTS}")
print(f"📧 Email backend: {EMAIL_BACKEND}")
print(
    f"📨 SendGrid API: {'Configured' if SENDGRID_API_KEY else 'Not configured'}")
print(f"🗄️  Database: PostgreSQL ({config('PGHOST', default='Unknown')})")
print(f"📊 Monitoring: {'Sentry enabled' if SENTRY_DSN else 'No monitoring'}")
print(f"🎯 Cache backend: {'Redis' if REDIS_URL else 'Database'}")
print(f"📁 Media storage: {'S3' if USE_S3_STORAGE else 'File System'}")
print(f"🌐 CDN: {'CloudFlare' if USE_CLOUDFLARE_CDN else 'Direct serving'}")
