"""
Django settings module selector.

This module automatically loads the appropriate settings based on the environment.
"""

import os
from decouple import config

# Check if DJANGO_SETTINGS_MODULE is explicitly set (e.g., for build)
django_settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')

if 'build' in django_settings_module:
    # Use build settings for Docker build-time operations
    from .build import *
    print(f"🎛️  Environment: build (via DJANGO_SETTINGS_MODULE)")
else:
    # Use environment-based selection for normal operations
    ENVIRONMENT = config('DJANGO_ENVIRONMENT', default='development')

    if ENVIRONMENT == 'production':
        from .production import *
    elif ENVIRONMENT == 'testing':
        from .testing import *  # We'll create this if needed
    else:
        from .development import *

    print(f"🎛️  Environment: {ENVIRONMENT}")
