"""
Custom exception handlers for Vineyard Group Fellowship API.

Implements Problem+JSON (RFC 7807) for standardized error responses.
"""

import logging
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException


logger = logging.getLogger(__name__)


class ProblemDetailException(APIException):
    """
    Custom exception for Problem+JSON (RFC 7807) responses.

    Allows raising exceptions with standardized error details.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A problem occurred'
    default_code = 'error'

    def __init__(self, title=None, detail=None, status_code=None, type_uri='about:blank', instance=None):
        self.title = title or 'Error'
        self.type_uri = type_uri
        self.instance = instance

        if status_code:
            self.status_code = status_code

        super().__init__(detail or self.default_detail)


def problem_exception_handler(exc, context):
    """
    Custom exception handler that returns Problem+JSON responses (RFC 7807).

    This provides standardized error responses across all API endpoints.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Transform DRF errors to Problem+JSON format
        problem_data = {
            'type': 'about:blank',
            'title': get_error_title(response.status_code),
            'status': response.status_code,
            'detail': get_error_detail(response.data),
        }

        # Add instance URL if available
        request = context.get('request')
        if request:
            problem_data['instance'] = request.build_absolute_uri()

        # Add validation errors for 400 Bad Request
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            problem_data['invalid_params'] = format_validation_errors(
                response.data)

        # Log the error for monitoring
        log_error(exc, context, response.status_code)

        response.data = problem_data
        response['Content-Type'] = 'application/problem+json'

    return response


def get_error_title(status_code):
    """Get human-readable title for HTTP status code."""
    titles = {
        400: 'Bad Request',
        401: 'Unauthorized',
        403: 'Forbidden',
        404: 'Not Found',
        405: 'Method Not Allowed',
        409: 'Conflict',
        422: 'Unprocessable Entity',
        429: 'Too Many Requests',
        500: 'Internal Server Error',
        502: 'Bad Gateway',
        503: 'Service Unavailable',
    }
    return titles.get(status_code, 'Error')


def get_error_detail(data):
    """Extract human-readable detail from response data."""
    if isinstance(data, dict):
        # Handle DRF serializer errors
        if 'detail' in data:
            return str(data['detail'])
        elif 'non_field_errors' in data:
            return '; '.join(data['non_field_errors'])
        else:
            # Return first error message found
            for key, value in data.items():
                if isinstance(value, list) and value:
                    return f"{key}: {value[0]}"
                elif isinstance(value, str):
                    return f"{key}: {value}"
    elif isinstance(data, list) and data:
        return str(data[0])

    return str(data)


def format_validation_errors(data):
    """Format validation errors for Problem+JSON invalid_params."""
    if not isinstance(data, dict):
        return []

    invalid_params = []
    for field, errors in data.items():
        if isinstance(errors, list):
            for error in errors:
                invalid_params.append({
                    'name': field,
                    'reason': str(error)
                })
        else:
            invalid_params.append({
                'name': field,
                'reason': str(errors)
            })

    return invalid_params


def log_error(exc, context, status_code):
    """Log error for monitoring and debugging."""
    request = context.get('request')
    user = getattr(request, 'user', None)

    logger.error(
        f"API Error {status_code}: {exc}",
        extra={
            'status_code': status_code,
            'exception_type': type(exc).__name__,
            'user_id': getattr(user, 'id', None) if user and user.is_authenticated else None,
            'path': request.path if request else None,
            'method': request.method if request else None,
            'ip_address': get_client_ip(request) if request else None,
        },
        exc_info=status_code >= 500  # Include stack trace for 5xx errors
    )


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
