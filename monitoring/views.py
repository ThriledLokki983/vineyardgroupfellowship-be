"""
Monitoring views for health checks and performance metrics.

Provides endpoints for:
- System health checks for container orchestration
- Performance metrics and monitoring dashboards
- Real-time application status
"""

import time
import logging
from typing import Dict, Any, List
from decimal import Decimal
from datetime import timedelta

from django.http import JsonResponse, HttpResponse
from django.db import connection, connections, models
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from core.api_tags import APITags, monitoring_schema

from .models import HealthCheck, PerformanceMetric, EndpointMetrics, MetricType

logger = logging.getLogger(__name__)


@csrf_exempt
@never_cache
@require_http_methods(["GET"])
def health_check(request):
    """
    Basic health check endpoint for load balancers and container orchestration.

    Returns 200 OK if the application is healthy, 503 if unhealthy.
    """
    try:
        # Basic database connectivity check
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'version': getattr(settings, 'APP_VERSION', 'unknown')
        })

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=503)


@csrf_exempt
@never_cache
@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness check for container orchestration.

    Verifies that all critical services are available.
    """
    checks = {}
    overall_status = 'ready'

    # Database connectivity
    try:
        start_time = time.perf_counter()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_time = (time.perf_counter() - start_time) * 1000

        checks['database'] = {
            'status': 'healthy',
            'response_time_ms': round(db_time, 2)
        }
    except Exception as e:
        checks['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        overall_status = 'not_ready'

    # Cache connectivity (Redis)
    try:
        start_time = time.perf_counter()
        cache.set('health_check', 'test', 10)
        cache.get('health_check')
        cache_time = (time.perf_counter() - start_time) * 1000

        checks['cache'] = {
            'status': 'healthy',
            'response_time_ms': round(cache_time, 2)
        }
    except Exception as e:
        checks['cache'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        overall_status = 'not_ready'

    # Record health check results
    try:
        for check_type, check_data in checks.items():
            HealthCheck.objects.create(
                check_type=check_type,
                status=check_data['status'],
                response_time=Decimal(
                    str(check_data.get('response_time_ms', 0))),
                details=check_data,
                error_message=check_data.get('error', '')
            )
    except Exception as e:
        logger.error(f"Failed to record health check results: {e}")

    response_data = {
        'status': overall_status,
        'timestamp': timezone.now().isoformat(),
        'checks': checks
    }

    status_code = 200 if overall_status == 'ready' else 503
    return JsonResponse(response_data, status=status_code)


@monitoring_schema(
    summary="Get Performance Metrics",
    description="Retrieve aggregated performance metrics for monitoring dashboards",
    responses={
        200: OpenApiResponse(description="Performance metrics data"),
        403: OpenApiResponse(description="Admin access required"),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def performance_metrics(request):
    """
    Get performance metrics for monitoring dashboards.

    Returns aggregated performance data for analysis.
    """
    try:
        # Get time range from query parameters
        hours = int(request.GET.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)

        # Aggregate metrics by type
        metrics_data = {}

        # Request/Response metrics
        request_metrics = PerformanceMetric.objects.filter(
            metric_type=MetricType.REQUEST_RESPONSE,
            timestamp__gte=since
        ).values('name').annotate(
            count=models.Count('id'),
            avg_value=models.Avg('value'),
            min_value=models.Min('value'),
            max_value=models.Max('value')
        )

        metrics_data['request_response'] = list(request_metrics)

        # Database query metrics
        db_metrics = PerformanceMetric.objects.filter(
            metric_type=MetricType.DATABASE_QUERY,
            timestamp__gte=since
        ).values('name').annotate(
            total_queries=models.Sum('value'),
            avg_queries=models.Avg('value')
        )

        metrics_data['database_queries'] = list(db_metrics)

        # Recent health checks
        health_checks = HealthCheck.objects.filter(
            timestamp__gte=since
        ).order_by('-timestamp')[:50]

        metrics_data['health_checks'] = [
            {
                'check_type': check.check_type,
                'status': check.status,
                'response_time': float(check.response_time),
                'timestamp': check.timestamp.isoformat(),
                'error_message': check.error_message
            }
            for check in health_checks
        ]

        return Response({
            'time_range_hours': hours,
            'since': since.isoformat(),
            'metrics': metrics_data
        })

    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {e}")
        return Response(
            {'error': 'Failed to retrieve metrics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@monitoring_schema(
    summary="Get Endpoint Metrics",
    description="Retrieve performance metrics grouped by API endpoint",
    responses={
        200: OpenApiResponse(description="Endpoint performance metrics"),
        403: OpenApiResponse(description="Admin access required"),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def endpoint_metrics(request):
    """
    Get performance metrics grouped by API endpoint.

    Returns aggregated performance data per endpoint.
    """
    try:
        # Get time range from query parameters
        hours = int(request.GET.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)

        # Get aggregated endpoint metrics
        endpoint_data = EndpointMetrics.objects.filter(
            time_window_start__gte=since
        ).order_by('endpoint_path', '-time_window_start')

        # Group by endpoint
        endpoints = {}
        for metric in endpoint_data:
            key = f"{metric.http_method} {metric.endpoint_path}"
            if key not in endpoints:
                endpoints[key] = []

            endpoints[key].append({
                'time_window_start': metric.time_window_start.isoformat(),
                'request_count': metric.request_count,
                'error_count': metric.error_count,
                'error_rate': float(metric.error_rate),
                'avg_response_time': float(metric.avg_response_time),
                'min_response_time': float(metric.min_response_time),
                'max_response_time': float(metric.max_response_time),
                'p95_response_time': float(metric.p95_response_time),
                'status_codes': metric.status_codes
            })

        return Response({
            'time_range_hours': hours,
            'since': since.isoformat(),
            'endpoints': endpoints
        })

    except Exception as e:
        logger.error(f"Error retrieving endpoint metrics: {e}")
        return Response(
            {'error': 'Failed to retrieve endpoint metrics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@monitoring_schema(
    summary="Get Real-time Metrics",
    description="Retrieve real-time performance metrics from cache",
    responses={
        200: OpenApiResponse(description="Real-time performance data"),
        403: OpenApiResponse(description="Admin access required"),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def real_time_metrics(request):
    """
    Get real-time performance metrics from cache.

    Returns current performance data for monitoring dashboards.
    """
    try:
        # Get cached metrics for last hour
        cache_pattern = "metrics:realtime:*"

        # Note: This is a simplified version. In production, you might want
        # to use Redis directly for pattern matching
        real_time_data = {
            'timestamp': timezone.now().isoformat(),
            'endpoints': {},
            'system': {
                'active_connections': getattr(connection, 'queries_count', 0),
                'cache_status': 'healthy'  # Simplified
            }
        }

        return Response(real_time_data)

    except Exception as e:
        logger.error(f"Error retrieving real-time metrics: {e}")
        return Response(
            {'error': 'Failed to retrieve real-time metrics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@monitoring_schema(
    summary="Clear Old Metrics",
    description="Clear old performance metrics to manage database size",
    responses={
        200: OpenApiResponse(description="Metrics cleared successfully"),
        403: OpenApiResponse(description="Admin access required"),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def clear_metrics(request):
    """
    Clear old performance metrics to manage database size.

    Removes metrics older than specified retention period.
    """
    try:
        # Get retention period from request or settings
        retention_days = int(request.data.get(
            'retention_days', getattr(settings, 'METRICS_RETENTION_DAYS', 30)))
        cutoff_date = timezone.now() - timedelta(days=retention_days)

        # Clear old metrics
        deleted_metrics = PerformanceMetric.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()

        deleted_health_checks = HealthCheck.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()

        deleted_endpoint_metrics = EndpointMetrics.objects.filter(
            time_window_start__lt=cutoff_date
        ).delete()

        return Response({
            'message': 'Metrics cleared successfully',
            'retention_days': retention_days,
            'cutoff_date': cutoff_date.isoformat(),
            'deleted_counts': {
                'performance_metrics': deleted_metrics[0] if deleted_metrics else 0,
                'health_checks': deleted_health_checks[0] if deleted_health_checks else 0,
                'endpoint_metrics': deleted_endpoint_metrics[0] if deleted_endpoint_metrics else 0
            }
        })

    except Exception as e:
        logger.error(f"Error clearing metrics: {e}")
        return Response(
            {'error': 'Failed to clear metrics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
