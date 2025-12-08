# # Vineyard Group Fellowship Backend Dockerfile
# # Multi-stage build for production deployment

# # ============================================================================
# # Build Stage - Install dependencies and compile static files
# # ============================================================================
# FROM python:3.13-slim AS builder

# # Set build arguments
# ARG BUILDPLATFORM
# ARG TARGETPLATFORM

# # Install system dependencies for building (including GDAL)
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     libpq-dev \
#     gcc \
#     gdal-bin \
#     libgdal-dev \
#     && rm -rf /var/lib/apt/lists/*

# # Set work directory
# WORKDIR /app

# # Create virtual environment
# RUN python -m venv /app/venv
# ENV PATH="/app/venv/bin:$PATH"

# # Install Python dependencies
# COPY requirements.txt ./
# RUN pip install --no-cache-dir --upgrade pip \
#     && pip install --no-cache-dir -r requirements.txt

# # ============================================================================
# # Production Stage - Minimal runtime environment
# # ============================================================================
# FROM python:3.13-slim AS production

# # Set environment variables
# # ENV PYTHONDONTWRITEBYTECODE=1 \
# #     PYTHONUNBUFFERED=1 \
# #     DJANGO_ENVIRONMENT=production \
# #     PATH="/app/venv/bin:$PATH"

# WORKDIR /app
# COPY --from=builder /app/venv /app/venv
# COPY . .

# # Create non-root user for security
# RUN groupadd -r django && useradd -r -g django django

# # Install runtime dependencies only (including GDAL 36 for Debian Trixie)
# # Note: libgdal36 is the correct package for GDAL 3.6.x in Debian Trixie
# RUN apt-get update && apt-get install -y \
#     libpq5 \
#     libmagic1 \
#     curl \
#     gdal-bin \
#     libgdal36 \
#     && rm -rf /var/lib/apt/lists/* \
#     && apt-get clean

# # Set work directory
# WORKDIR /app

# # Copy virtual environment from builder stage
# COPY --from=builder /app/venv /app/venv

# # Copy application code
# COPY . .

# # Make startup and post-migration scripts executable
# RUN chmod +x start.sh scripts/post-migration.sh

# # Create required directories with proper ownership
# RUN mkdir -p /app/staticfiles /app/logs /app/media/group_photos /app/media/profile_photos /app/media/message_attachments \
#     && chown -R django:django /app

# # Note: NOT switching to django user here - will be handled in start.sh
# # This allows the startup script to create directories in volume mounts as root
# # Then drop to django user for running the application

# # Collect static files with environment variables for build
# # nosec - These are dummy values only used for build-time static collection
# ENV SECRET_KEY=build-time-secret-key-not-for-production \
#     DJANGO_SETTINGS_MODULE=vineyard_group_fellowship.settings.build \
#     DB_NAME=dummy \
#     DB_USER=dummy \
#     DB_PASSWORD=dummy \
#     DB_HOST=dummy \
#     DB_PORT=5432 \
#     PGDATABASE=dummy \
#     PGUSER=dummy \
#     PGPASSWORD=dummy \
#     PGHOST=dummy \
#     PGPORT=5432 \
#     EMAIL_HOST_PASSWORD=dummy \
#     DEFAULT_FROM_EMAIL=build@vineyardgroupfellowship.org \
#     VIRTUAL_ENV=/app/venv \
#     PATH="$VIRTUAL_ENV/bin:$PATH"
# RUN python manage.py collectstatic --noinput

# # Health check - Railway will override this with its own health check
# # HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
# #     CMD curl -f http://localhost:8001/readiness/ || exit 1

# # Expose port (default 8001, but Railway will override with PORT env var)
# EXPOSE 8001

# # Start command - Use startup script for better debugging
# CMD ["./start.sh"]

# Vineyard Group Fellowship Backend Dockerfile
# Multi-stage build for production deployment

# ============================================================================
# Build Stage - Install dependencies and create virtualenv
# ============================================================================
FROM python:3.13-slim AS builder

# Optional build args (kept in case you use them in CI)
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install system dependencies for building (including GDAL)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Create virtual environment
RUN python -m venv /app/venv

# Use the venv Python for all subsequent build-stage python commands
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python dependencies into the venv
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Production Stage - Minimal runtime environment
# ============================================================================
FROM python:3.13-slim AS production

# Base runtime env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_ENVIRONMENT=production \
    VIRTUAL_ENV=/app/venv \
    PATH="$VIRTUAL_ENV/bin:$PATH"

# Workdir for the app
WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /app/venv /app/venv

# Copy application code
COPY . .

# Create non-root user for security
RUN groupadd -r django && useradd -r -g django django

# Install runtime dependencies only (including GDAL 3.6 for Debian Trixie)
RUN apt-get update && apt-get install -y \
    libpq5 \
    libmagic1 \
    curl \
    gdal-bin \
    libgdal36 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create required directories with proper ownership
RUN mkdir -p \
        /app/staticfiles \
        /app/logs \
        /app/media/group_photos \
        /app/media/profile_photos \
        /app/media/message_attachments \
    && chown -R django:django /app

# --------------------------------------------------------------------------
# Build-time settings for collectstatic
# (dummy values, NOT used in real production runtime)
# --------------------------------------------------------------------------
ENV \
    SECRET_KEY=build-time-secret-key-not-for-production \
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
    DEFAULT_FROM_EMAIL=build@vineyardgroupfellowship.org

# IMPORTANT:
# Use the venv python explicitly so Django is found
RUN /app/venv/bin/python manage.py collectstatic --noinput

# Health check - Railway will override this with its own health check if needed
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:8001/readiness/ || exit 1

# Expose port (start.sh will respect $PORT; default is 8001)
EXPOSE 8001

# Start command - uses start.sh to handle migrations & gunicorn
CMD ["./start.sh"]