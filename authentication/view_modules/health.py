"""
Health check views for Vineyard Group Fellowship authentication.

This module provides health monitoring endpoints for:
- Authentication service status
- Database connectivity
- Redis cache connectivity
- Email service status
- Overall system health
"""

from django.db import connections
from django.core.cache import cache
from django.core.mail import get_connection
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from core.api_tags import APITags, system_health_schema
import structlog

from ..serializers import HealthCheckSerializer
from core.api_tags import APITags, system_health_schema

logger = structlog.get_logger(__name__)


@system_health_schema(
    description="Check authentication system health",
    summary="Returns the current health status of the authentication system including database connectivity and critical components."
)
@api_view(['GET'])
@permission_classes([AllowAny])
@never_cache
def health_check_view(request):
    """
    Authentication service health check.

    This endpoint provides comprehensive health information about the
    authentication service and its dependencies.

    **Authentication**: Not required
    **Caching**: Disabled (always fresh status)

    **Response**:
    ```json
    {
        "status": "healthy",
        "timestamp": "2023-10-29T15:30:00Z",
        "version": "1.0.0",
        "checks": {
            "database": {
                "status": "healthy",
                "response_time_ms": 15,
                "details": "PostgreSQL connection successful"
            },
            "cache": {
                "status": "healthy",
                "response_time_ms": 3,
                "details": "Redis connection successful"
            },
            "email": {
                "status": "healthy",
                "response_time_ms": 125,
                "details": "SMTP connection successful"
            }
        }
    }
    ```

    **Response Codes**:
    - `200 OK`: Service is healthy
    - `503 Service Unavailable`: One or more components are unhealthy
    """

    timestamp = timezone.now()
    checks = {}
    overall_status = "healthy"

    # Check database connectivity
    db_status = check_database_health()
    checks['database'] = db_status
    if db_status['status'] != 'healthy':
        overall_status = "unhealthy"

    # Check cache connectivity
    cache_status = check_cache_health()
    checks['cache'] = cache_status
    if cache_status['status'] != 'healthy':
        overall_status = "degraded"  # Cache issues are less critical

    # Check email service
    email_status = check_email_health()
    checks['email'] = email_status
    if email_status['status'] != 'healthy':
        overall_status = "degraded"  # Email issues are less critical

    # Check authentication-specific components
    auth_status = check_auth_components()
    checks['authentication'] = auth_status
    if auth_status['status'] != 'healthy':
        overall_status = "unhealthy"

    health_data = {
        'status': overall_status,
        'timestamp': timestamp,
        'version': getattr(settings, 'VERSION', '1.0.0'),
        'checks': checks
    }

    # Log health check
    logger.info(
        "Health check performed",
        status=overall_status,
        checks_count=len(checks),
        ip_address=get_client_ip(request)
    )

    # Return appropriate status code
    if overall_status == "healthy":
        return Response(health_data, status=status.HTTP_200_OK)
    else:
        return Response(health_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)


def check_database_health():
    """Check database connectivity and performance."""
    import time
    start_time = time.time()

    try:
        # Test database connection
        db_conn = connections['default']
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        response_time = int((time.time() - start_time) * 1000)

        return {
            'status': 'healthy',
            'response_time_ms': response_time,
            'details': f'{db_conn.vendor.title()} connection successful'
        }

    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        logger.error("Database health check failed", error=str(e))

        return {
            'status': 'unhealthy',
            'response_time_ms': response_time,
            'details': f'Database connection failed: {str(e)[:100]}'
        }


def check_cache_health():
    """Check Redis cache connectivity and performance."""
    import time
    start_time = time.time()

    try:
        # Test cache connection
        test_key = f'health_check_{int(time.time())}'
        test_value = 'ok'

        cache.set(test_key, test_value, timeout=10)
        retrieved_value = cache.get(test_key)

        if retrieved_value != test_value:
            raise Exception("Cache write/read mismatch")

        cache.delete(test_key)
        response_time = int((time.time() - start_time) * 1000)

        return {
            'status': 'healthy',
            'response_time_ms': response_time,
            'details': 'Redis cache connection successful'
        }

    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        logger.warning("Cache health check failed", error=str(e))

        return {
            'status': 'unhealthy',
            'response_time_ms': response_time,
            'details': f'Cache connection failed: {str(e)[:100]}'
        }


def check_email_health():
    """Check email service connectivity."""
    import time
    start_time = time.time()

    try:
        # Test email backend connection
        connection = get_connection()
        connection.open()
        connection.close()

        response_time = int((time.time() - start_time) * 1000)

        return {
            'status': 'healthy',
            'response_time_ms': response_time,
            'details': 'Email service connection successful'
        }

    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        logger.warning("Email health check failed", error=str(e))

        return {
            'status': 'unhealthy',
            'response_time_ms': response_time,
            'details': f'Email service connection failed: {str(e)[:100]}'
        }


def check_auth_components():
    """Check authentication-specific components."""
    import time
    start_time = time.time()

    try:
        from ..models import User, UserSession, TokenBlacklist

        # Test model queries
        user_count = User.objects.count()
        active_sessions = UserSession.objects.filter(is_active=True).count()
        blacklisted_tokens = TokenBlacklist.objects.count()

        response_time = int((time.time() - start_time) * 1000)

        return {
            'status': 'healthy',
            'response_time_ms': response_time,
            'details': f'Auth models accessible (Users: {user_count}, Sessions: {active_sessions}, Blacklisted: {blacklisted_tokens})'
        }

    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        logger.error("Auth components health check failed", error=str(e))

        return {
            'status': 'unhealthy',
            'response_time_ms': response_time,
            'details': f'Auth components check failed: {str(e)[:100]}'
        }


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
