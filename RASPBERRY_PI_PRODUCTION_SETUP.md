# Raspberry Pi Production Setup Guide
# ====================================

## Quick Fix for Current Issue

The error `LookupError: No installed app with label 'admin'` means Django is loading the wrong settings file.

### Immediate Steps on Raspberry Pi:

```bash
# 1. Navigate to backend directory
cd ~/apps/vineyardgroupfellowship/backend

# 2. Check if .env.docker exists
ls -la .env.docker

# If .env.docker doesn't exist, create it:
nano .env.docker
```

### Minimum Required .env.docker Content:

```bash
# Copy these lines into .env.docker and update passwords:

# CRITICAL: Generate a random secret key
# Run on Pi: python3 -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY=<PASTE_GENERATED_SECRET_KEY_HERE>

# Django Settings
DJANGO_SETTINGS_MODULE=vineyard_group_fellowship.settings.production
DJANGO_ENVIRONMENT=production
DEBUG=False

# Database (update passwords!)
DB_NAME=vineyard_group_fellowship_prod
DB_USER=vineyard_group_fellowship
DB_PASSWORD=your_secure_db_password_here
DB_HOST=pgbouncer
DB_PORT=5432

# Redis (update password!)
REDIS_PASSWORD=your_secure_redis_password_here
REDIS_URL=redis://:your_secure_redis_password_here@redis:6379/1

# Server
PORT=8002
SERVER_PORT=8002

# Security (add your Pi's IP)
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,web,192.168.1.XXX
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Email (for testing, use console)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=Vineyard Group Fellowship <noreply@vineyardgroupfellowship.org>

# Celery
CELERY_BROKER_URL=redis://:your_secure_redis_password_here@redis:6379/0
CELERY_RESULT_BACKEND=redis://:your_secure_redis_password_here@redis:6379/0

# Features
USE_MAILHOG=false
ENABLE_DEBUG_TOOLBAR=false
ENABLE_SILK_PROFILING=false
ENABLE_PERFORMANCE_MONITORING=true

# Logging
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
MONITORING_SAMPLE_RATE=0.1
```

### Save and Restart:

```bash
# Save the file (Ctrl+O, Enter, Ctrl+X in nano)

# Pull latest changes
git pull origin main

# Rebuild with updated docker-compose.production.yml
docker compose -f docker-compose.production.yml down
docker compose -f docker-compose.production.yml build --no-cache web
docker compose -f docker-compose.production.yml up -d

# Check logs
docker compose -f docker-compose.production.yml logs -f web
```

---

## Full Production Setup (Complete Guide)

### 1. Generate Secure Credentials

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(50))"

# Generate strong passwords (or use a password manager)
python3 -c "import secrets; print('DB_PASSWORD:', secrets.token_urlsafe(32))"
python3 -c "import secrets; print('REDIS_PASSWORD:', secrets.token_urlsafe(32))"
```

### 2. Create Production Environment File

```bash
cd ~/apps/vineyardgroupfellowship/backend

# Copy the example file
cp .env.production.example .env.docker

# Edit with your credentials
nano .env.docker
```

Update all values marked with `<CHANGE_THIS>` in the file.

### 3. Update PostgreSQL & PgBouncer Passwords

Since you're using Docker Compose, the database passwords in `docker-compose.production.yml` should match your `.env.docker`:

```yaml
# In docker-compose.production.yml, these use the same env vars:
POSTGRES_PASSWORD: ${DB_PASSWORD:-vineyard_group_fellowship_dev_password}
DATABASE_URL: "postgres://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}"
```

### 4. Deploy

```bash
# Stop old containers
docker compose down

# Build and start with production config
docker compose -f docker-compose.production.yml up -d --build

# Watch logs
docker compose -f docker-compose.production.yml logs -f web
```

### 5. Verify Deployment

```bash
# Check venv exists
docker compose -f docker-compose.production.yml exec web ls -la /app/venv

# Check settings loaded correctly
docker compose -f docker-compose.production.yml exec web /app/venv/bin/python manage.py check

# Check database connection
docker compose -f docker-compose.production.yml exec web /app/venv/bin/python manage.py showmigrations

# Create superuser
docker compose -f docker-compose.production.yml exec web /app/venv/bin/python manage.py createsuperuser
```

### 6. Test the Application

```bash
# Get your Pi's IP
hostname -I

# Test from browser:
# http://YOUR_PI_IP:8002/api/health/
# http://YOUR_PI_IP:8002/admin/
```

---

## Common Issues & Solutions

### Issue 1: "No installed app with label 'admin'"
**Cause**: Missing or incorrect `DJANGO_SETTINGS_MODULE` in .env.docker  
**Fix**: Ensure `.env.docker` contains:
```bash
DJANGO_SETTINGS_MODULE=vineyard_group_fellowship.settings.production
```

### Issue 2: "SECRET_KEY required"
**Cause**: Missing SECRET_KEY in .env.docker  
**Fix**: Generate and add SECRET_KEY (see step 1 above)

### Issue 3: Database connection timeout
**Cause**: Incorrect DB_HOST or credentials  
**Fix**: Ensure DB_HOST=pgbouncer and passwords match

### Issue 4: "/app/venv not found"
**Cause**: Using wrong compose file or volume inheritance  
**Fix**: Use `docker-compose.production.yml` ALONE (not with docker-compose.yml)

---

## Security Checklist

- ✅ Generated strong SECRET_KEY
- ✅ Changed DB_PASSWORD from default
- ✅ Changed REDIS_PASSWORD from default
- ✅ Set DEBUG=False
- ✅ Updated ALLOWED_HOSTS with your domain/IP
- ✅ .env.docker is NOT in Git (check .gitignore)
- ✅ File permissions: `chmod 600 .env.docker`

---

## Ansible Integration

Update your Ansible playbook to use production compose file:

```yaml
# In your backend.yml task:
- name: Start Docker Compose services
  command: docker compose -f docker-compose.production.yml up -d --build
  args:
    chdir: /home/{{ ansible_user }}/apps/vineyardgroupfellowship/backend
```

---

## Monitoring

```bash
# View logs
docker compose -f docker-compose.production.yml logs -f

# View only errors
docker compose -f docker-compose.production.yml logs -f web | grep ERROR

# Check container health
docker compose -f docker-compose.production.yml ps

# Check resource usage
docker stats
```

---

## Backup

```bash
# Backup database
docker compose -f docker-compose.production.yml exec postgres pg_dump -U vineyard_group_fellowship vineyard_group_fellowship_prod > backup_$(date +%Y%m%d).sql

# Backup media files
tar -czf media_backup_$(date +%Y%m%d).tar.gz media/

# Backup environment file (encrypted!)
gpg -c .env.docker  # Creates .env.docker.gpg
```
