"""
Enhanced error handling middleware for improved error tracking and user experience.

This middleware provides:
- Comprehensive error capture and logging
- User-friendly error responses with Problem+JSON format
- Correlation ID tracking for error debugging
- Sensitive data filtering in error responses
"""

import json
import logging
import traceback
import uuid
from typing import Any, Dict, Optional
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import DatabaseError
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from rest_framework.exceptions import APIException

from ..logging.structured import get_contextual_logger, setup_request_logging

logger = get_contextual_logger(__name__)


class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Middleware for enhanced error handling and logging.

    Provides consistent error responses and comprehensive error logging
    with correlation IDs for better debugging.
    """

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Set up request context for error handling."""
        # Set up correlation ID for this request
        correlation_id = setup_request_logging(request)

        # Store start time for response time calculation
        request.start_time = timezone.now()

        return None

    def process_exception(self, request: HttpRequest, exception: Exception) -> Optional[HttpResponse]:
        """
        Handle exceptions and provide user-friendly error responses.

        Returns appropriate error responses while logging detailed error information.
        """
        try:
            # Get correlation ID
            correlation_id = getattr(
                request, 'correlation_id', str(uuid.uuid4()))

            # Determine error type and status code
            error_info = self._classify_error(exception)

            # Log the error with context
            self._log_error(request, exception, error_info, correlation_id)

            # Create user-friendly error response
            error_response = self._create_error_response(
                request, exception, error_info, correlation_id
            )

            return error_response

        except Exception as e:
            # Fallback error handling - log the meta-error
            logger.critical(
                f"Error in error handling middleware: {e}",
                exc_info=True,
                extra={'correlation_id': getattr(
                    request, 'correlation_id', None)}
            )

            # Return basic error response
            return JsonResponse(
                {
                    'type': 'about:blank',
                    'title': 'Internal Server Error',
                    'status': 500,
                    'detail': 'An unexpected error occurred. Please try again.',
                    'instance': request.build_absolute_uri()
                },
                status=500
            )

    def _classify_error(self, exception: Exception) -> Dict[str, Any]:
        """
        Classify the error and determine appropriate response.

        Returns error information including status code, title, and whether
        it's safe to expose details to the user.
        """
        # Database errors
        if isinstance(exception, DatabaseError):
            return {
                'status_code': 503,
                'title': 'Service Temporarily Unavailable',
                'type': 'database_error',
                'safe_to_expose': False,
                'user_message': 'We are experiencing technical difficulties. Please try again later.'
            }

        # Validation errors
        if isinstance(exception, ValidationError):
            return {
                'status_code': 400,
                'title': 'Validation Error',
                'type': 'validation_error',
                'safe_to_expose': True,
                'user_message': None  # Will use exception message
            }

        # Permission errors
        if isinstance(exception, PermissionDenied):
            return {
                'status_code': 403,
                'title': 'Forbidden',
                'type': 'permission_error',
                'safe_to_expose': True,
                'user_message': 'You do not have permission to access this resource.'
            }

        # DRF API exceptions
        if isinstance(exception, APIException):
            return {
                'status_code': exception.status_code,
                'title': exception.__class__.__name__,
                'type': 'api_error',
                'safe_to_expose': True,
                'user_message': None  # Will use exception detail
            }

        # Generic server errors
        return {
            'status_code': 500,
            'title': 'Internal Server Error',
            'type': 'server_error',
            'safe_to_expose': False,
            'user_message': 'An unexpected error occurred. Please try again.'
        }

    def _log_error(self, request: HttpRequest, exception: Exception, error_info: Dict[str, Any], correlation_id: str):
        """Log error with comprehensive context information."""
        # Collect request context
        request_context = {
            'correlation_id': correlation_id,
            'request_path': request.path,
            'request_method': request.method,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'status_code': error_info['status_code'],
            'error_type': error_info['type'],
        }

        # Add user context if available
        if hasattr(request, 'user') and request.user.is_authenticated:
            request_context.update({
                'user_id': request.user.id,
                'username': request.user.username,
            })

        # Add request data (filtered for security)
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if hasattr(request, 'data') and request.data:
                    request_context['request_data'] = self._filter_sensitive_data(
                        dict(request.data))
                elif request.POST:
                    request_context['request_data'] = self._filter_sensitive_data(
                        dict(request.POST))
            except Exception:
                # Don't let data logging errors prevent error logging
                pass

        # Add query parameters
        if request.GET:
            request_context['query_params'] = dict(request.GET)

        # Log at appropriate level based on error type
        if error_info['status_code'] >= 500:
            logger.error(
                f"Server error: {exception}",
                exc_info=True,
                extra=request_context
            )
        elif error_info['status_code'] >= 400:
            logger.warning(
                f"Client error: {exception}",
                extra=request_context
            )
        else:
            logger.info(
                f"Request error: {exception}",
                extra=request_context
            )

    def _create_error_response(self, request: HttpRequest, exception: Exception, error_info: Dict[str, Any], correlation_id: str) -> JsonResponse:
        """Create user-friendly error response in Problem+JSON format."""
        # Base error response following RFC 7807 (Problem Details for HTTP APIs)
        error_response = {
            'type': 'about:blank',
            'title': error_info['title'],
            'status': error_info['status_code'],
            'instance': request.build_absolute_uri(),
            'correlation_id': correlation_id,
        }

        # Add appropriate detail message
        if error_info['safe_to_expose'] and not error_info['user_message']:
            # Use exception message for safe errors
            if hasattr(exception, 'detail'):
                # DRF exceptions
                error_response['detail'] = str(exception.detail)
            elif hasattr(exception, 'message'):
                error_response['detail'] = str(exception.message)
            else:
                error_response['detail'] = str(exception)
        elif error_info['user_message']:
            # Use predefined user-friendly message
            error_response['detail'] = error_info['user_message']
        else:
            # Generic message for unsafe errors
            error_response['detail'] = 'An error occurred while processing your request.'

        # Add validation error details if available
        if isinstance(exception, ValidationError) and hasattr(exception, 'error_dict'):
            error_response['validation_errors'] = exception.error_dict
        elif hasattr(exception, 'detail') and isinstance(exception.detail, dict):
            error_response['validation_errors'] = exception.detail

        # In development, add more debug information
        if settings.DEBUG and error_info['status_code'] >= 500:
            error_response['debug'] = {
                'exception_type': exception.__class__.__name__,
                'exception_message': str(exception),
                'traceback': traceback.format_exc().split('\\n') if settings.DEBUG else None
            }

        return JsonResponse(
            error_response,
            status=error_info['status_code'],
            content_type='application/problem+json'
        )

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip

    def _filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from request data for logging."""
        sensitive_fields = {
            'password', 'password1', 'password2', 'token', 'secret', 'key',
            'authorization', 'auth_token', 'access_token', 'refresh_token',
            'csrf_token', 'session_key', 'secret_key', 'credit_card', 'ssn'
        }

        filtered_data = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                filtered_data[key] = '[FILTERED]'
            else:
                filtered_data[key] = value

        return filtered_data


class CorrelationIdMiddleware(MiddlewareMixin):
    """
    Middleware to add correlation IDs to all responses.

    Helps with request tracing and debugging across services.
    """

    def process_request(self, request: HttpRequest) -> None:
        """Set up correlation ID for the request."""
        # Check if correlation ID is provided in headers
        correlation_id = request.META.get('HTTP_X_CORRELATION_ID')

        if not correlation_id:
            # Generate new correlation ID
            correlation_id = str(uuid.uuid4())

        # Store on request
        request.correlation_id = correlation_id

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add correlation ID to response headers."""
        correlation_id = getattr(request, 'correlation_id', None)
        if correlation_id:
            response['X-Correlation-ID'] = correlation_id

        return response
