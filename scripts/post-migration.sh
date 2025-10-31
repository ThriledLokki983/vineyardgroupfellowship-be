#!/bin/bash
set -e

echo "🚀 Running post-migration setup..."

# Create admin user if environment variables are set
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "📧 Admin credentials found, creating admin user..."
    python manage.py create_admin_user
else
    echo "⚠️  ADMIN_EMAIL and ADMIN_PASSWORD not set, skipping admin user creation"
fi

# Run any other post-migration tasks here
echo "✅ Post-migration setup completed"