"""
Testing settings for Vineyard Group Fellowship project.

This file contains settings specific to running tests.
Optimized for speed and isolation.
"""

from .base import *

# ============================================================================
# DEBUG & TESTING
# ============================================================================

DEBUG = False
TESTING = True

# ============================================================================
# DATABASE - Testing
# ============================================================================

# Use in-memory SQLite for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# ============================================================================
# EMAIL BACKEND - Testing
# ============================================================================

# Use in-memory email backend for testing (no actual emails sent)
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'test@Vineyard Group Fellowship.test'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# For testing SendGrid integration specifically, set SENDGRID_API_KEY
# This will use the Web API backend instead
SENDGRID_API_KEY = config('SENDGRID_API_KEY', default='')
if SENDGRID_API_KEY and config('TEST_WITH_SENDGRID', default=False, cast=bool):
    EMAIL_BACKEND = 'core.email_backends.SendGridWebAPIBackend'
    DEFAULT_FROM_EMAIL = config(
        'DEFAULT_FROM_EMAIL', default='info@vineyardgroupfellowship.org')

# ============================================================================
# PASSWORD HASHING - Testing
# ============================================================================

# Use faster password hasher for tests (speeds up user creation)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# ============================================================================
# CACHING - Testing
# ============================================================================

# Use local memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# ============================================================================
# LOGGING - Testing
# ============================================================================

# Minimize logging during tests (set to DEBUG to troubleshoot)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',  # Change to DEBUG to see detailed logs
    },
}

# ============================================================================
# THROTTLING - Testing
# ============================================================================

# Disable throttling in tests (or it will slow down test suite)
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '10000/hour',
    'user': '10000/hour',
    'authentication': '10000/hour',
    'registration': '10000/hour',
    'token_refresh': '10000/hour',
    'password_reset': '10000/hour',
    'password_reset_confirm': '10000/hour',
    'email_verification': '10000/hour',
    'profile_update': '10000/hour',
    'device_management': '10000/hour',
    'content_moderation': '10000/hour',
    'post_creation': '10000/hour',
    'comment_creation': '10000/hour',
}

# ============================================================================
# SECURITY - Testing
# ============================================================================

# Disable some security features for easier testing
SECRET_KEY = 'test-secret-key-not-for-production'  # nosec - test environment only
ALLOWED_HOSTS = ['*']
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# JWT Cookie settings for testing
REFRESH_TOKEN_COOKIE_SECURE = False  # Allow HTTP in testing
