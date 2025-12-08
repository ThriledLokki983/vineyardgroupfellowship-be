#!/bin/bash
# Vineyard Group Fellowship Backend Startup Script
# =================================================
#
# Startup script for Docker deployment (Pi + Railway)
# Handles database migrations, static files, and graceful startup

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Prefer venv Python, fall back to system python
if [ -x "/app/venv/bin/python" ]; then
    PYTHON=/app/venv/bin/python
    echo -e "${GREEN}✅ Using virtualenv Python at /app/venv/bin/python${NC}"
    export VIRTUAL_ENV=/app/venv
    export PATH="/app/venv/bin:$PATH"
else
    PYTHON=python
    echo -e "${YELLOW}⚠️  /app/venv/bin/python not found, using 'python' from PATH${NC}"
    echo "which python -> $(which python || echo 'not found')"
fi

echo -e "${BLUE}🚀 Starting Vineyard Group Fellowship Backend...${NC}"
echo "================================================"

# If the venv directory exists, still export VIRTUAL_ENV / PATH
if [ -d "/app/venv" ]; then
    export VIRTUAL_ENV=/app/venv
    export PATH="/app/venv/bin:$PATH"
fi

# Default port (for Docker / Pi)
export PORT=${PORT:-8002}

# -------------------------------------------------------------------
# Database environment normalisation
# - Prefer DB_* variables (Docker / Pi)
# - Only fall back to PG* (Railway style) if DB_* are not set
# -------------------------------------------------------------------
if [ -n "$DB_HOST" ]; then
    # Map DB_* → PG* so Django / libs that read PG* also work
    export PGHOST="$DB_HOST"
    export PGPORT="${DB_PORT:-5432}"
    export PGDATABASE="${DB_NAME:-}"
    export PGUSER="${DB_USER:-}"
    export PGPASSWORD="${DB_PASSWORD:-}"  # nosec - env var reference
fi

echo -e "${BLUE}🔧 Validating environment configuration...${NC}"

# Required variables
required_vars=(
    "SECRET_KEY"
    "DJANGO_ENVIRONMENT"
)

# For local/docker/Pi: require DB_* if DATABASE_URL is not used
if [ -z "$DATABASE_URL" ] && [ -z "$DB_HOST" ]; then
    required_vars+=(
        "DB_NAME"
        "DB_USER"
        "DB_PASSWORD"  # nosec - env var name
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

# -------------------------------------------------------------------
# Show configuration (without sensitive data)
# -------------------------------------------------------------------
echo -e "${BLUE}📊 Configuration:${NC}"
echo "   Environment: ${DJANGO_ENVIRONMENT}"
echo "   Port: ${PORT}"

if [ -n "$DATABASE_URL" ]; then
    db_info="DATABASE_URL configured"
elif [ -n "$DB_HOST" ]; then
    db_info="${DB_HOST}:${DB_PORT:-5432}/${DB_NAME}"
elif [ -n "$PGHOST" ]; then
    # Fallback: Railway-like PG* configuration
    db_info="PG: ${PGHOST}:${PGPORT:-5432}/${PGDATABASE}"
else
    db_info="(no database configured)"
fi
echo "   Database: ${db_info}"

# -------------------------------------------------------------------
# Wait for database to be ready (a bit more generous on the Pi)
# -------------------------------------------------------------------
echo -e "${BLUE}🗄️  Waiting for database connection...${NC}"
timeout=20
counter=0

while ! $PYTHON manage.py check --database default --fail-level ERROR >/dev/null 2>&1; do
    if [ $counter -ge $timeout ]; then
        echo -e "${YELLOW}⚠️  Database check timeout after ${timeout}s - continuing anyway${NC}"
        break
    fi

    echo -e "${YELLOW}⏳ Waiting for database... (${counter}s/${timeout}s)${NC}"
    sleep 1
    counter=$((counter + 1))
done

if [ $counter -lt $timeout ]; then
    echo -e "${GREEN}✅ Database connection established${NC}"
fi

# -------------------------------------------------------------------
# Run database migrations
# -------------------------------------------------------------------
echo -e "${BLUE}🔄 Running database migrations...${NC}"
if $PYTHON manage.py migrate --noinput; then
    echo -e "${GREEN}✅ Database migrations completed${NC}"
else
    echo -e "${RED}❌ Database migration failed${NC}"
    exit 1
fi

# Post-migration setup
echo -e "${BLUE}⚙️  Running post-migration setup...${NC}"
if [ -x "scripts/post-migration.sh" ]; then
    ./scripts/post-migration.sh
else
    echo -e "${YELLOW}⚠️  Post-migration script not found or not executable${NC}"
fi

# Collect static files
echo -e "${BLUE}📦 Collecting static files...${NC}"
if $PYTHON manage.py collectstatic --noinput --clear; then
    echo -e "${GREEN}✅ Static files collected${NC}"
else
    echo -e "${YELLOW}⚠️  Static file collection failed (continuing anyway)${NC}"
fi

# Cache table (if using DB cache)
echo -e "${BLUE}🗃️  Setting up cache tables...${NC}"
$PYTHON manage.py createcachetable 2>/dev/null || echo -e "${YELLOW}⚠️  Cache table setup skipped (may already exist)${NC}"

# Health checks
echo -e "${BLUE}🔍 Running system health checks...${NC}"
if $PYTHON manage.py check --deploy --fail-level WARNING; then
    echo -e "${GREEN}✅ System health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Health check warnings detected (continuing anyway)${NC}"
fi

# Log startup information
echo -e "${BLUE}📝 Startup information:${NC}"
echo "   Django version: $($PYTHON -c 'import django; print(django.get_version())')"
echo "   Python version: $($PYTHON --version)"
echo "   Working directory: $(pwd)"
echo "   User: $(whoami)"

# -------------------------------------------------------------------
# Graceful shutdown handler
# -------------------------------------------------------------------
cleanup() {
    echo -e "${YELLOW}🛑 Received shutdown signal, stopping gracefully...${NC}"
    kill $server_pid 2>/dev/null || true
    wait $server_pid 2>/dev/null || true
    echo -e "${GREEN}✅ Shutdown complete${NC}"
    exit 0
}

trap cleanup SIGTERM SIGINT

# -------------------------------------------------------------------
# Start the Django server
# -------------------------------------------------------------------
echo -e "${GREEN}🎉 Starting Django server on port ${PORT}...${NC}"
echo "================================================"

if [ "$DJANGO_ENVIRONMENT" = "production" ]; then
    echo -e "${BLUE}🏭 Starting Gunicorn (production mode) as django user...${NC}"

    if [ "$(id -u)" = "0" ]; then
        echo -e "${YELLOW}Running as root - will drop to django user${NC}"
        mkdir -p /app/media/group_photos /app/media/profile_photos /app/media/message_attachments
        chown -R django:django /app/media
        chmod -R 755 /app/media
        echo -e "${GREEN}✅ Media directory permissions set${NC}"

        exec runuser -u django -- gunicorn vineyard_group_fellowship.wsgi:application \
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
    fi
else
    echo -e "${BLUE}🔧 Starting Django development server...${NC}"
    exec $PYTHON manage.py runserver 0.0.0.0:$PORT &
fi

server_pid=$!
wait $server_pid