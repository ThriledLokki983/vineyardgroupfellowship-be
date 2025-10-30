"""
Django settings module selector.

This module automatically loads the appropriate settings based on the environment.
"""

import os
from decouple import config

# Determine which settings to use
ENVIRONMENT = config('DJANGO_ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'testing':
    from .testing import *  # We'll create this if needed
else:
    from .development import *

print(f"🎛️  Environment: {ENVIRONMENT}")
