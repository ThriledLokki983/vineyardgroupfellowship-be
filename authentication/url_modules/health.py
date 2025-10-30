"""
Health check URL configuration.
"""

from django.urls import path

from ..view_modules.health import health_check_view

app_name = 'health'

urlpatterns = [
    # Health Check
    path('', health_check_view, name='check'),
]
