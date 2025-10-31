#!/usr/bin/env python3
"""
Script to create admin user for production deployment.
This connects directly to the Railway PostgreSQL database using the public URL.
"""
import os
import sys
import django
from decouple import config

# Database configuration for direct connection
DATABASE_PUBLIC_URL = config('DATABASE_PUBLIC_URL')
ADMIN_EMAIL = config('ADMIN_EMAIL')
ADMIN_PASSWORD = config('ADMIN_PASSWORD')

# Override the DATABASE_URL to use the public URL for this script
os.environ['DATABASE_URL'] = DATABASE_PUBLIC_URL

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vineyard_group_fellowship.settings.production')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Django and configure
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_admin_user():
    """Create an admin user if one doesn't exist."""
    
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("❌ ADMIN_EMAIL and ADMIN_PASSWORD environment variables must be set")
        return False
    
    try:
        # Check if admin user already exists
        if User.objects.filter(email=ADMIN_EMAIL).exists():
            print(f"✅ Admin user with email {ADMIN_EMAIL} already exists")
            return True
        
        # Create the admin user
        admin_user = User.objects.create_user(
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
        
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {ADMIN_EMAIL}")
        print(f"   User ID: {admin_user.id}")
        print(f"   Is Staff: {admin_user.is_staff}")
        print(f"   Is Superuser: {admin_user.is_superuser}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create admin user: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Creating admin user for production deployment...")
    print(f"📧 Admin email: {ADMIN_EMAIL}")
    
    success = create_admin_user()
    
    if success:
        print("\n🎉 Admin user setup completed successfully!")
        print(f"🌐 You can now access the Django admin at: https://api.vineyardgroupfellowship.org/admin/")
        print(f"🔐 Login with: {ADMIN_EMAIL}")
    else:
        print("\n❌ Admin user setup failed!")
        sys.exit(1)