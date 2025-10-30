# Copilot Instructions - Vineyard Group Fellowship Backend

## Project Overview

This is a Django 5.2.7 backend application named "Vineyard Group Fellowship" that appears to be
in early development. It's a minimal Django setup with only core Django apps
installed.

## Project Structure

```
backend/
├── .venv/                       # Virtual environment (Python 3.13.7)
├── .vscode/                     # VS Code configuration
│   └── settings.json           # Python interpreter and formatting settings
├── Vineyard Group Fellowship/                  # Main Django project package
│   ├── settings.py             # Core Django settings
│   ├── urls.py                 # Root URL configuration
│   ├── wsgi.py/asgi.py         # WSGI/ASGI application
│   └── __init__.py
├── docker-compose.yml           # Local development infrastructure
├── makefile                     # Common Django commands
├── .env.example                # Environment variables template
├── .pre-commit-config.yaml     # Code quality hooks
├── manage.py                   # Django management script
└── db.sqlite3                  # SQLite database (temporary - migrating to PostgreSQL)
```

## Development Environment

### **Quick Start with Make Commands**

- **Use Makefile for all common tasks** (no need to remember long paths)
- **Available commands**:
  ```bash
  make setup      # Install dependencies from requirements.txt
  make run        # Start development server
  make migrate    # Apply database migrations
  make superuser  # Create Django superuser
  make check      # Run Django system checks
  make deploycheck # Run production deployment checks
  make test       # Run test suite
  make fmt        # Format code with Ruff and Black
  ```

### **Local Development Infrastructure**

- **Docker Compose**: PostgreSQL, Redis, and MailHog for development
- **Start infrastructure**: `docker-compose up -d`
- **Services**:
  - PostgreSQL: `localhost:5432` (user: Vineyard Group Fellowship, password: Vineyard Group Fellowship, db:
    Vineyard Group Fellowship)
  - Redis: `localhost:6379` (for caching and rate limiting)
  - MailHog: `localhost:8025` (email testing UI), SMTP on `localhost:1025`

### Virtual Environment Setup

- Uses a local `.venv/` virtual environment
- Python 3.13.7 with minimal dependencies: Django 5.2.7, asgiref, sqlparse
- **VS Code configured** with proper interpreter path in `.vscode/settings.json`
- **Always use the virtual environment prefix**:
  `/Users/gnimoh001/Desktop/Vineyard Group Fellowship/backend/.venv/bin/python`

### **CRITICAL: Dependency Management with requirements.txt**

- **ALWAYS use requirements.txt** for production dependencies
- **Use requirements-dev.txt** for development dependencies
- **NEVER use standalone pip install commands** - always update requirements files first
- **Simplified workflow** (no more complex requirements/ directory):

  ```bash
  # 1. Add desired dependency to requirements.txt or requirements-dev.txt
  echo "djangorestframework==3.15.2" >> requirements.txt

  # 2. Install from requirements files
  make local-setup        # Production dependencies
  make local-setup-dev    # Development dependencies (includes production)
  ```

### **Requirements Files Structure:**

```
requirements.txt         # Production dependencies (clean, single file)
requirements-dev.txt     # Development dependencies (includes requirements.txt)
pytest.ini              # Test configuration
```

### **Environment Configuration**

- **Template**: Use `.env.example` as template, copy to `.env` for local
  development
- **Never commit**: Real `.env` files (git-ignored)
- **Production**: Use host's secret store, not `.env` files
- **Settings Structure**: Split into `base.py`, `development.py`,
  `production.py`, `testing.py`

### Database Configuration

- **Database**: PostgreSQL (migrating from SQLite for development)
- **Current State**: SQLite `db.sqlite3` - temporary during development setup
- **Target Database**: PostgreSQL with proper connection settings
- **Migrations**: None applied yet (fresh Django installation)
- **Models**: Only Django built-in models (auth, admin, contenttypes, sessions)

## Key Development Patterns

### **Django Project Hygiene**

- **12-Factor Config**: Use environment variables; separate `settings/base.py`,
  `dev.py`, `prod.py`
- **Immutable Settings**: Never mutate settings at runtime; compute derived
  values once at import
- **Secrets Management**: No `.env` in production - use host's secret store
- **Example Structure**:
  ```
  Vineyard Group Fellowship/settings/
  ├── __init__.py
  ├── base.py      # Common settings
  ├── development.py
  ├── production.py
  └── testing.py
  ```

### **Architecture Patterns**

- **Fat Models, Thin Views**: Domain logic in model methods/services; views for
  orchestration only
- **Service Layer**: Use `core/services/*.py` for multi-model operations (e.g.,
  user registration, token rotation)
- **Bounded Contexts**: Small apps with clear responsibilities
  (`authentication`, `community`, `content`)
- **Signals Carefully**: Prefer services; use signals only for cross-cutting
  concerns (audit logs)

### **Data & ORM Best Practices**

- **Query Optimization**: Always consider `select_related()` and
  `prefetch_related()`; test for N+1 queries
- **Transactions**: Wrap multi-write flows in `transaction.atomic()`; use
  `select_for_update()` when needed
- **Idempotency**: Design writes so retries don't double-apply (use request IDs
  or unique constraints)
- **Validation Layers**: Use model `clean()`, DRF serializer `validate_*`, AND
  database constraints
- **Migration Discipline**: Create early, commit often; avoid mixing data +
  schema in risky migrations

**Example N+1 Prevention**:

```python
class PostViewSet(ModelViewSet):
    queryset = Post.objects.select_related("author").prefetch_related("tags")
```

### **API Design (DRF) Patterns**

- **ViewSets + Routers**: Use for CRUD; explicit `@action` for verbs (e.g.,
  `POST /users/{id}/deactivate/`)
- **Serializer Separation**: `ReadSerializer` vs `WriteSerializer` to avoid
  leaking internal fields
- **Pagination Everywhere**: Default page size; never return unbounded lists
- **Permissions First**: Object-level checks in `has_object_permission`; never
  trust client IDs
- **API Versioning**: Use `/api/v1/...` and freeze old behavior
- **Error Contract**: Return Problem+JSON (RFC 7807) consistently

### **Security & Auth Patterns**

- **Token Strategy**: httpOnly refresh cookies + short-lived access tokens in
  memory
- **CSRF & CORS**: Enable CSRF for cookie flows; pin exact origins in CORS
- **PII Handling**: Never log PII; normalize emails (lowercase); use Django
  validators
- **Security Headers**: HSTS, X-Frame-Options DENY, basic CSP; `SECURE_*` flags
  in production
- **Role Model**: Use groups/flags; don't bake roles into code branches

### **Background Tasks & Performance**

- **Task Queues**: Use Celery/RQ for email, notifications, heavy jobs; keep
  tasks idempotent and small
- **Caching Strategy**: Per-view, per-object, per-query caching; invalidate on
  write via signals/services
- **Redis Usage**: For rate limits (DRF throttling) and session management
- **Compression**: Enable GZip/Brotli; keep JSON responses compact

### **Observability & Testing**

- **Structured Logging**: JSON logs with correlation/request IDs; never expose
  stack traces to users
- **Monitoring**: Sentry for errors + metrics for login failures, token refresh
  errors, latency
- **Health Checks**: DB, cache, queue checks for container orchestrators
- **Testing Strategy**: pytest-django with factory_boy; Unit > Integration > E2E
  ratio
- **Security Tests**: CSRF, CORS, authorization gaps, rate limiting, N+1 guards

### **GDPR & Privacy (Critical for Vineyard Group Fellowship)**

- **Consent Tracking**: Store timestamps and privacy policy versions
- **Data Rights**: Implement export/erasure services for user data
- **Data Minimization**: Collect only what you use; implement retention policies
- **Audit Logging**: Track all security-sensitive operations

### **Code Quality Standards**

- **Type Hints**: Use everywhere with mypy + django-stubs
- **Code Formatting**: Ruff/Black/isort with pre-commit hooks
- **Small Functions**: Prefer clarity over cleverness; explicit returns

**Example Service Pattern**:

```python
# core/services/auth.py
from django.db import transaction
from django.db.utils import IntegrityError

def register_user(dto):
    with transaction.atomic():
        user, created = User.objects.get_or_create(
            email=dto.email.lower(),
            defaults={"username": dto.username, "is_active": False},
        )
        if not created:
            raise IntegrityError("Email already used")
        send_verification_email(user)  # queue async
        return user
```

**Problem+JSON Error Handling**:

```python
# core/exceptions.py
from rest_framework.views import exception_handler

def problem_exception_handler(exc, ctx):
    resp = exception_handler(exc, ctx)
    if resp is None:
        return resp
    resp.data = {
        "type": "about:blank",
        "title": resp.status_text,
        "status": resp.status_code,
        "detail": resp.data,
    }
    resp["Content-Type"] = "application/problem+json"
    return resp
```

### **Django Command Usage**

```bash
# Always use virtual environment for Django commands:
/Users/gnimoh001/Desktop/Vineyard Group Fellowship/backend/.venv/bin/python manage.py [command]

# Essential commands:
/Users/gnimoh001/Desktop/Vineyard Group Fellowship/backend/.venv/bin/python manage.py runserver
/Users/gnimoh001/Desktop/Vineyard Group Fellowship/backend/.venv/bin/python manage.py migrate
/Users/gnimoh001/Desktop/Vineyard Group Fellowship/backend/.venv/bin/python manage.py createsuperuser
/Users/gnimoh001/Desktop/Vineyard Group Fellowship/backend/.venv/bin/python manage.py startapp [app_name]
/Users/gnimoh001/Desktop/Vineyard Group Fellowship/backend/.venv/bin/python manage.py check --deploy
```

## Architecture Decisions

### **Core System Design (ADRs)**

#### **API Architecture**

- **API Style**: REST-first with DRF, SSE for realtime events, optional GraphQL
  later
- **Versioning**: URL-based (`/api/v1/...`) with frozen behavior per version
- **Authentication**: Email/username + password with JWT (access+refresh),
  optional OAuth
- **Authorization**: Role-based (user, moderator, admin) + object-level
  permissions via DRF

#### **Data & Storage**

- **Database**: PostgreSQL 15+ (RDS/managed preferred)
- **Storage**: S3-compatible object storage for future media (avatars only
  initially)
- **Search**: Postgres FTS v1, consider OpenSearch for scale
- **Caching**: Redis for rate limits, token blacklist, short-lived caches
- **Background Jobs**: Celery for async tasks

#### **Content & Safety**

- **Initial Scope**: Text-only posts/comments (no media uploads to avoid
  triggers)
- **Moderation**: Profanity/trigger filters, community rules checker,
  report/appeal pipeline
- **Privacy**: Privacy-by-default profiles, pseudonymous display names option
- **Crisis Support**: Always-on "Need help now?" banner with local helplines

#### **Security Baseline**

- **Edge**: Cloudflare WAF/CDN for DDoS protection and geo-rules
- **TLS**: HTTPS everywhere with HSTS headers
- **CSP**: Strict Content Security Policy with nonces
- **Secrets**: Environment variables + parameter store/sealed secrets
- **Dependencies**: Pinned versions with automated security scanning

#### **Data Privacy & Compliance (GDPR)**

- **Data Minimization**: Collect only necessary data, progressive profiling
- **Retention**: Posts 36mo (user-configurable), logs 12mo, reports 24mo
- **User Rights**: One-click data export, cascading anonymization for erasure
- **Age Gate**: 18+ with self-attestation (KYC hooks for regions requiring it)

#### **Core Data Models**

```python
# Primary entities to implement:
User, Profile, Journey (streaks/goals), Post, Comment,
Room (groups), DMThread, Report, Block, SessionLog (audit)
```

### **Current Implementation State**

- **Status**: Fresh Django project with core apps only
- **Database**: SQLite (temporary) → PostgreSQL migration planned
- **API**: No DRF yet → REST API implementation planned
- **Auth**: Basic Django auth → JWT with device management planned

### **Implementation Sequence**

1. **Dependencies & Environment Setup** (requirements.txt, PostgreSQL, Redis)
2. **Authentication System** (JWT, device management, security hardening)
3. **Core Models** (User, Profile, Post, Comment with privacy controls)
4. **Content Moderation** (filters, reporting, moderator queue)
5. **API Development** (DRF endpoints with versioning and pagination)
6. **Safety Features** (crisis support, privacy controls, audit logging)

### **Good Defaults to Apply**

```python
# DRF Settings (Production-Ready)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "120/min"},
    "EXCEPTION_HANDLER": "core.exceptions.problem_exception_handler",
}

# JWT Configuration (Secure)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
}

# OpenAPI Documentation
SPECTACULAR_SETTINGS = {
    "TITLE": "Vineyard Group Fellowship API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# Security Headers (Production)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"

# CSP Headers
CSP_DEFAULT_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:", "blob:")
CSP_FRAME_ANCESTORS = ("'none'",)
```

### When Adding New Features

1. **Dependencies**: ALWAYS update requirements.txt FIRST, then install from it
2. **New Apps**: Create with `startapp` and add to `INSTALLED_APPS` in
   `settings.py`
3. **URLs**: Include app URLs in `Vineyard Group Fellowship/urls.py` using `include()`
4. **Models**: Remember to run `makemigrations` and `migrate` after model
   changes
5. **Privacy**: Consider GDPR implications for any new data collection
6. **Security**: Add appropriate permissions and rate limiting for new endpoints

### **Dependency Management Workflow**

```bash
# CORRECT: Always update requirements.txt first
# 1. Edit requirements.txt to add new package
echo "djangorestframework==3.14.0" >> requirements.txt

# 2. Install from requirements.txt
/Users/gnimoh001/Desktop/Vineyard Group Fellowship/backend/.venv/bin/pip install -r requirements.txt

# WRONG: Never install packages directly
# pip install djangorestframework  # ❌ DON'T DO THIS
```

## Development Workflow

1. **Check for requirements.txt**: If missing, create it before any
   implementation
2. **Update dependencies**: Always edit requirements.txt first, then install
   from it
3. **Activate virtual environment**: Use full path for Python/pip commands
4. **Apply pending migrations**: Before running the server for the first time
5. **Create superuser**: For admin access: `python manage.py createsuperuser`
6. **Use Django admin**: At `/admin/` for quick data management during
   development

### **Requirements Files Management Rules**

- **Production File**: `requirements.txt` contains all production dependencies
- **Development File**: `requirements-dev.txt` includes production + development tools
- **Format**: Use specific versions (e.g., `Django==5.2.7`) for reproducibility
- **Installation Commands**:
  - `make local-setup` for production dependencies
  - `make local-setup-dev` for development dependencies
- **Updates**: Always commit requirements file changes with your code
- **Never**: Use `pip install package` directly - always update requirements files first

## Missing Components (Ready to Implement)

### **Infrastructure & Tooling**

- drf-spectacular + OpenAPI schema UI
- Celery + Redis scaffolding for background tasks
- Pre-commit hooks and CI pipelines (GitHub Actions)
- Problem+JSON exception handler wired into settings
- Request-ID middleware and structured JSON logging

### **Security & Monitoring**

- JWT with refresh token rotation and device management
- Rate limiting with Redis backend
- Sentry integration for error monitoring
- Security headers (CSP, HSTS, X-Frame-Options)
- CSRF protection for cookie-based auth

### **Development Experience**

- requirements.in + pip-tools workflow for dependency management
- PostgreSQL migration from SQLite
- Custom Django management commands
- Testing framework with pytest-django and factory_boy
- Code quality gates with coverage thresholds

### **Production Readiness**

- Settings split (base/dev/prod/testing)
- Health check endpoints (/healthz, /readiness)
- Docker containerization
- Backup and disaster recovery procedures
- GDPR compliance tools (data export/erasure)
