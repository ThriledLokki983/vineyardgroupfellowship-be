"""
 Enhanced CSRF Protection utilities for Vineyard Group Fellowship API.

This module provides comprehensive CSRF protection features including:
- Custom CSRF failure handling
- SPA-compatible CSRF token management
- Enhanced CSRF validation
- CSRF token rotation
- Security monitoring and logging
"""

import json
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.middleware.csrf import get_token, rotate_token
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_safe
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def csrf_failure_handler(request: HttpRequest, reason: str = "") -> JsonResponse:
    """
     Custom CSRF failure handler for API responses.

    Provides detailed error information for SPA debugging while
    maintaining security by not revealing sensitive information.

    Args:
        request: Django request object
        reason: CSRF failure reason

    Returns:
        JsonResponse with error details
    """
    from authentication.models import AuditLog

    # Log the CSRF failure for security monitoring
    try:
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action='csrf_failure',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=False,
            details={
                'reason': reason,
                'path': request.path,
                'method': request.method,
                'referer': request.META.get('HTTP_REFERER', ''),
                'csrf_cookie_name': settings.CSRF_COOKIE_NAME,
                'csrf_header_name': settings.CSRF_HEADER_NAME,
            },
            risk_level='medium'
        )
    except Exception as e:
        logger.error(f"Failed to log CSRF failure: {e}")

    # Determine user-friendly error message
    error_messages = {
        'CSRF_COOKIE_INCORRECT': _('CSRF token mismatch. Please refresh the page and try again.'),
        'CSRF_TOKEN_MISSING': _('CSRF token is missing. Please include the token in your request.'),
        'CSRF_TOKEN_INCORRECT': _('CSRF token is invalid. Please refresh the page and try again.'),
        'ORIGIN_CHECKING_FAILED': _('Request origin verification failed. Please check your domain configuration.'),
        'REFERER_CHECKING_FAILED': _('Request referer verification failed.'),
        'CSRF_COOKIE_MISSING': _('CSRF cookie is missing. Please enable cookies and refresh the page.'),
    }

    user_message = error_messages.get(
        reason, _('CSRF verification failed. Please try again.'))

    response_data = {
        'type': 'about:blank',
        'title': 'CSRF Verification Failed',
        'status': 403,
        'detail': user_message,
        'code': 'CSRF_FAILURE',
        'timestamp': timezone.now().isoformat(),
    }

    # Add debug information in development
    if settings.DEBUG:
        response_data['debug'] = {
            'reason': reason,
            'path': request.path,
            'method': request.method,
            'csrf_cookie_name': settings.CSRF_COOKIE_NAME,
            'csrf_header_name': settings.CSRF_HEADER_NAME,
            'has_csrf_cookie': settings.CSRF_COOKIE_NAME in request.COOKIES,
            'csrf_header_present': _get_csrf_header_name() in request.META,
        }

    logger.warning(
        f"CSRF failure: {reason} for {request.method} {request.path} "
        f"from {request.META.get('REMOTE_ADDR')} "
        f"({request.META.get('HTTP_USER_AGENT', 'Unknown')})"
    )

    return JsonResponse(
        response_data,
        status=status.HTTP_403_FORBIDDEN,
        headers={
            'X-CSRF-Failure-Reason': reason,
            'Vary': 'Cookie',
        }
    )


def _get_csrf_header_name() -> str:
    """Get the CSRF header name from settings."""
    header_name = getattr(settings, 'CSRF_HEADER_NAME', 'HTTP_X_CSRFTOKEN')
    if header_name.startswith('HTTP_'):
        return header_name
    return f'HTTP_{header_name.replace("-", "_").upper()}'


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def get_csrf_token(request: HttpRequest) -> Response:
    """
     Get CSRF token for SPA applications.

    This endpoint provides a CSRF token for Single Page Applications
    that need to make authenticated requests.

    Returns:
        Response with CSRF token information
    """
    from authentication.models import AuditLog

    try:
        # Get or generate CSRF token
        csrf_token = get_token(request)

        # Log token request for monitoring
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action='csrf_token_requested',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True,
            details={
                'method': request.method,
                'path': request.path,
                'authenticated': request.user.is_authenticated,
            },
            risk_level='low'
        )

        response_data = {
            'csrfToken': csrf_token,
            'cookieName': settings.CSRF_COOKIE_NAME,
            'headerName': settings.CSRF_HEADER_NAME.replace('HTTP_', '').replace('_', '-'),
            'issued_at': timezone.now().isoformat(),
            'expires_in': getattr(settings, 'CSRF_TOKEN_VALIDITY_SECONDS', 3600),
        }

        # Add debug information in development
        if settings.DEBUG:
            response_data['debug'] = {
                'cookie_secure': getattr(settings, 'CSRF_COOKIE_SECURE', False),
                'cookie_samesite': getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Lax'),
                'cookie_httponly': getattr(settings, 'CSRF_COOKIE_HTTPONLY', False),
                'trusted_origins': getattr(settings, 'CSRF_TRUSTED_ORIGINS', []),
            }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error generating CSRF token: {e}")
        return Response({
            'type': 'about:blank',
            'title': 'CSRF Token Generation Failed',
            'status': 500,
            'detail': 'Unable to generate CSRF token. Please try again.',
            'code': 'CSRF_TOKEN_ERROR',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def rotate_csrf_token(request: HttpRequest) -> Response:
    """
     Rotate CSRF token for enhanced security.

    This endpoint allows rotating the CSRF token, which is useful
    after sensitive operations or suspected token compromise.

    Returns:
        Response with new CSRF token
    """
    from authentication.models import AuditLog

    try:
        # Get old token for logging
        old_token = request.COOKIES.get(settings.CSRF_COOKIE_NAME)

        # Rotate the CSRF token
        rotate_token(request)
        new_token = get_token(request)

        # Log token rotation
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action='csrf_token_rotated',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True,
            details={
                'old_token_present': bool(old_token),
                'reason': request.data.get('reason', 'manual_rotation'),
                'rotated_at': timezone.now().isoformat(),
            },
            risk_level='low'
        )

        response_data = {
            'csrfToken': new_token,
            'cookieName': settings.CSRF_COOKIE_NAME,
            'headerName': settings.CSRF_HEADER_NAME.replace('HTTP_', '').replace('_', '-'),
            'rotated_at': timezone.now().isoformat(),
            'expires_in': getattr(settings, 'CSRF_TOKEN_VALIDITY_SECONDS', 3600),
            'message': 'CSRF token has been rotated successfully.',
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error rotating CSRF token: {e}")
        return Response({
            'type': 'about:blank',
            'title': 'CSRF Token Rotation Failed',
            'status': 500,
            'detail': 'Unable to rotate CSRF token. Please try again.',
            'code': 'CSRF_ROTATION_ERROR',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CSRFValidationMixin:
    """
     Mixin for enhanced CSRF validation in views.

    Provides additional CSRF validation features for API views
    that need custom CSRF handling beyond Django's default.
    """

    def validate_csrf_token(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Validate CSRF token with enhanced checks.

        Args:
            request: Django request object

        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'metadata': {}
        }

        # Check if CSRF cookie is present
        csrf_cookie = request.COOKIES.get(settings.CSRF_COOKIE_NAME)
        if not csrf_cookie:
            validation_result['errors'].append('CSRF cookie is missing')
            return validation_result

        # Check if CSRF header is present
        csrf_header = request.META.get(_get_csrf_header_name())
        if not csrf_header:
            validation_result['errors'].append('CSRF header is missing')
            return validation_result

        # Check token length (basic validation)
        if len(csrf_cookie) < 32:
            validation_result['errors'].append(
                'CSRF token appears to be malformed')
            return validation_result

        # Check if tokens match
        if csrf_cookie != csrf_header:
            validation_result['errors'].append('CSRF tokens do not match')
            return validation_result

        # Additional validation checks
        validation_result['metadata'] = {
            'token_length': len(csrf_cookie),
            'cookie_name': settings.CSRF_COOKIE_NAME,
            'header_name': settings.CSRF_HEADER_NAME,
            'validated_at': timezone.now().isoformat(),
        }

        # Check token age if configured
        token_validity = getattr(settings, 'CSRF_TOKEN_VALIDITY_SECONDS', None)
        if token_validity:
            # This would require additional implementation to track token creation time
            validation_result['warnings'].append(
                'Token age validation not implemented')

        validation_result['is_valid'] = True
        return validation_result

    def handle_csrf_failure(self, request: HttpRequest, reason: str) -> HttpResponse:
        """
        Handle CSRF validation failure with logging.

        Args:
            request: Django request object
            reason: Failure reason

        Returns:
            HTTP response for the failure
        """
        return csrf_failure_handler(request, reason)


def get_csrf_status(request: HttpRequest) -> Dict[str, Any]:
    """
    Get comprehensive CSRF status information.

    Args:
        request: Django request object

    Returns:
        Dictionary with CSRF status details
    """
    csrf_cookie = request.COOKIES.get(settings.CSRF_COOKIE_NAME)
    csrf_header = request.META.get(_get_csrf_header_name())

    status_info = {
        'csrf_protection_enabled': True,
        'cookie_present': bool(csrf_cookie),
        'header_present': bool(csrf_header),
        'tokens_match': csrf_cookie == csrf_header if (csrf_cookie and csrf_header) else False,
        'cookie_name': settings.CSRF_COOKIE_NAME,
        'header_name': settings.CSRF_HEADER_NAME.replace('HTTP_', '').replace('_', '-'),
        'trusted_origins': getattr(settings, 'CSRF_TRUSTED_ORIGINS', []),
        'configuration': {
            'cookie_secure': getattr(settings, 'CSRF_COOKIE_SECURE', False),
            'cookie_samesite': getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Lax'),
            'cookie_httponly': getattr(settings, 'CSRF_COOKIE_HTTPONLY', False),
            'cookie_age': getattr(settings, 'CSRF_COOKIE_AGE', None),
            'use_sessions': getattr(settings, 'CSRF_USE_SESSIONS', False),
        },
        'status_checked_at': timezone.now().isoformat(),
    }

    return status_info


@api_view(['GET'])
@permission_classes([AllowAny])
def csrf_status(request: HttpRequest) -> Response:
    """
     Get CSRF protection status information.

    This endpoint provides detailed information about the current
    CSRF protection status for debugging and monitoring.

    Returns:
        Response with CSRF status information
    """
    try:
        status_info = get_csrf_status(request)

        # Add request-specific information
        status_info['request_info'] = {
            'method': request.method,
            'path': request.path,
            'authenticated': request.user.is_authenticated,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'origin': request.META.get('HTTP_ORIGIN', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
        }

        return Response(status_info, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error getting CSRF status: {e}")
        return Response({
            'type': 'about:blank',
            'title': 'CSRF Status Check Failed',
            'status': 500,
            'detail': 'Unable to check CSRF status. Please try again.',
            'code': 'CSRF_STATUS_ERROR',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
