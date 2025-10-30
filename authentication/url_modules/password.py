"""
Password management URL configuration.
"""

from django.urls import path

from ..view_modules.password import (
    change_password_view,
    password_reset_request_view,
    password_reset_confirm_view
)

app_name = 'password'

urlpatterns = [
    # Password Change
    path('change/', change_password_view, name='change'),

    # Password Reset Flow
    path('reset/', password_reset_request_view, name='reset_request'),
    path('reset/confirm/', password_reset_confirm_view, name='reset_confirm'),
]
