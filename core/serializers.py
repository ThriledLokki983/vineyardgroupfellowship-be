"""
Core serializers for common response types.
"""

from rest_framework import serializers


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""
    error = serializers.CharField(help_text="Error message")
    details = serializers.DictField(required=False, help_text="Additional error details")


class MessageResponseSerializer(serializers.Serializer):
    """Serializer for simple message responses."""
    message = serializers.CharField(help_text="Response message")
    status = serializers.CharField(default="success", help_text="Status indicator")


class ValidationErrorResponseSerializer(serializers.Serializer):
    """Serializer for validation error responses."""
    error = serializers.CharField(help_text="Error message")
    validation_errors = serializers.DictField(help_text="Field-specific validation errors")


class RateLimitErrorResponseSerializer(serializers.Serializer):
    """Serializer for rate limit error responses."""
    error = serializers.CharField(help_text="Rate limit error message")
    retry_after = serializers.IntegerField(required=False, help_text="Seconds to wait before retrying")


class AuthenticationErrorResponseSerializer(serializers.Serializer):
    """Serializer for authentication error responses."""
    error = serializers.CharField(help_text="Authentication error message")
    code = serializers.CharField(required=False, help_text="Error code")


class PermissionErrorResponseSerializer(serializers.Serializer):
    """Serializer for permission error responses."""
    error = serializers.CharField(help_text="Permission error message")
    required_permission = serializers.CharField(required=False, help_text="Required permission")