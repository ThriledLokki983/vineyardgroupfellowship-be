"""
 CSRF URL configuration for Vineyard Group Fellowship API.

Defines URL patterns for CSRF token management endpoints.
"""

from django.urls import path
from core.views.csrf import (
    csrf_token_view,
    csrf_rotate_view,
    csrf_status_view,
    csrf_validate_view,
)

app_name = 'csrf'

urlpatterns = [
    # CSRF token endpoints
    path('token/', csrf_token_view, name='token'),
    path('rotate/', csrf_rotate_view, name='rotate'),
    path('status/', csrf_status_view, name='status'),
    path('validate/', csrf_validate_view, name='validate'),
]
