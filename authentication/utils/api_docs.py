"""
API Documentation utilities for consistent tagging and schema generation.
"""

from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.openapi import AutoSchema


# Standard API tags for documentation organization
class APITags:
    AUTHENTICATION = "Authentication"
    USER_PROFILES = "User Profiles"
    EMAIL_VERIFICATION = "Email Verification"
    PASSWORD_MANAGEMENT = "Password Management"
    SESSION_MANAGEMENT = "Session Management"
    SECURITY = "Security"
    SYSTEM = "System"


# Common response examples
COMMON_EXAMPLES = {
    'validation_error': OpenApiExample(
        name="Validation Error",
        description="Example of validation error response",
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
        description="Example of authentication error",
        value={
            "error": "Authentication failed",
            "message": "Invalid credentials provided"
        }
    ),
    'permission_error': OpenApiExample(
        name="Permission Error",
        description="Example of permission denied error",
        value={
            "error": "Permission denied",
            "message": "You do not have permission to perform this action"
        }
    ),
    'rate_limit_error': OpenApiExample(
        name="Rate Limit Error",
        description="Example of rate limit exceeded error",
        value={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": 3600
        }
    )
}


def authentication_schema(**kwargs):
    """Decorator for authentication-related endpoints."""
    return extend_schema(
        tags=[APITags.AUTHENTICATION],
        **kwargs
    )


def email_verification_schema(**kwargs):
    """Decorator for email verification endpoints."""
    return extend_schema(
        tags=[APITags.EMAIL_VERIFICATION],
        **kwargs
    )


def user_profile_schema(**kwargs):
    """Decorator for user profile endpoints."""
    return extend_schema(
        tags=[APITags.USER_PROFILES],
        **kwargs
    )


def session_management_schema(**kwargs):
    """Decorator for session management endpoints."""
    return extend_schema(
        tags=[APITags.SESSION_MANAGEMENT],
        **kwargs
    )


def security_schema(**kwargs):
    """Decorator for security operations, audit logs, and threat monitoring."""
    return extend_schema(
        tags=[APITags.SECURITY],
        **kwargs
    )


def system_schema(**kwargs):
    """Decorator for health checks and system status endpoints."""
    return extend_schema(
        tags=[APITags.SYSTEM],
        **kwargs
    )
