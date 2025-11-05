"""
Home and health check views for the Vineyard Group Fellowship API server.
"""
from django.shortcuts import render
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import django
import sys
from datetime import datetime


def home(request):
    """
    Home page view for the Vineyard Group Fellowship API server.
    Displays API information and available endpoints.
    """
    context = {
        'server_name': 'Vineyard Group Fellowship API',
        'version': 'v1',
        'status': 'active',
    }
    return render(request, 'home.html', context)


def health_check(request):
    """
    Health check view for monitoring and status verification.
    """
    # Check database connection
    db_status = 'operational'
    db_type = 'Unknown'
    db_response_time = 'N/A'
    try:
        from django.db import connections
        from django.db.utils import OperationalError
        import time

        start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_response_time = f"{int((time.time() - start) * 1000)}ms"
        db_status = 'operational'

        # Get database type
        db_engine = settings.DATABASES['default']['ENGINE']
        if 'postgresql' in db_engine:
            db_type = 'PostgreSQL'
        elif 'sqlite' in db_engine:
            db_type = 'SQLite'
        elif 'mysql' in db_engine:
            db_type = 'MySQL'
    except Exception as e:
        db_status = 'failed'
        db_response_time = 'N/A'

    # Check cache connection
    cache_status = 'operational'
    cache_type = 'Unknown'
    cache_response_time = 'N/A'
    try:
        import time
        start = time.time()
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        cache_response_time = f"{int((time.time() - start) * 1000)}ms"
        cache_status = 'operational'

        # Get cache type
        cache_backend = settings.CACHES['default']['BACKEND']
        if 'redis' in cache_backend.lower():
            cache_type = 'Redis'
        elif 'memcached' in cache_backend.lower():
            cache_type = 'Memcached'
        elif 'locmem' in cache_backend.lower():
            cache_type = 'Local Memory'
        elif 'dummy' in cache_backend.lower():
            cache_type = 'Dummy Cache'
    except Exception as e:
        cache_status = 'failed'
        cache_response_time = 'N/A'

    # Determine overall system status
    system_status = 'healthy' if db_status == 'operational' and cache_status == 'operational' else 'unhealthy'
    
    context = {
        'status': system_status,
        'overall_status': system_status,  # Template expects overall_status
        'service': 'Vineyard Group Fellowship API',
        'db_status': db_status,
        'db_engine': db_type,  # Template expects db_engine
        'db_type': db_type,
        'db_response_time': db_response_time,
        'cache_status': cache_status,
        'cache_backend': cache_type,  # Template expects cache_backend
        'cache_type': cache_type,
        'cache_response_time': cache_response_time,
        'api_status': 'operational',
        'api_version': 'v1',
        'api_endpoints': 12,  # You can update this to be dynamic
        'endpoint_count': 12,  # Template expects endpoint_count
        'environment': settings.DEBUG and 'Development' or 'Production',
        'django_version': django.get_version(),
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'debug_mode': settings.DEBUG,
        'debug_status': 'Enabled' if settings.DEBUG else 'Disabled',
        'timezone': settings.TIME_ZONE,
        'language': settings.LANGUAGE_CODE,
        'last_checked': datetime.now().strftime('%A, %B %d, %Y at %I:%M:%S %p'),
        'check_time': datetime.now().strftime('%A, %B %d, %Y at %I:%M:%S %p'),
    }
    return render(request, 'health_check.html', context)
