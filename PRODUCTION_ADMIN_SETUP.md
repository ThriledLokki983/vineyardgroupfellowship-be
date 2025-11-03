# Production Admin User Setup Guide

*Last Updated: November 3, 2025*

This guide shows you how to create a Django admin superuser in your Railway production environment.

---

## 🎯 **Choose Your Method**

| Method | Difficulty | Best For | Time |
|--------|------------|----------|------|
| **Method 1: Railway CLI** | ⭐ Easy | Quick setup | 2 min |
| **Method 2: Django Management Command** | ⭐⭐ Medium | Automated setup | 3 min |
| **Method 3: Railway Web Shell** | ⭐ Easy | No local setup needed | 2 min |

---

## 🚀 **METHOD 1: Railway CLI (Recommended)**

This is the **fastest and easiest** method.

### **Prerequisites**
- Railway CLI installed
- Logged into Railway

### **Step-by-Step**

#### 1. Install Railway CLI (if not installed)
```bash
# macOS/Linux
curl -fsSL https://railway.app/install.sh | sh

# Or with Homebrew
brew install railway
```

#### 2. Login to Railway
```bash
railway login
```

#### 3. Link to Your Project
```bash
cd /Users/gnimoh001/Desktop/vineyard-group-fellowship/backend
railway link
```
Select your project: `vineyardgroupfellowship-be`

#### 4. Create the Admin User
```bash
railway run python manage.py create_verified_superuser \
  --email admin@vineyardgroupfellowship.com \
  --username admin
```

You'll be prompted to enter a password (twice for confirmation).

#### 5. Verify It Worked
```bash
# Check that the user was created
railway run python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
user = User.objects.get(email='admin@vineyardgroupfellowship.com');
print(f'✅ User created: {user.email}');
print(f'✅ Is superuser: {user.is_superuser}');
print(f'✅ Email verified: {user.email_verified}');
"
```

#### 6. Login to Django Admin
Visit: `https://your-railway-domain.railway.app/admin/`

**Credentials**:
- Email: `admin@vineyardgroupfellowship.com`
- Password: (what you entered above)

---

## 🛠️ **METHOD 2: Environment Variables + Script**

Use the existing `create_production_admin.py` script.

### **Step-by-Step**

#### 1. Set Environment Variables in Railway

Go to Railway Dashboard → Your Project → Variables

Add these variables:
```bash
ADMIN_EMAIL=admin@vineyardgroupfellowship.com
ADMIN_PASSWORD=YourSecurePassword123!
DATABASE_PUBLIC_URL=postgresql://user:pass@host:port/database
```

**Get DATABASE_PUBLIC_URL**:
- Railway Dashboard → PostgreSQL → Connect → Public Network URL

#### 2. Run the Script via Railway CLI
```bash
cd /Users/gnimoh001/Desktop/vineyard-group-fellowship/backend
railway run python create_production_admin.py
```

**Expected Output**:
```
🚀 Creating admin user for production deployment...
📧 Admin email: admin@vineyardgroupfellowship.com
✅ Admin user created successfully!
   Email: admin@vineyardgroupfellowship.com
   User ID: 1
   Is Staff: True
   Is Superuser: True

🎉 Admin user setup completed successfully!
🌐 You can now access the Django admin at: https://your-domain/admin/
```

#### 3. Login
Visit: `https://your-railway-domain.railway.app/admin/`

---

## 🌐 **METHOD 3: Railway Web Shell**

No CLI needed - do everything in the browser.

### **Step-by-Step**

#### 1. Open Railway Shell
1. Go to Railway Dashboard
2. Select your Django service
3. Click on **"Shell"** tab or **"Deploy" → "Shell"**

#### 2. Run Django Command
In the web shell, type:
```bash
python manage.py create_verified_superuser --email admin@vineyardgroupfellowship.com --username admin
```

#### 3. Enter Password When Prompted
```
Password: [enter secure password]
Password (again): [enter same password]
```

#### 4. Verify Success
You should see:
```
Successfully created verified superuser: admin@vineyardgroupfellowship.com
```

#### 5. Login
Visit: `https://your-railway-domain.railway.app/admin/`

---

## 🔧 **METHOD 4: One-Time Deployment Script**

Add admin creation to your deployment process.

### **Option A: Add to `start.sh`**

Edit `/Users/gnimoh001/Desktop/vineyard-group-fellowship/backend/start.sh`:

```bash
#!/bin/bash

# Database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create admin user if ADMIN_EMAIL and ADMIN_PASSWORD are set
if [ ! -z "$ADMIN_EMAIL" ] && [ ! -z "$ADMIN_PASSWORD" ]; then
    echo "Creating admin user if it doesn't exist..."
    python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vineyard_group_fellowship.settings')
django.setup()
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()
email = os.environ.get('ADMIN_EMAIL')
password = os.environ.get('ADMIN_PASSWORD')

if email and password and not User.objects.filter(email=email).exists():
    user = User.objects.create_superuser(
        email=email,
        username='admin',
        password=password,
        first_name='Admin',
        last_name='User'
    )
    user.email_verified = True
    user.email_verified_at = timezone.now()
    user.save()
    print(f'✅ Admin user created: {email}')
else:
    print(f'ℹ️  Admin user already exists or credentials not provided')
"
fi

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn vineyard_group_fellowship.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

Then set these in Railway:
```bash
ADMIN_EMAIL=admin@vineyardgroupfellowship.com
ADMIN_PASSWORD=YourSecurePassword123!
```

**Next deployment** will automatically create the admin user!

### **Option B: Separate Django Management Command**

Create a reusable command in `authentication/management/commands/ensure_admin.py`:

```python
"""
Management command to ensure admin user exists.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Ensure admin user exists (idempotent)'

    def handle(self, *args, **options):
        email = os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('ADMIN_PASSWORD')

        if not email or not password:
            self.stdout.write(
                self.style.WARNING('ADMIN_EMAIL and ADMIN_PASSWORD not set')
            )
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.SUCCESS(f'Admin user already exists: {email}')
            )
            return

        user = User.objects.create_superuser(
            email=email,
            username='admin',
            password=password,
            first_name='Admin',
            last_name='User'
        )
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save()

        self.stdout.write(
            self.style.SUCCESS(f'Created admin user: {email}')
        )
```

Then run:
```bash
railway run python manage.py ensure_admin
```

---

## 🔐 **Security Best Practices**

### **1. Use Strong Passwords**
```bash
# Generate a secure password
openssl rand -base64 32
```

### **2. Don't Commit Admin Credentials**
❌ Never add to `.env` and commit
✅ Set in Railway dashboard only

### **3. Use Environment-Specific Emails**
- **Production**: `admin@vineyardgroupfellowship.com`
- **Staging**: `admin-staging@vineyardgroupfellowship.com`
- **Development**: `admin@example.com`

### **4. Enable 2FA (Future Enhancement)**
Consider adding Django 2FA for production admin:
```bash
pip install django-otp qrcode
```

---

## 🧪 **Testing Your Admin Access**

### **1. Check Admin Can Login**
```bash
curl -X POST https://your-domain/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@vineyardgroupfellowship.com",
    "password": "YourPassword"
  }'
```

Expected: JWT tokens returned

### **2. Verify Admin Permissions**
```bash
railway run python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
admin = User.objects.get(email='admin@vineyardgroupfellowship.com');
print(f'Is staff: {admin.is_staff}');
print(f'Is superuser: {admin.is_superuser}');
print(f'Email verified: {admin.email_verified}');
print(f'Has usable password: {admin.has_usable_password()}');
"
```

All should be `True`.

### **3. Access Django Admin
Visit: `https://your-railway-domain.railway.app/admin/`

You should see:
- ✅ Login page
- ✅ Successful login with credentials
- ✅ Full admin dashboard access

---

## ❌ **Troubleshooting**

### **Issue: "User already exists"**

**Solution 1: Reset Password**
```bash
railway run python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
user = User.objects.get(email='admin@vineyardgroupfellowship.com');
user.set_password('NewPassword123!');
user.save();
print('✅ Password reset successfully');
"
```

**Solution 2: Delete and Recreate**
```bash
railway run python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
User.objects.filter(email='admin@vineyardgroupfellowship.com').delete();
print('✅ User deleted');
"

# Then create again
railway run python manage.py create_verified_superuser --email admin@vineyardgroupfellowship.com --username admin
```

### **Issue: "Email not verified"**

**Solution:**
```bash
railway run python manage.py shell -c "
from django.contrib.auth import get_user_model;
from django.utils import timezone;
User = get_user_model();
user = User.objects.get(email='admin@vineyardgroupfellowship.com');
user.email_verified = True;
user.email_verified_at = timezone.now();
user.save();
print('✅ Email verified');
"
```

### **Issue: "Permission denied"**

**Solution:**
```bash
railway run python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
user = User.objects.get(email='admin@vineyardgroupfellowship.com');
user.is_staff = True;
user.is_superuser = True;
user.is_active = True;
user.save();
print('✅ Permissions updated');
"
```

### **Issue: Can't access Railway CLI**

Use **Method 3** (Railway Web Shell) instead.

---

## 📋 **Quick Reference Commands**

```bash
# Create admin (interactive)
railway run python manage.py create_verified_superuser --email admin@example.com --username admin

# Create admin (from script)
railway run python create_production_admin.py

# Check if admin exists
railway run python manage.py shell -c "from django.contrib.auth import get_user_model; print(get_user_model().objects.filter(email='admin@example.com').exists())"

# Reset admin password
railway run python manage.py shell -c "from django.contrib.auth import get_user_model; u=get_user_model().objects.get(email='admin@example.com'); u.set_password('NewPass123'); u.save()"

# List all superusers
railway run python manage.py shell -c "from django.contrib.auth import get_user_model; [print(f'{u.email} - {u.is_superuser}') for u in get_user_model().objects.filter(is_superuser=True)]"
```

---

## ✅ **Recommended Setup Flow**

For your first production admin:

1. **Install Railway CLI** (one-time)
   ```bash
   brew install railway
   railway login
   ```

2. **Link Project** (one-time)
   ```bash
   cd /Users/gnimoh001/Desktop/vineyard-group-fellowship/backend
   railway link
   ```

3. **Create Admin** (quick!)
   ```bash
   railway run python manage.py create_verified_superuser \
     --email admin@vineyardgroupfellowship.com \
     --username admin
   ```

4. **Login**
   - Visit: `https://your-domain/admin/`
   - Email: `admin@vineyardgroupfellowship.com`
   - Password: (what you entered)

**Done!** ✅

---

## 🎯 **Next Steps**

After creating your admin:

1. ✅ Login to `/admin/` and verify access
2. ✅ Create additional staff users if needed
3. ✅ Configure Django admin settings
4. ✅ Set up admin notifications (optional)
5. ✅ Enable 2FA (recommended for production)

---

**Questions?** The Railway CLI method (Method 1) is the simplest and most reliable! 🚀
