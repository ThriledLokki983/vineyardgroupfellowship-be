"""
Email template preview views for development.
These views allow you to preview email templates in the browser.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@staff_member_required
def email_preview_list(request):
    """List all available email templates for preview."""
    templates = [
        {
            'name': 'Email Verification',
            'url': 'email-preview:verification',
            'description': 'Email sent to users when they sign up to verify their email address.'
        },
        {
            'name': 'Password Reset',
            'url': 'email-preview:password-reset',
            'description': 'Email sent to users when they request to reset their password.'
        },
    ]

    return render(request, 'email_preview_list.html', {
        'templates': templates,
        'page_title': 'Email Template Previews'
    })


@staff_member_required
def email_verification_preview(request):
    """Preview the email verification template."""

    # Sample data
    context = {
        'user': request.user,
        'site_name': 'Vineyard Group Fellowship',
        'verification_url': 'https://api.vineyardgroupfellowship.org/api/v1/auth/email/verify/sample-token-here/1234567890:sample-hash/',
        'token_expiry_hours': 24,
        'support_email': 'support@vineyardgroupfellowship.org',
        'current_year': timezone.now().year,
    }

    return render(request, 'authentication/email_verification_email.html', context)


@staff_member_required
def password_reset_preview(request):
    """Preview the password reset email template."""

    # Sample data
    context = {
        'user': request.user,
        'site_name': 'Vineyard Group Fellowship',
        'reset_url': 'https://app.vineyardgroupfellowship.org/reset-password/sample-token-here/1234567890:sample-hash/',
        'token_expiry_hours': 1,
        'support_email': 'support@vineyardgroupfellowship.org',
        'current_year': timezone.now().year,
    }

    return render(request, 'authentication/password_reset_email.html', context)
