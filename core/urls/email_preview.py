"""
Email Template Preview URLs
Allows staff members to preview email templates in the browser before deployment
"""
from django.urls import path
from core.email_preview_views import (
    email_preview_list,
    email_verification_preview,
    password_reset_preview,
)

app_name = 'email-preview'

urlpatterns = [
    path('', email_preview_list, name='list'),
    path('verification/', email_verification_preview, name='verification'),
    path('password-reset/', password_reset_preview, name='password-reset'),
]
