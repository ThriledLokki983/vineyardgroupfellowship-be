"""
 CSRF endpoints for Vineyard Group Fellowship API.

Provides endpoints for CSRF token management and status checking.
"""

from django.conf import settings
from django.http import JsonResponse
from django.middleware.csrf import get_token as django_get_token
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_token_view(request):
    """
     Get CSRF token for SPA applications.

    Returns:
        JSON response with CSRF token
    """
    try:
        # Get CSRF token using Django's built-in function
        token = django_get_token(request)

        return Response({
            'csrfToken': token,
            'cookieName': getattr(settings, 'CSRF_COOKIE_NAME', 'csrftoken'),
            'headerName': getattr(settings, 'CSRF_HEADER_NAME', 'X-CSRFToken').replace('HTTP_', '').replace('_', '-'),
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"CSRF token generation error: {e}", exc_info=True)
        return Response({
            'type': 'about:blank',
            'title': 'CSRF Token Error',
            'status': 500,
            'detail': str(e) if settings.DEBUG else 'Unable to generate CSRF token',
            'code': 'CSRF_TOKEN_ERROR',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_rotate_view(request):
    """
     Rotate CSRF token for enhanced security.

    This endpoint allows authenticated users to rotate their CSRF token
    after security-sensitive operations.

    Returns:
        JSON response with new CSRF token
    """
    if not request.user.is_authenticated:
        return Response({
            'type': 'about:blank',
            'title': 'Authentication Required',
            'status': 401,
            'detail': 'Authentication required to rotate CSRF token',
            'code': 'AUTHENTICATION_REQUIRED',
        }, status=status.HTTP_401_UNAUTHORIZED)

    try:
        from django.middleware.csrf import rotate_token as django_rotate_token
        django_rotate_token(request)
        new_token = django_get_token(request)

        return Response({
            'csrfToken': new_token,
            'rotated': True,
            'message': 'CSRF token rotated successfully',
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"CSRF rotation error: {e}", exc_info=True)
        return Response({
            'type': 'about:blank',
            'title': 'CSRF Rotation Error',
            'status': 500,
            'detail': str(e) if settings.DEBUG else 'Unable to rotate CSRF token',
            'code': 'CSRF_ROTATION_ERROR',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def csrf_status_view(request):
    """
     Check CSRF protection status.

    Returns information about CSRF configuration and token status.

    Returns:
        JSON response with CSRF status information
    """
    csrf_data = {
        'csrfEnabled': getattr(settings, 'CSRF_COOKIE_NAME', None) is not None,
        'cookieName': getattr(settings, 'CSRF_COOKIE_NAME', 'csrftoken'),
        'headerName': getattr(settings, 'CSRF_HEADER_NAME', 'X-CSRFToken').replace('HTTP_', '').replace('_', '-'),
        'cookieSecure': getattr(settings, 'CSRF_COOKIE_SECURE', False),
        'cookieHttponly': getattr(settings, 'CSRF_COOKIE_HTTPONLY', False),
        'cookieSamesite': getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Lax'),
        'hasToken': getattr(settings, 'CSRF_COOKIE_NAME', 'csrftoken') in request.COOKIES,
        'userAuthenticated': request.user.is_authenticated if hasattr(request, 'user') else False,
        'spaMode': not getattr(settings, 'CSRF_COOKIE_HTTPONLY', False),
        'trustedOrigins': getattr(settings, 'CSRF_TRUSTED_ORIGINS', []),
    }

    return Response(csrf_data, status=status.HTTP_200_OK)


@api_view(['POST'])
@csrf_exempt
def csrf_validate_view(request):
    """
     Validate CSRF token without performing any action.

    This endpoint allows testing CSRF validation without side effects.

    Returns:
        JSON response indicating validation result
    """
    try:
        # Simple validation: check if token exists in cookie and header
        cookie_name = getattr(settings, 'CSRF_COOKIE_NAME', 'csrftoken')
        has_cookie = cookie_name in request.COOKIES
        has_header = request.META.get('HTTP_X_CSRFTOKEN') is not None

        is_valid = has_cookie and has_header

        return Response({
            'valid': is_valid,
            'hasCookie': has_cookie,
            'hasHeader': has_header,
            'method': request.method,
            'message': 'CSRF validation successful' if is_valid else 'CSRF validation failed',
        }, status=status.HTTP_200_OK if is_valid else status.HTTP_403_FORBIDDEN)

    except Exception as e:
        logger.error(f"CSRF validation error: {e}", exc_info=True)
        return Response({
            'type': 'about:blank',
            'title': 'CSRF Validation Error',
            'status': 500,
            'detail': str(e) if settings.DEBUG else 'Unable to validate CSRF token',
            'code': 'CSRF_VALIDATION_ERROR',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
