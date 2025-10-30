"""
CSRF token utilities and views for secure SPA integration.
"""

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.api_tags import APITags


@ensure_csrf_cookie
@require_http_methods(["GET"])
def get_csrf_token(request):
    """
    Get CSRF token for SPA authentication.

    This endpoint provides CSRF tokens for single-page applications
    to use when making authenticated requests.
    """
    token = get_token(request)
    return JsonResponse({
        'csrfToken': token,
        'detail': 'CSRF token generated successfully'
    })


class CSRFTokenAPIView(APIView):
    """
    DRF-compatible CSRF token endpoint.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id='auth_csrf_token',
        summary='Get CSRF Token',
        description='Get CSRF token for SPA authentication',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'csrfToken': {'type': 'string'},
                    'detail': {'type': 'string'}
                }
            }
        },
        tags=[APITags.AUTHENTICATION]
    )
    def get(self, request):
        """Get CSRF token."""
        # Apply CSRF cookie decorator functionality
        get_token(request)  # This sets the cookie
        token = get_token(request)
        return Response({
            'csrfToken': token,
            'detail': 'CSRF token generated successfully'
        })


# Backward compatibility
csrf_token_api = CSRFTokenAPIView.as_view()
