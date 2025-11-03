#!/usr/bin/env python3
"""
Script to create admin user for production deployment.
Run with: railway run python create_production_admin.py
"""
import os
import sys
import django

# Set up Django - Railway automatically provides DATABASE_URL
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vineyard_group_fellowship.settings')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Django and configure
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# Get credentials from environment variables
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')


def create_admin_user():
    """Create an admin user if one doesn't exist."""

    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("❌ ERROR: ADMIN_EMAIL and ADMIN_PASSWORD environment variables must be set")
        print("\nSet them in Railway Dashboard:")
        print("  1. Go to your project → Variables")
        print("  2. Add ADMIN_EMAIL = your-email@example.com")
        print("  3. Add ADMIN_PASSWORD = your-secure-password")
        return False

    try:
        # Check if admin user already exists
        if User.objects.filter(email=ADMIN_EMAIL).exists():
            user = User.objects.get(email=ADMIN_EMAIL)
            print(f"✅ Admin user with email {ADMIN_EMAIL} already exists")
            print(f"   User ID: {user.id}")
            print(f"   Is Staff: {user.is_staff}")
            print(f"   Is Superuser: {user.is_superuser}")
            print(f"   Email Verified: {user.email_verified}")
            return True

        # Create the admin user
        admin_user = User.objects.create_superuser(
            email=ADMIN_EMAIL,
            username='admin',  # Default username
            password=ADMIN_PASSWORD,
            first_name='Admin',
            last_name='User'
        )
        
        # Mark email as verified
        admin_user.email_verified = True
        admin_user.email_verified_at = timezone.now()
        admin_user.save()

        print(f"✅ Admin user created successfully!")
        print(f"   Email: {ADMIN_EMAIL}")
        print(f"   Username: admin")
        print(f"   User ID: {admin_user.id}")
        print(f"   Is Staff: {admin_user.is_staff}")
        print(f"   Is Superuser: {admin_user.is_superuser}")
        print(f"   Email Verified: {admin_user.email_verified}")
        return True

    except Exception as e:
        print(f"❌ Failed to create admin user: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Creating admin user for production deployment...")
    
    if ADMIN_EMAIL:
        print(f"📧 Admin email: {ADMIN_EMAIL}")
    else:
        print("⚠️  No ADMIN_EMAIL set in environment variables")

    success = create_admin_user()

    if success:
        print("\n🎉 Admin user setup completed successfully!")
        print(f"🌐 You can now access the Django admin at:")
        print(f"   https://your-railway-domain.railway.app/admin/")
        print(f"🔐 Login with:")
        print(f"   Email: {ADMIN_EMAIL}")
        print(f"   Password: [the password you set in ADMIN_PASSWORD]")
    else:
        print("\n❌ Admin user setup failed!")
        sys.exit(1)
