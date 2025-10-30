"""
Unified API Documentation Tags for the Vineyard Group Fellowship platform.

This module provides a single source of truth for all API documentation tags
to prevent duplicate sections in the OpenAPI/Swagger documentation.
"""

from drf_spectacular.utils import extend_schema, OpenApiExample


class APITags:
    """
    Unified API tags for consistent documentation organization.

    Usage:
        @extend_schema(tags=[APITags.AUTHENTICATION])
        def my_view(request):
            pass
    """

    # === CORE FUNCTIONALITY ===
    AUTHENTICATION = "Authentication"  # Login, logout, registration, tokens
    SESSION_MANAGEMENT = "Session Management"  # User sessions, device management
    USER_PROFILES = "User Profiles"  # Profile management, photos, settings

    # === COMMUNICATION ===
    EMAIL_VERIFICATION = "Email Verification"  # Email verification flows
    PASSWORD_MANAGEMENT = "Password Management"  # Password reset, change

    # === SYSTEM & MONITORING ===
    SYSTEM_HEALTH = "System Health"  # Health checks, status endpoints
    MONITORING = "Monitoring"  # Performance metrics, analytics
    SECURITY = "Security"  # Security incidents, CSP reports

    # === PRIVACY & COMPLIANCE ===
    PRIVACY = "Privacy"  # GDPR, data exports, consent management
    ADMINISTRATIVE = "Administrative"  # Admin-only endpoints


# Tag descriptions for OpenAPI documentation
TAG_DESCRIPTIONS = {
    APITags.AUTHENTICATION: "User authentication, registration, and token management",
    APITags.SESSION_MANAGEMENT: "User session tracking and device management",
    APITags.USER_PROFILES: "User profile management, photos, and personal settings",
    # APITags.EMAIL_VERIFICATION: "Email verification and communication workflows",
    # APITags.PASSWORD_MANAGEMENT: "Password reset, change, and security operations",
    APITags.SYSTEM_HEALTH: "Health checks and system status for load balancers",
    APITags.MONITORING: "Performance metrics and application monitoring",
    APITags.SECURITY: "Security incident reporting and policy violation tracking",
    # APITags.PRIVACY: "GDPR compliance, data exports, and privacy controls",
    # APITags.ADMINISTRATIVE: "Administrative endpoints for system management"
}


def get_api_tags_metadata():
    """
    Returns OpenAPI tags metadata for Spectacular configuration.

    Add this to your DRF_SPECTACULAR_SETTINGS:
    TAGS = get_api_tags_metadata()
    """
    return [
        {"name": tag, "description": description}
        for tag, description in TAG_DESCRIPTIONS.items()
    ]


# Common examples used across multiple endpoints
COMMON_EXAMPLES = {
    'validation_error': OpenApiExample(
        name="Validation Error",
        description="Request validation failed",
        value={
            "error": "Validation failed",
            "details": {
                "email": ["This field is required."],
                "password": ["Password is too weak."]
            }
        }
    ),
    'authentication_error': OpenApiExample(
        name="Authentication Error",
        description="Authentication credentials invalid or missing",
        value={
            "error": "Authentication failed",
            "message": "Invalid credentials provided"
        }
    ),
    'permission_error': OpenApiExample(
        name="Permission Error",
        description="User lacks required permissions",
        value={
            "error": "Permission denied",
            "message": "You do not have permission to perform this action"
        }
    ),
    'rate_limit_error': OpenApiExample(
        name="Rate Limit Error",
        description="Request rate limit exceeded",
        value={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": 60
        }
    ),
    'server_error': OpenApiExample(
        name="Server Error",
        description="Internal server error occurred",
        value={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )
}


# Common schema decorators for consistent API documentation
def authentication_schema(**kwargs):
    """Schema decorator for authentication endpoints."""
    defaults = {
        'tags': [APITags.AUTHENTICATION],
        'examples': [
            COMMON_EXAMPLES['validation_error'],
            COMMON_EXAMPLES['rate_limit_error']
        ]
    }
    defaults.update(kwargs)
    return extend_schema(**defaults)


def session_schema(**kwargs):
    """Schema decorator for session management endpoints."""
    defaults = {
        'tags': [APITags.SESSION_MANAGEMENT],
        'examples': [
            COMMON_EXAMPLES['authentication_error'],
            COMMON_EXAMPLES['rate_limit_error']
        ]
    }
    defaults.update(kwargs)
    return extend_schema(**defaults)


def profile_schema(**kwargs):
    """Schema decorator for user profile endpoints."""
    defaults = {
        'tags': [APITags.USER_PROFILES],
        'examples': [
            COMMON_EXAMPLES['authentication_error'],
            COMMON_EXAMPLES['validation_error']
        ]
    }
    defaults.update(kwargs)
    return extend_schema(**defaults)


def monitoring_schema(**kwargs):
    """Schema decorator for monitoring endpoints."""
    defaults = {
        'tags': [APITags.MONITORING],
        'examples': [
            COMMON_EXAMPLES['server_error']
        ]
    }
    defaults.update(kwargs)
    return extend_schema(**defaults)


def security_schema(**kwargs):
    """Schema decorator for security endpoints."""
    defaults = {
        'tags': [APITags.SECURITY],
        'examples': [
            COMMON_EXAMPLES['validation_error'],
            COMMON_EXAMPLES['server_error']
        ]
    }
    defaults.update(kwargs)
    return extend_schema(**defaults)


def system_health_schema(**kwargs):
    """Schema decorator for system health endpoints."""
    defaults = {
        'tags': [APITags.SYSTEM_HEALTH],
        'examples': [
            COMMON_EXAMPLES['server_error']
        ]
    }
    defaults.update(kwargs)
    return extend_schema(**defaults)
