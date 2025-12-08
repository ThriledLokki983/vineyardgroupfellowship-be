#!/bin/bash
# Database Credentials Fix Script for Raspberry Pi
# =================================================
# This script fixes database credential mismatches between PostgreSQL and Django

set -e

echo "🔧 Fixing Database Credentials..."
echo "=================================="

# Check if .env.docker exists
if [ ! -f .env.docker ]; then
    echo "❌ Error: .env.docker file not found!"
    echo "Please create .env.docker first (see RASPBERRY_PI_PRODUCTION_SETUP.md)"
    exit 1
fi

# Load variables from .env.docker
source .env.docker

echo "📋 Current .env.docker settings:"
echo "   DB_NAME: ${DB_NAME}"
echo "   DB_USER: ${DB_USER}"
echo ""

# Stop running containers
echo "🛑 Stopping containers..."
docker compose -f docker-compose.production.yml down

# Remove old volumes (CAUTION: This will delete existing data!)
read -p "⚠️  Do you want to delete existing database volumes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Removing old database volumes..."
    docker volume rm vineyard-group-fellowship_postgres_data 2>/dev/null || echo "Volume already removed or doesn't exist"
    echo "✅ Old volumes removed"
else
    echo "⏭️  Keeping existing volumes"
fi

# Pull latest code
echo "📥 Pulling latest code from Git..."
git pull origin main

# Start services
echo "🚀 Starting services with fresh configuration..."
docker compose -f docker-compose.production.yml up -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10

# Check database connection
echo "🔍 Verifying database setup..."
docker compose -f docker-compose.production.yml exec postgres psql -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT version();" 2>/dev/null && {
    echo "✅ Database connection successful!"
} || {
    echo "⚠️  Database connection failed. Checking details..."
    
    # Show pgbouncer config
    echo ""
    echo "📊 PgBouncer DATABASE_URL:"
    docker compose -f docker-compose.production.yml exec pgbouncer env | grep DATABASE_URL
    
    echo ""
    echo "📊 PostgreSQL logs (last 20 lines):"
    docker compose -f docker-compose.production.yml logs --tail=20 postgres
}

# Show web logs
echo ""
echo "📊 Web container logs (last 30 lines):"
docker compose -f docker-compose.production.yml logs --tail=30 web

echo ""
echo "✅ Script complete!"
echo ""
echo "Next steps:"
echo "1. Check web logs: docker compose -f docker-compose.production.yml logs -f web"
echo "2. Run migrations: docker compose -f docker-compose.production.yml exec web /app/venv/bin/python manage.py migrate"
echo "3. Create superuser: docker compose -f docker-compose.production.yml exec web /app/venv/bin/python manage.py createsuperuser"
