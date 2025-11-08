"""
Performance Monitoring Middleware
==================================

Tracks request/response metrics for all API endpoints.
Logs slow queries and sends metrics to monitoring systems.
"""

import time
import logging
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

# Import sentry_sdk at module level to avoid import overhead on each request
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

logger = logging.getLogger('performance')


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to track request performance metrics.

    Features:
    - Logs request duration
    - Identifies slow requests (> 200ms warning, > 500ms error)
    - Tracks database query count
    - Sends metrics to Sentry (if configured)
    """

    SLOW_REQUEST_WARNING_MS = 200
    SLOW_REQUEST_ERROR_MS = 500

    def process_request(self, request):
        """Store request start time."""
        request._start_time = time.time()
        request._queries_before = len(self._get_queries())
        return None

    def process_response(self, request, response):
        """Calculate and log request metrics."""
        if not hasattr(request, '_start_time'):
            return response

        # Calculate duration
        duration_ms = (time.time() - request._start_time) * 1000

        # Get query count
        queries_after = len(self._get_queries())
        query_count = queries_after - request._queries_before

        # Prepare log data
        log_data = {
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration_ms, 2),
            'query_count': query_count,
            'user': getattr(request.user, 'username', 'Anonymous') if hasattr(request, 'user') else 'Anonymous',
        }

        # Add to response headers for debugging
        if settings.DEBUG:
            response['X-Request-Duration-Ms'] = str(round(duration_ms, 2))
            response['X-Query-Count'] = str(query_count)

        # Log based on performance
        if duration_ms > self.SLOW_REQUEST_ERROR_MS:
            logger.error(
                f"SLOW REQUEST: {request.method} {request.path} "
                f"took {duration_ms:.2f}ms with {query_count} queries",
                extra=log_data
            )
        elif duration_ms > self.SLOW_REQUEST_WARNING_MS:
            logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {duration_ms:.2f}ms with {query_count} queries",
                extra=log_data
            )
        else:
            logger.info(
                f"{request.method} {request.path} - {duration_ms:.2f}ms ({query_count} queries)",
                extra=log_data
            )

        # Send to Sentry as breadcrumb
        self._add_sentry_breadcrumb(request, duration_ms, query_count)

        return response

    def _get_queries(self):
        """Get current database queries."""
        try:
            from django.db import connection
            return connection.queries
        except Exception:
            return []

    def _add_sentry_breadcrumb(self, request, duration_ms, query_count):
        """Add performance data to Sentry breadcrumb."""
        if not SENTRY_AVAILABLE:
            return

        try:
            sentry_sdk.add_breadcrumb(
                category='performance',
                message=f"{request.method} {request.path}",
                level='info' if duration_ms < self.SLOW_REQUEST_WARNING_MS else 'warning',
                data={
                    'duration_ms': duration_ms,
                    'query_count': query_count,
                    'status_code': getattr(request, 'status_code', None),
                }
            )
        except Exception:
            pass  # Sentry not configured
        except Exception as e:
            logger.debug(f"Failed to add Sentry breadcrumb: {e}")


class QueryCountWarningMiddleware(MiddlewareMixin):
    """
    Middleware to detect N+1 query problems.
    Raises warning if query count exceeds threshold.
    """

    MAX_QUERIES_WARNING = 20
    MAX_QUERIES_ERROR = 50

    def process_request(self, request):
        """Reset query tracking."""
        request._queries_start = len(self._get_queries())
        return None

    def process_response(self, request, response):
        """Check query count and warn if excessive."""
        if not hasattr(request, '_queries_start'):
            return response

        queries_end = len(self._get_queries())
        query_count = queries_end - request._queries_start

        if query_count > self.MAX_QUERIES_ERROR:
            logger.error(
                f"EXCESSIVE QUERIES: {request.method} {request.path} "
                f"executed {query_count} database queries! Possible N+1 problem.",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'query_count': query_count,
                    'status_code': response.status_code,
                }
            )
        elif query_count > self.MAX_QUERIES_WARNING:
            logger.warning(
                f"High query count: {request.method} {request.path} "
                f"executed {query_count} queries. Consider optimization.",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'query_count': query_count,
                }
            )

        return response

    def _get_queries(self):
        """Get current database queries."""
        try:
            from django.db import connection
            return connection.queries
        except Exception:
            return []
