"""
 Enhanced CSRF middleware for Vineyard Group Fellowship API.

This middleware extends Django's CSRF protection with additional
features for SPA applications and enhanced security monitoring.
"""

import logging
import time
from typing import Optional, Callable
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class EnhancedCSRFMiddleware(CsrfViewMiddleware):
    """
     Enhanced CSRF middleware with additional security features.

    Extends Django's CSRF middleware with:
    - Enhanced logging and monitoring
    - SPA-specific token handling
    - Rate limiting for CSRF failures
    - Custom token validation
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        super().__init__(get_response)
        self.csrf_failure_count = {}
        self.csrf_failure_window = 300  # 5 minutes
        self.max_failures_per_ip = 10

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Enhanced request processing with monitoring.

        Args:
            request: Django request object

        Returns:
            HttpResponse if request should be rejected, None otherwise
        """
        # Completely skip Enhanced CSRF for admin URLs - let Django's standard CSRF handle it
        if request.path.startswith('/admin/'):
            return None

        # Check for excessive CSRF failures from this IP
        client_ip = self._get_client_ip(request)
        if self._is_rate_limited(client_ip):
            logger.warning(f"CSRF rate limit exceeded for IP: {client_ip}")
            return self._create_rate_limit_response(request)

        # Add CSRF metadata to request for monitoring
        request.csrf_metadata = {
            'client_ip': client_ip,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'origin': request.META.get('HTTP_ORIGIN', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
            'timestamp': timezone.now(),
        }

        return super().process_request(request)

    def process_view(self, request: HttpRequest, callback: Callable,
                     callback_args: tuple, callback_kwargs: dict) -> Optional[HttpResponse]:
        """
        Enhanced view processing with custom validation.

        Args:
            request: Django request object
            callback: View function
            callback_args: View function arguments
            callback_kwargs: View function keyword arguments

        Returns:
            HttpResponse if request should be rejected, None otherwise
        """
        # Completely skip Enhanced CSRF for admin URLs - let Django's standard CSRF handle it
        if request.path.startswith('/admin/'):
            return None

        # Skip CSRF for certain endpoints (like CSRF token retrieval)
        if self._should_skip_csrf(request):
            return None

        # Add custom CSRF validation for API endpoints
        validation_result = self._validate_csrf_token(request)
        if not validation_result['is_valid']:
            self._record_csrf_failure(request, validation_result['reason'])
            return self._create_csrf_failure_response(request, validation_result['reason'])

        return super().process_view(request, callback, callback_args, callback_kwargs)

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client IP is rate limited for CSRF failures."""
        current_time = time.time()
        failure_times = self.csrf_failure_count.get(client_ip, [])

        # Remove old failures outside the window
        failure_times = [t for t in failure_times
                         if current_time - t < self.csrf_failure_window]
        self.csrf_failure_count[client_ip] = failure_times

        return len(failure_times) >= self.max_failures_per_ip

    def _record_csrf_failure(self, request: HttpRequest, reason: str) -> None:
        """Record CSRF failure for rate limiting."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        if client_ip not in self.csrf_failure_count:
            self.csrf_failure_count[client_ip] = []

        self.csrf_failure_count[client_ip].append(current_time)

        # Log the failure
        logger.warning(
            f"CSRF validation failed: {reason} for {request.method} {request.path} "
            f"from {client_ip} ({request.META.get('HTTP_USER_AGENT', 'Unknown')})"
        )

    def _should_skip_csrf(self, request: HttpRequest) -> bool:
        """Check if CSRF should be skipped for this request."""
        # Check for @csrf_exempt decorator
        if getattr(request, '_dont_enforce_csrf_checks', False):
            return True

        skip_paths = [
            '/admin/',  # Django admin interface
            '/api/v1/csrf/token/',
            '/api/v1/csrf/status/',
            '/api/v1/security/csp-report/',  # CSP reports don't send CSRF tokens
            '/api/docs/',
            '/api/schema/',
        ]

        return any(request.path.startswith(path) for path in skip_paths)

    def _validate_csrf_token(self, request: HttpRequest) -> dict:
        """Custom CSRF token validation."""
        # Skip validation for safe methods
        if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            return {'is_valid': True}

        # Check for CSRF exemption
        if getattr(request, '_dont_enforce_csrf_checks', False):
            return {'is_valid': True}

        # Get CSRF token from cookie and header
        csrf_cookie = request.COOKIES.get(settings.CSRF_COOKIE_NAME)
        csrf_header = request.META.get(
            getattr(settings, 'CSRF_HEADER_NAME', 'HTTP_X_CSRFTOKEN')
        )

        # Validate tokens
        if not csrf_cookie:
            return {'is_valid': False, 'reason': 'CSRF_COOKIE_MISSING'}

        if not csrf_header:
            return {'is_valid': False, 'reason': 'CSRF_TOKEN_MISSING'}

        if csrf_cookie != csrf_header:
            return {'is_valid': False, 'reason': 'CSRF_TOKEN_INCORRECT'}

        # Additional custom validations can be added here

        return {'is_valid': True}

    def _create_rate_limit_response(self, request: HttpRequest) -> HttpResponse:
        """Create response for rate limited requests."""
        from django.http import JsonResponse
        from rest_framework import status

        return JsonResponse({
            'type': 'about:blank',
            'title': 'Rate Limit Exceeded',
            'status': 429,
            'detail': 'Too many CSRF failures. Please wait before trying again.',
            'code': 'CSRF_RATE_LIMIT',
            'retry_after': self.csrf_failure_window,
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    def _create_csrf_failure_response(self, request: HttpRequest, reason: str) -> HttpResponse:
        """Create response for CSRF failures."""
        from core.csrf import csrf_failure_handler
        return csrf_failure_handler(request, reason)


class CSRFTokenRefreshMiddleware(MiddlewareMixin):
    """
     Middleware for automatic CSRF token refresh.

    Automatically refreshes CSRF tokens based on configurable conditions
    such as token age, user activity, or security events.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        super().__init__(get_response)
        self.token_refresh_interval = getattr(
            settings, 'CSRF_TOKEN_REFRESH_INTERVAL', 3600)  # 1 hour

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Process response and refresh CSRF token if needed.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            Modified response with refreshed token if applicable
        """
        # Skip if not an authenticated user
        if not request.user.is_authenticated:
            return response

        # Skip for certain content types
        content_type = response.get('Content-Type', '')
        if not content_type.startswith(('application/json', 'text/html')):
            return response

        # Check if token needs refresh
        if self._should_refresh_token(request):
            self._refresh_csrf_token(request, response)

        return response

    def _should_refresh_token(self, request: HttpRequest) -> bool:
        """
        Determine if CSRF token should be refreshed.

        Args:
            request: Django request object

        Returns:
            True if token should be refreshed
        """
        # Check if user just logged in
        if hasattr(request, 'user') and hasattr(request.user, '_just_logged_in'):
            return True

        # Check for security-sensitive operations
        sensitive_paths = [
            '/api/v1/auth/password/change/',
            '/api/v1/auth/logout/',
            '/api/v1/profile/privacy/',
        ]

        if any(request.path.startswith(path) for path in sensitive_paths):
            return True

        # Add time-based refresh logic here if needed
        # This would require tracking token creation time

        return False

    def _refresh_csrf_token(self, request: HttpRequest, response: HttpResponse) -> None:
        """
        Refresh the CSRF token.

        Args:
            request: Django request object
            response: Django response object
        """
        try:
            from django.middleware.csrf import rotate_token, get_token

            # Rotate the token
            rotate_token(request)
            new_token = get_token(request)

            # Log the refresh
            logger.info(
                f"CSRF token refreshed for user {request.user.id} "
                f"from {self._get_client_ip(request)}"
            )

            # Add header to inform client of token refresh
            response['X-CSRF-Token-Refreshed'] = 'true'
            response['X-CSRF-Token'] = new_token

        except Exception as e:
            logger.error(f"Error refreshing CSRF token: {e}")

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip


class CSRFLoggingMiddleware(MiddlewareMixin):
    """
     Middleware for comprehensive CSRF logging and monitoring.

    Logs all CSRF-related events for security monitoring and analysis.
    """

    def process_request(self, request: HttpRequest) -> None:
        """
        Log CSRF-related request information.

        Args:
            request: Django request object
        """
        # Only log for state-changing methods
        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return

        csrf_data = {
            'has_csrf_cookie': settings.CSRF_COOKIE_NAME in request.COOKIES,
            'has_csrf_header': self._get_csrf_header_name() in request.META,
            'origin': request.META.get('HTTP_ORIGIN', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
            'user_authenticated': request.user.is_authenticated if hasattr(request, 'user') else False,
        }

        # Store for later use in response processing
        request._csrf_logging_data = csrf_data

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Log CSRF validation results.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            Unmodified response
        """
        # Only process if we have logging data
        if not hasattr(request, '_csrf_logging_data'):
            return response

        csrf_data = request._csrf_logging_data
        csrf_data.update({
            'response_status': response.status_code,
            'csrf_failure': response.status_code == 403 and 'csrf' in response.get('Content-Type', '').lower(),
        })

        # Log significant CSRF events
        if csrf_data['csrf_failure'] or (csrf_data['has_csrf_cookie'] and csrf_data['has_csrf_header']):
            logger.info(
                f"CSRF event: {request.method} {request.path} -> {response.status_code} "
                f"(cookie: {csrf_data['has_csrf_cookie']}, header: {csrf_data['has_csrf_header']})"
            )

        return response

    def _get_csrf_header_name(self) -> str:
        """Get the CSRF header name."""
        header_name = getattr(settings, 'CSRF_HEADER_NAME', 'HTTP_X_CSRFTOKEN')
        if header_name.startswith('HTTP_'):
            return header_name
        return f'HTTP_{header_name.replace("-", "_").upper()}'
