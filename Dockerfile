# Vineyard Group Fellowship Backend Dockerfile
# Multi-stage build for production deployment

# ============================================================================
# Build Stage - Install dependencies and compile static files
# ============================================================================
FROM python:3.13-slim AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Create virtual environment
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Production Stage - Minimal runtime environment
# ============================================================================
FROM python:3.13-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_ENVIRONMENT=production \
    PATH="/app/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r django && useradd -r -g django django

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set work directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/venv /app/venv

# Copy application code
COPY . .

# Make startup script executable
RUN chmod +x start.sh

# Create required directories
RUN mkdir -p /app/staticfiles /app/logs \
    && chown -R django:django /app

# Switch to non-root user
USER django

# Collect static files with environment variables for build
# nosec - These are dummy values only used for build-time static collection
ENV SECRET_KEY=build-time-secret-key-not-for-production \
    DJANGO_SETTINGS_MODULE=vineyard_group_fellowship.settings.build \
    DB_NAME=dummy \
    DB_USER=dummy \
    DB_PASSWORD=dummy \
    DB_HOST=dummy \
    DB_PORT=5432 \
    PGDATABASE=dummy \
    PGUSER=dummy \
    PGPASSWORD=dummy \
    PGHOST=dummy \
    PGPORT=5432 \
    EMAIL_HOST_PASSWORD=dummy \
    DEFAULT_FROM_EMAIL=build@vineyard-group-fellowship.org
RUN python manage.py collectstatic --noinput

# Health check - Railway will override this with its own health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:8001/readiness/ || exit 1

# Expose port (default 8001, but Railway will override with PORT env var)
EXPOSE 8001

# Start command - Use startup script for better debugging
CMD ["./start.sh"]