#!/bin/bash
# Vineyard Group Fellowship Backend Startup Script
# =================================================
#
# Production startup script for Railway deployment
# Handles database migrations, static files, and graceful startup

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Vineyard Group Fellowship Backend...${NC}"
echo "================================================"

# Set default port if not provided by Railway
export PORT=${PORT:-8001}

# Validate required environment variables
echo -e "${BLUE}🔧 Validating environment configuration...${NC}"

# Check for required environment variables
required_vars=(
    "SECRET_KEY"
    "DJANGO_ENVIRONMENT"
)

# Database variables (Railway supports DATABASE_URL or individual PGHOST/PGDATABASE vars)
if [ -z "$DATABASE_URL" ] && [ -z "$PGHOST" ]; then
    # Only require individual DB vars if neither DATABASE_URL nor Railway vars are available
    required_vars+=(
        "DB_NAME"
        "DB_USER"
        "DB_PASSWORD"
        "DB_HOST"
    )
fi

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for var in "${missing_vars[@]}"; do
        echo -e "${RED}   - $var${NC}"
    done
    echo -e "${YELLOW}💡 Please check your environment configuration${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment validation passed${NC}"

# Show configuration (without sensitive data)
echo -e "${BLUE}📊 Configuration:${NC}"
echo "   Environment: ${DJANGO_ENVIRONMENT}"
echo "   Port: ${PORT}"
echo "   Database: $([ -n "$DATABASE_URL" ] && echo "DATABASE_URL configured" || ([ -n "$PGHOST" ] && echo "Railway PG: $PGHOST:${PGPORT:-5432}/$PGDATABASE" || echo "$DB_HOST:${DB_PORT:-5432}/$DB_NAME"))"

# Wait for database to be ready
echo -e "${BLUE}🗄️  Waiting for database connection...${NC}"
timeout=30
counter=0

while ! python manage.py check --database default --fail-level ERROR >/dev/null 2>&1; do
    if [ $counter -ge $timeout ]; then
        echo -e "${RED}❌ Database connection timeout after ${timeout}s${NC}"
        echo -e "${YELLOW}💡 Check database configuration and network connectivity${NC}"
        exit 1
    fi

    echo -e "${YELLOW}⏳ Waiting for database... (${counter}s/${timeout}s)${NC}"
    sleep 1
    counter=$((counter + 1))
done

echo -e "${GREEN}✅ Database connection established${NC}"

# Create media directories with proper permissions
echo -e "${BLUE}📁 Setting up media directories...${NC}"
mkdir -p media/group_photos media/profile_photos media/message_attachments
chmod -R 755 media/
echo -e "${GREEN}✅ Media directories created${NC}"

# Run database migrations
echo -e "${BLUE}🔄 Running database migrations...${NC}"
if python manage.py migrate --noinput; then
    echo -e "${GREEN}✅ Database migrations completed${NC}"
else
    echo -e "${RED}❌ Database migration failed${NC}"
    exit 1
fi

# Run post-migration setup
echo -e "${BLUE}⚙️  Running post-migration setup...${NC}"
if [ -x "scripts/post-migration.sh" ]; then
    ./scripts/post-migration.sh
else
    echo -e "${YELLOW}⚠️  Post-migration script not found or not executable${NC}"
fi

# Collect static files (in case they weren't collected during build)
echo -e "${BLUE}📦 Collecting static files...${NC}"
if python manage.py collectstatic --noinput --clear; then
    echo -e "${GREEN}✅ Static files collected${NC}"
else
    echo -e "${YELLOW}⚠️  Static file collection failed (continuing anyway)${NC}"
fi

# Create cache table if using database cache
echo -e "${BLUE}🗃️  Setting up cache tables...${NC}"
python manage.py createcachetable 2>/dev/null || echo -e "${YELLOW}⚠️  Cache table setup skipped (may already exist)${NC}"

# System health check
echo -e "${BLUE}🔍 Running system health checks...${NC}"
if python manage.py check --deploy --fail-level WARNING; then
    echo -e "${GREEN}✅ System health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Health check warnings detected (continuing anyway)${NC}"
fi

# Log startup information
echo -e "${BLUE}📝 Startup information:${NC}"
echo "   Django version: $(python -c 'import django; print(django.get_version())')"
echo "   Python version: $(python --version)"
echo "   Working directory: $(pwd)"
echo "   User: $(whoami)"

# Graceful shutdown handler
cleanup() {
    echo -e "${YELLOW}🛑 Received shutdown signal, stopping gracefully...${NC}"
    kill $server_pid 2>/dev/null || true
    wait $server_pid 2>/dev/null || true
    echo -e "${GREEN}✅ Shutdown complete${NC}"
    exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGTERM SIGINT

# Start the Django server
echo -e "${GREEN}🎉 Starting Django server on port ${PORT}...${NC}"
echo "================================================"

# Use gunicorn for production, runserver for development
if [ "$DJANGO_ENVIRONMENT" = "production" ]; then
    # Production: Use Gunicorn with optimized settings
    echo -e "${BLUE}🏭 Starting Gunicorn (production mode)...${NC}"
    exec gunicorn vineyard_group_fellowship.wsgi:application \
        --bind 0.0.0.0:$PORT \
        --workers 2 \
        --threads 4 \
        --worker-class gthread \
        --worker-connections 1000 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --timeout 30 \
        --keep-alive 2 \
        --preload \
        --log-level info \
        --access-logfile - \
        --error-logfile - \
        --capture-output &
else
    # Development/Staging: Use Django's development server
    echo -e "${BLUE}🔧 Starting Django development server...${NC}"
    exec python manage.py runserver 0.0.0.0:$PORT &
fi

server_pid=$!

# Wait for the server process
wait $server_pid