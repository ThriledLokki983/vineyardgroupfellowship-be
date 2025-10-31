"""
Performance monitoring middleware for tracking request/response metrics.

This middleware captures:
- Request/response times for all endpoints
- HTTP status codes and error rates
- Database query counts per request
- Performance data aggregation
"""

import time
import logging
from typing import Callable, Dict, Any
from decimal import Decimal
from django.http import HttpRequest, HttpResponse
from django.urls import resolve, Resolver404
from django.db import connection
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache

from ..models import PerformanceMetric, MetricType

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware:
    """
    Middleware to track request/response performance metrics.

    Collects timing data, status codes, and database query counts
    for each request to monitor application performance.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.sample_rate = getattr(settings, 'MONITORING_SAMPLE_RATE', 1.0)
        self.slow_request_threshold = getattr(
            settings, 'MONITORING_SLOW_REQUEST_THRESHOLD_MS', 1000)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip monitoring for certain paths
        if self._should_skip_monitoring(request):
            return self.get_response(request)

        # Start timing and query tracking
        start_time = time.perf_counter()
        start_queries = len(connection.queries)

        # Process the request
        response = self.get_response(request)

        # Calculate metrics
        end_time = time.perf_counter()
        response_time_ms = (end_time - start_time) * 1000
        query_count = len(connection.queries) - start_queries

        # Collect and store metrics
        self._record_request_metrics(
            request, response, response_time_ms, query_count)

        # Add performance headers in development
        if settings.DEBUG:
            response['X-Response-Time'] = f"{response_time_ms:.2f}ms"
            response['X-Query-Count'] = str(query_count)

        return response

    def _should_skip_monitoring(self, request: HttpRequest) -> bool:
        """
        Determine if monitoring should be skipped for this request.

        Skips static files, admin, and health check endpoints.
        """
        path = request.path

        # Skip static files and media
        if path.startswith('/static/') or path.startswith('/media/'):
            return True

        # Skip admin interface (optional)
        if path.startswith('/admin/') and not getattr(settings, 'MONITOR_ADMIN', False):
            return True

        # Skip health check endpoints to avoid self-monitoring
        if path in ['/health/', '/healthz/', '/ready/']:
            return True

        return False

    def _record_request_metrics(
        self,
        request: HttpRequest,
        response: HttpResponse,
        response_time_ms: float,
        query_count: int
    ) -> None:
        """
        Record performance metrics for this request.

        Stores timing, status, and query data for analysis.
        """
        try:
            # Get endpoint information
            endpoint_path = self._get_endpoint_path(request)

            # Basic request context
            user_id = getattr(request.user, 'id', None) if hasattr(
                request, 'user') else None
            context = {
                'endpoint_path': endpoint_path,
                'method': request.method,
                'status_code': response.status_code,
                'query_count': query_count,
                # Convert UUID to string
                'user_id': str(user_id) if user_id else None,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'remote_addr': self._get_client_ip(request),
            }

            # Record response time metric
            PerformanceMetric.objects.create(
                metric_type=MetricType.REQUEST_RESPONSE,
                name=f"{request.method} {endpoint_path}",
                value=Decimal(str(response_time_ms)),
                unit='ms',
                context=context
            )

            # Record query count metric
            PerformanceMetric.objects.create(
                metric_type=MetricType.DATABASE_QUERY,
                name=f"query_count_{endpoint_path}",
                value=Decimal(str(query_count)),
                unit='count',
                context=context
            )

            # Log slow requests
            if response_time_ms > self.slow_request_threshold:
                logger.warning(
                    f"Slow request detected: {request.method} {endpoint_path} "
                    f"took {response_time_ms:.2f}ms with {query_count} queries"
                )

            # Update real-time metrics cache
            self._update_realtime_metrics(
                endpoint_path, request.method, response_time_ms, response.status_code)

        except Exception as e:
            # Don't let monitoring failures affect the application
            logger.error(f"Error recording performance metrics: {e}")

    def _get_endpoint_path(self, request: HttpRequest) -> str:
        """
        Get the endpoint path pattern for this request.

        Converts dynamic URLs like /users/123/ to /users/{id}/ for aggregation.
        """
        try:
            resolver_match = resolve(request.path)
            if resolver_match:
                # Use the URL pattern name or path for aggregation
                return resolver_match.route or request.path
        except Resolver404:
            pass

        # Fallback to the raw path
        return request.path

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _update_realtime_metrics(
        self,
        endpoint_path: str,
        method: str,
        response_time_ms: float,
        status_code: int
    ) -> None:
        """
        Update real-time metrics in cache for monitoring dashboards.

        Maintains sliding window counters for quick access to current metrics.
        """
        try:
            cache_key_prefix = f"metrics:realtime:{method}:{endpoint_path}"
            cache_timeout = 3600  # 1 hour

            # Update request count
            cache.get_or_set(f"{cache_key_prefix}:count", 0, cache_timeout)
            cache.incr(f"{cache_key_prefix}:count")

            # Update error count for 4xx/5xx responses
            if status_code >= 400:
                cache.get_or_set(
                    f"{cache_key_prefix}:errors", 0, cache_timeout)
                cache.incr(f"{cache_key_prefix}:errors")

            # Update response time metrics (simplified)
            current_avg = cache.get(f"{cache_key_prefix}:avg_time", 0)
            current_count = cache.get(f"{cache_key_prefix}:count", 1)

            # Simple moving average calculation
            new_avg = ((current_avg * (current_count - 1)) +
                       response_time_ms) / current_count
            cache.set(f"{cache_key_prefix}:avg_time", new_avg, cache_timeout)

        except Exception as e:
            logger.error(f"Error updating real-time metrics: {e}")


class DatabaseQueryMonitoringMiddleware:
    """
    Middleware to monitor database query performance.

    Tracks slow queries and database performance issues.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.slow_query_threshold = getattr(
            settings, 'MONITORING_SLOW_QUERY_THRESHOLD_MS', 100)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not settings.DEBUG and not getattr(settings, 'MONITOR_DB_QUERIES', False):
            return self.get_response(request)

        # Clear previous queries
        connection.queries_log.clear() if hasattr(connection, 'queries_log') else None

        response = self.get_response(request)

        # Analyze queries
        self._analyze_queries(request)

        return response

    def _analyze_queries(self, request: HttpRequest) -> None:
        """
        Analyze executed queries for performance issues.

        Identifies slow queries and potential N+1 problems.
        """
        try:
            queries = connection.queries

            # Check for slow queries
            for query in queries:
                query_time = float(query.get('time', 0)) * \
                    1000  # Convert to ms

                if query_time > self.slow_query_threshold:
                    logger.warning(
                        f"Slow query detected: {query_time:.2f}ms "
                        f"on {request.path} - {query.get('sql', '')[:100]}..."
                    )

            # Check for potential N+1 queries
            if len(queries) > 10:  # Arbitrary threshold
                logger.warning(
                    f"High query count detected: {len(queries)} queries "
                    f"on {request.path}. Potential N+1 problem."
                )

        except Exception as e:
            logger.error(f"Error analyzing database queries: {e}")
