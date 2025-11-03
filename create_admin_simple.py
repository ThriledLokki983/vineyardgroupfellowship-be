#!/usr/bin/env python3
"""
Simplest admin creation script - no dependencies needed.
Usage: 
  railway run python create_admin_simple.py
  
Or with inline credentials (not recommended):
  railway run python create_admin_simple.py admin@example.com MySecurePassword123
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vineyard_group_fellowship.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# Get email and password
if len(sys.argv) >= 3:
    # From command line arguments
    email = sys.argv[1]
    password = sys.argv[2]
else:
    # From environment variables
    email = os.environ.get('ADMIN_EMAIL')
    password = os.environ.get('ADMIN_PASSWORD')

if not email or not password:
    print("❌ Error: Email and password required")
    print("\nOption 1 - Set environment variables in Railway:")
    print("  ADMIN_EMAIL=admin@example.com")
    print("  ADMIN_PASSWORD=your-password")
    print("\nOption 2 - Pass as arguments:")
    print("  railway run python create_admin_simple.py admin@example.com MyPassword123")
    sys.exit(1)

# Create or get admin user
try:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': 'admin',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
            'email_verified': True,
            'email_verified_at': timezone.now(),
        }
    )
    
    if created:
        user.set_password(password)
        user.save()
        print(f"✅ Admin user created: {email}")
    else:
        # Update password for existing user
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save()
        print(f"✅ Admin user already exists, password updated: {email}")
    
    print(f"\n🎉 Success!")
    print(f"📧 Email: {email}")
    print(f"🔐 Password: [as provided]")
    print(f"🌐 Login at: /admin/")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
