"""
Build-time settings for Vineyard Group Fellowship project.

These settings are used during Docker build phase when collecting static files.
No database connection is required during build.
"""

from .base import *

# ============================================================================
# BUILD-TIME CONFIGURATION
# ============================================================================

DEBUG = False

# Build-time dummy database (not used during collectstatic)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Static files configuration for build
STATIC_URL = '/static/'
STATIC_ROOT = '/app/staticfiles'

# Disable security features that require database during build
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Minimal allowed hosts for build
ALLOWED_HOSTS = ['*']

# Disable middleware that might require database
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

# Minimal installed apps for collectstatic - include core Django apps that are dependencies
INSTALLED_APPS = [
    'django.contrib.contenttypes',  # Required by auth and other apps
    'django.contrib.auth',          # Required by custom user models
    'django.contrib.staticfiles',   # Required for collectstatic
    'rest_framework',               # For DRF static files
    'corsheaders',                  # For CORS static files
    
    # Local apps (needed for static files and model definitions)
    'core',
    'authentication',
    'profiles',
    'privacy',
    'monitoring',
]

# Email backend (dummy for build)
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

# Disable logging during build
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Cache (dummy for build)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Disable Sentry during build
SENTRY_DSN = None

print("🔨 Build-time settings loaded for static file collection")