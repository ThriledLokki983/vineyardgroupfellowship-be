"""
Base Django settings for vineyard_group_fellowship project.

This file contains settings common to all environments.
Environment-specific settings should be in development.py, production.py, etc.
"""

from core.api_tags import get_api_tags_metadata
import os
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

# Set the Django environment for proper configuration
DJANGO_ENVIRONMENT = config('DJANGO_ENVIRONMENT', default='development')

# ============================================================================
# SECURITY
# ============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# ============================================================================
# APPLICATION DEFINITION
# ============================================================================

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_otp',
    'drf_spectacular',
    'csp',
    'anymail',
]

LOCAL_APPS = [
    'core',
    'authentication',
    'profiles',
    'privacy',
]

INSTALLED_APPS = [
    # Django Core Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party Apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',  # OpenAPI documentation
    'django_otp',
    'csp',
    # 'anymail',  # Email backend for SendGrid/Mailgun/etc (using custom backend instead)

    # Local Apps
    'core',
    'authentication',
    'profiles',
    'privacy',
    'monitoring',
    'onboarding',
    'group',
]

# ============================================================================
# MIDDLEWARE
# ============================================================================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'monitoring.middleware.performance.PerformanceMonitoringMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ============================================================================
# URL & WSGI
# ============================================================================

ROOT_URLCONF = 'vineyard_group_fellowship.urls'
WSGI_APPLICATION = 'vineyard_group_fellowship.wsgi.application'

# ============================================================================
# TEMPLATES
# ============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Added templates directory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ============================================================================
# DATABASE
# ============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default=5432, cast=int),
        'CONN_MAX_AGE': 600,  # Persistent connections
        'OPTIONS': {
            'connect_timeout': 60,
        },
    }
}

# ============================================================================
# PASSWORD VALIDATION & SECURITY
# ============================================================================

# Custom User model with UUID primary key
AUTH_USER_MODEL = 'authentication.User'  # Use our custom User model
# Using UserProfile.id (UUID) for public API identification instead

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ('username', 'email', 'first_name', 'last_name'),
            'max_similarity': 0.7,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

PASSWORD_RESET_TIMEOUT = 1800  # 30 minutes

# ============================================================================
# INTERNATIONALIZATION
# ============================================================================

LANGUAGE_CODE = config('LANGUAGE_CODE', default='en-us')
TIME_ZONE = config('TIME_ZONE', default='UTC')
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ============================================================================
# STATIC FILES
# ============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# ============================================================================
# MEDIA FILES
# ============================================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ============================================================================
# DEFAULT FIELD TYPES
# ============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# DJANGO REST FRAMEWORK
# ============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        # Increased from 10/hour - allows normal usage while preventing brute force
        'login': '25/hour',
        'registration': '100/hour',  # Increased for testing (was 5/hour)
        'password_reset': '5/hour',
        'token_refresh': '60/hour',  # Allow reasonable token refresh frequency
        'email_verification_confirm': '10/hour',
        'email_verification_resend': '5/hour',
        'onboarding': '20/hour',  # Allow reasonable onboarding interactions
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    # Custom exception handler enabled
    'EXCEPTION_HANDLER': 'core.exceptions.problem_exception_handler',
}

# ============================================================================
# JWT CONFIGURATION
# ============================================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'ISSUER': 'vineyard_group_fellowship',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',

    # HttpOnly Cookie Configuration
    'AUTH_COOKIE': 'refresh_token',  # Cookie name
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_SAMESITE': 'Lax',
}

# ============================================================================
# REFRESH TOKEN COOKIE SETTINGS
# ============================================================================

# Cookie name and configuration for JWT refresh tokens
REFRESH_TOKEN_COOKIE_NAME = 'refresh_token'
REFRESH_TOKEN_COOKIE_MAX_AGE = 14 * 24 * 60 * \
    60  # 14 days (matches REFRESH_TOKEN_LIFETIME)
REFRESH_TOKEN_COOKIE_HTTPONLY = True
REFRESH_TOKEN_COOKIE_PATH = '/'
REFRESH_TOKEN_COOKIE_SAMESITE = 'Lax'

# Feature flag for httpOnly cookie refresh tokens (allows gradual rollout)
ENABLE_COOKIE_REFRESH_TOKEN = config(
    'ENABLE_COOKIE_REFRESH_TOKEN', default=True, cast=bool)

# ============================================================================
# SPECTACULAR (OpenAPI) SETTINGS
# ============================================================================

# ============================================================================
# DRF SPECTACULAR (OpenAPI Documentation)
# ============================================================================


SPECTACULAR_SETTINGS = {
    'TITLE': 'Vineyard Group Fellowship API',
    'DESCRIPTION': 'REST API for Vineyard Group Fellowship platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'TAGS': get_api_tags_metadata(),  # Use unified tag system
    'SERVERS': [
        {'url': 'http://localhost:8001/api/v1/',
            'description': 'Development server'},
        {'url': 'https://api.vineyardgroupfellowship.org/api/v1/',
            'description': 'Production server'},
    ],
    'EXTERNAL_DOCS': {
        'description': 'REST API for Vineyard Group Fellowship Documentation',
        'url': 'https://api.vineyardgroupfellowship.org/api/v1/',
    },
    # Schema generation compatibility settings
    'SCHEMA_COERCE_PATH_PK': True,
    'SCHEMA_COERCE_METHOD_NAMES': {
        'retrieve': 'get',
        'destroy': 'delete',
    },
}

# ============================================================================
# CSRF PROTECTION
# ============================================================================

CSRF_COOKIE_NAME = 'csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_COOKIE_HTTPONLY = False  # Must be False for SPA access
CSRF_COOKIE_AGE = 31449600  # 1 year
CSRF_USE_SESSIONS = False

# ============================================================================
# CORS CONFIGURATION
# ============================================================================

CORS_ALLOW_CREDENTIALS = True  # Allow cookies to be sent cross-origin
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']
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
]

# ============================================================================
# SESSION CONFIGURATION
# ============================================================================

SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'vineyard_group_fellowship',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# ============================================================================
# PROFILE PHOTO SETTINGS
# ============================================================================

# File upload settings (optimized for base64 storage)
# Must be integers for Django's multipart parser
FILE_UPLOAD_MAX_MEMORY_SIZE = int(1.5 * 1024 * 1024)  # 1.5MB raw file size (1572864 bytes)
DATA_UPLOAD_MAX_MEMORY_SIZE = int(1.5 * 1024 * 1024)  # 1.5MB (1572864 bytes)

# Profile photo specific settings for base64 storage
PROFILE_PHOTO_SETTINGS = {
    # Image processing
    'THUMBNAIL_SIZE': (150, 150),
    'PROFILE_SIZE': (400, 400),
    'MAX_ORIGINAL_SIZE': (600, 600),  # Smaller to keep base64 size reasonable
    'QUALITY': 85,  # High quality since we're compressing to smaller size
    'FORMAT': 'WEBP',  # Most efficient format for base64

    # Storage configuration
    'STORAGE_METHOD': 'base64',  # Always use base64 for consistency
    'MAX_FILE_SIZE': 1.5 * 1024 * 1024,  # 1.5MB original file
    'MAX_BASE64_SIZE': 2 * 1024 * 1024,  # ~2MB base64 (with encoding overhead)

    # Content validation
    'ALLOWED_TYPES': ['image/jpeg', 'image/png', 'image/webp'],
    'ALLOWED_EXTENSIONS': ['.jpg', '.jpeg', '.png', '.webp'],

    # Security and moderation
    'REQUIRE_MODERATION': True,
    'AUTO_APPROVE_SIZE_LIMIT': 500 * 1024,  # Auto-approve photos under 500KB
    'ENABLE_THUMBNAILS': True,  # Generate smaller thumbnails for list views

    # Performance optimizations
    'COMPRESS_QUALITY': 85,  # Compression quality for storage
    'THUMBNAIL_QUALITY': 75,  # Lower quality for thumbnails (smaller data)
}

# ============================================================================
# MONITORING CONFIGURATION
# ============================================================================

# Performance monitoring settings
MONITORING_SAMPLE_RATE = 1.0  # Monitor all requests in development
MONITORING_SLOW_REQUEST_THRESHOLD_MS = 1000  # Log requests slower than 1s
MONITORING_SLOW_QUERY_THRESHOLD_MS = 100     # Log queries slower than 100ms
MONITOR_ADMIN = False  # Skip monitoring admin interface
MONITOR_DB_QUERIES = True  # Enable database query monitoring
METRICS_RETENTION_DAYS = 30  # Keep metrics for 30 days

# Health check settings
HEALTH_CHECK_CACHE_TIMEOUT = 60  # Cache health check results for 1 minute

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'sensitive_data_filter': {
            '()': 'core.logging.structured.SensitiveDataFilter',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'structured': {
            '()': 'core.logging.structured.StructuredFormatter',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['sensitive_data_filter'],
        },
        'structured_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
            'filters': ['sensitive_data_filter'],
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'structured',
            'filters': ['sensitive_data_filter'],
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/security.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'structured',
            'filters': ['sensitive_data_filter'],
        },
        'performance_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/performance.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'structured',
            'filters': ['sensitive_data_filter'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'vineyard_group_fellowship': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'security': {
            'handlers': ['console', 'security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'performance': {
            'handlers': ['console', 'performance_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
