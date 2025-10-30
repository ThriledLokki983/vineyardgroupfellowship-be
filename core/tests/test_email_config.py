#!/usr/bin/env python
"""
Test script to verify email configuration is working with new domain-authenticated sender.
"""
from core.email_backends import SendGridWebAPIBackend
from django.conf import settings
from django.core.mail import send_mail
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'Vineyard Group Fellowship.settings.development')
sys.path.append('/app')
django.setup()


def test_email_config():
    """Test email configuration and send a test email."""

    print("🔧 Current Email Configuration:")
    print(f"   Email Backend: {settings.EMAIL_BACKEND}")
    print(f"   Default From Email: {settings.DEFAULT_FROM_EMAIL}")

    if hasattr(settings, 'SERVER_EMAIL'):
        print(f"   Server Email: {settings.SERVER_EMAIL}")
    if hasattr(settings, 'SUPPORT_EMAIL'):
        print(f"   Support Email: {settings.SUPPORT_EMAIL}")
    if hasattr(settings, 'NOREPLY_EMAIL'):
        print(f"   No Reply Email: {settings.NOREPLY_EMAIL}")

    print(
        f"   SendGrid API Key: {'Set' if getattr(settings, 'SENDGRID_API_KEY', None) else 'Not Set'}")
    print()

    # Test email sending
    try:
        print("📧 Sending test email...")

        result = send_mail(
            subject='🧪 Vineyard Group Fellowship Email Configuration Test',
            message='This is a test email to verify the new domain-authenticated sender configuration.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            # Will be caught by MailHog locally
            recipient_list=['test@example.com'],
            fail_silently=False,
        )

        print(f"✅ Email sent successfully! Result: {result}")
        print("📬 Check MailHog at http://localhost:8025 to see the email")

        return True

    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False


if __name__ == '__main__':
    test_email_config()
