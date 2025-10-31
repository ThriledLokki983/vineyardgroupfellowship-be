# Core App

## Purpose

Shared utilities, middleware, security components, and core functionality used
across all apps in the Vineyard Group Fellowship platform. Provides common infrastructure and
cross-cutting concerns.

## Responsibilities

- **Security Middleware**: CSRF protection, security headers, PII scrubbing
- **Authentication Utilities**: JWT handling, CSRF token management
- **System Configuration**: Dynamic system settings manageable via admin
- **Common Utilities**: Shared functions and helpers
- **Error Handling**: Custom exception handlers and error responses
- **Rate Limiting**: Custom throttling classes
- **Monitoring**: Security incident logging and monitoring

## Key Components

### Security Infrastructure

✅ **Security Headers Middleware**:

- Content Security Policy (CSP) with violation reporting
- HSTS, X-Frame-Options, X-Content-Type-Options
- Environment-specific header configuration
- API documentation CSP exceptions

✅ **CSRF Protection**:

- SPA-compatible CSRF token handling
- Cookie-based CSRF tokens with secure flags
- API endpoint CSRF validation

✅ **PII Protection**:

- Automatic scrubbing of sensitive data in logs
- Request/response sanitization
- Security incident logging without PII

### System Configuration

```python
class SystemSetting(models.Model):
    """Dynamic system settings manageable via Django admin."""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    setting_type = models.CharField(max_length=20)  # boolean, integer, string, json
    category = models.CharField(max_length=50)      # throttling, security, etc.
```

### Authentication Components

- **JWT Cookie Handling**: Secure JWT token management via httpOnly cookies
- **Token Validation**: Custom JWT authentication backend
- **Session Management**: Integration with Django sessions

## File Structure

```
core/
├── models.py              # SystemSetting model
├── auth.py               # JWT authentication utilities
├── csrf.py               # CSRF protection utilities
├── exceptions.py         # Custom exception handlers
├── throttling.py         # Custom rate limiting classes
├── utils.py              # General utilities
├── views.py              # Core API endpoints
├── middleware/           # Custom middleware
│   ├── csrf.py          # Enhanced CSRF middleware
│   └── timezone.py      # Timezone detection middleware
├── security/            # Security components
│   ├── headers.py       # Security headers middleware
│   └── monitoring.py    # Security monitoring utilities
├── urls/               # URL modules
│   └── csrf.py         # CSRF-related URLs
└── utils_package/      # Utility packages
    └── timezone.py     # Timezone utilities
```

## API Endpoints

### CSRF Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/csrf/` | Get CSRF token for SPA | No |

### Security Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/security/csp-report/` | CSP violation reporting | No |
| POST | `/api/v1/security/incident/` | Report security incident | Yes |
| GET | `/api/v1/security/status/` | Get security status | No |
| GET | `/api/v1/security/analysis/` | Get security analysis | Admin |
| POST | `/api/v1/security/sessions/terminate-all/` | Terminate all sessions (security) | Yes |
| POST | `/api/v1/security/sessions/terminate-suspicious/` | Terminate suspicious sessions | Yes |

### Health & Monitoring
See [Monitoring App README](../monitoring/README.md) for health check endpoints.

---## Security Features

### Content Security Policy (CSP)

- Strict CSP with nonce-based script execution
- Automatic violation reporting
- Development vs production CSP differences
- API documentation exceptions

### Rate Limiting

```python
class AuthenticationThrottle(UserRateThrottle):
    """Custom throttling for authentication endpoints."""
    scope = 'auth'

class RegistrationThrottle(AnonRateThrottle):
    """Strict throttling for user registration."""
    scope = 'registration'
```

### Security Monitoring

- CSP violation logging and analysis
- Security incident detection
- Suspicious activity monitoring
- Audit trail for security events

## Current Issues

### Positive Aspects

✅ **Well-Structured Security**: Comprehensive security middleware ✅ **Proper
Separation**: Security concerns properly isolated ✅ **Configuration
Management**: Dynamic settings via admin ✅ **Monitoring**: Good security
incident logging

### Potential Issues

🟡 **Kitchen Sink Risk**: Could become catch-all for miscellaneous utilities 🟡
**Complexity**: Security middleware is quite complex for an MVP 🟢 **Generally
Well-Implemented**: This app follows good practices

## Dependencies

- Django security features
- Django REST Framework
- Redis (for rate limiting)
- Logging infrastructure

## Security Middleware Configuration

### Production Settings

```python
# Security headers applied in production
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

### CSP Configuration

```python
# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'nonce-{nonce}'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "blob:")
```

## System Settings Categories

### Throttling & Rate Limiting

- Login attempt limits
- Registration rate limits
- API endpoint throttling
- Account lockout thresholds

### Security Features

- CSP violation reporting
- Security header enforcement
- PII scrubbing configuration
- Audit logging levels

### Development Tools

- Debug mode settings
- Development-only features
- Testing configurations

## Performance Considerations

- **Caching**: System settings are cached for performance
- **Middleware Order**: Security middleware is properly ordered
- **Async Processing**: CSP violation processing is async
- **Memory Usage**: Efficient security monitoring

## Testing Requirements

- Test all security middleware components
- Validate CSP policy enforcement
- Test CSRF protection mechanisms
- Verify rate limiting functionality
- Security header validation

## Usage Examples

### System Settings

```python
from core.models import SystemSetting

# Get a setting value
max_login_attempts = SystemSetting.get_setting('max_login_attempts', default=5)

# Set a setting via admin or programmatically
SystemSetting.objects.create(
    key='maintenance_mode',
    value='false',
    setting_type='boolean',
    category='security'
)
```

### Security Monitoring

```python
from core.security.monitoring import log_security_incident

# Log a security incident
log_security_incident(
    user=request.user,
    incident_type='suspicious_login',
    details={'ip': request.META.get('REMOTE_ADDR')},
    risk_level='medium'
)
```

## Integration Points

### With Authentication App

- JWT token validation
- Security monitoring integration
- Rate limiting for auth endpoints

### With All Apps

- Security headers for all responses
- CSRF protection for state-changing operations
- PII scrubbing for all logging

## Monitoring & Alerting

- CSP violation monitoring
- Security incident alerting
- Rate limiting threshold monitoring
- System setting change auditing

## Production Considerations

- **Security Headers**: Strict security policy enforcement
- **Performance**: Efficient middleware with minimal overhead
- **Monitoring**: Comprehensive security event logging
- **Configuration**: Environment-specific security settings

## Best Practices Followed

- ✅ Separation of concerns (security isolated)
- ✅ Configuration management (dynamic settings)
- ✅ Proper middleware ordering
- ✅ Comprehensive security coverage
- ✅ Performance optimization

This app provides the security foundation that all other apps depend on and is
generally well-implemented compared to other apps in the project.
