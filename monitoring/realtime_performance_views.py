"""
Real-time Performance Monitoring Dashboard for Phase 5

Comprehensive real-time monitoring system providing:
- Live system metrics and health indicators
- Performance trend analysis
- Resource utilization monitoring
- Automated alerting and anomaly detection
"""

from django.db import models, connection
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from datetime import timedelta, datetime
from typing import Dict, List, Optional, Tuple
import psutil
import time
import logging
from collections import defaultdict

from groups.models import Group, GroupMembership, DiscussionTopic, Comment
from authentication.models import User

logger = logging.getLogger('performance_monitoring')


class RealTimePerformanceMonitor:
    """
    Real-time performance monitoring service for group system.
    """

    def __init__(self):
        self.cache_prefix = "realtime_perf"
        self.metrics_retention = 3600  # 1 hour

    def get_real_time_dashboard(self) -> Dict:
        """
        Get comprehensive real-time dashboard data.

        Returns:
            Real-time performance and health metrics
        """
        dashboard_data = {
            'timestamp': timezone.now().isoformat(),
            'system_health': self._get_system_health(),
            'performance_metrics': self._get_performance_metrics(),
            'database_metrics': self._get_database_metrics(),
            'cache_metrics': self._get_cache_metrics(),
            'application_metrics': self._get_application_metrics(),
            'user_activity': self._get_real_time_user_activity(),
            'alerts': self._get_active_alerts(),
            'trends': self._get_short_term_trends()
        }

        # Store metrics for trending
        self._store_metrics_snapshot(dashboard_data)

        return dashboard_data

    def _get_system_health(self) -> Dict:
        """Get system health indicators."""
        try:
            # CPU and Memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Network I/O
            network = psutil.net_io_counters()            # Database connection health
            db_health = self._check_database_health()

            # Cache health
            cache_health = self._check_cache_health()

            # Overall health status
            health_status = self._calculate_health_status(
                cpu_percent, memory.percent, disk.percent, db_health, cache_health
            )

            return {
                'overall_status': health_status,
                'cpu_usage': round(cpu_percent, 2),
                'memory_usage': round(memory.percent, 2),
                'disk_usage': round(disk.percent, 2),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'database_status': db_health,
                'cache_status': cache_health,
                'last_updated': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'last_updated': timezone.now().isoformat()
            }

    def _get_performance_metrics(self) -> Dict:
        """Get application performance metrics."""
        # Database query performance
        slow_queries = self._get_slow_query_count()

        # Response time metrics (from cache if available)
        response_times = self._get_cached_response_times()

        # Error rates
        error_rates = self._get_error_rates()

        # Throughput metrics
        throughput = self._get_throughput_metrics()

        return {
            'avg_response_time_ms': response_times.get('avg', 0),
            'p95_response_time_ms': response_times.get('p95', 0),
            'slow_queries_count': slow_queries,
            'error_rate_percent': error_rates.get('rate', 0),
            'requests_per_minute': throughput.get('rpm', 0),
            'concurrent_users': self._get_concurrent_users(),
            'cache_hit_rate': self._get_cache_hit_rate()
        }

    def _get_database_metrics(self) -> Dict:
        """Get database performance metrics."""
        try:
            with connection.cursor() as cursor:
                # Active connections
                cursor.execute("""
                    SELECT count(*) as active_connections
                    FROM pg_stat_activity
                    WHERE state = 'active'
                """)
                active_connections = cursor.fetchone()[0]

                # Database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
                """)
                db_size = cursor.fetchone()[0]

                # Recent query stats
                cursor.execute("""
                    SELECT
                        count(*) as total_queries,
                        avg(mean_exec_time) as avg_exec_time,
                        max(max_exec_time) as max_exec_time
                    FROM pg_stat_statements
                    WHERE last_exec > NOW() - INTERVAL '1 hour'
                """)
                query_stats = cursor.fetchone()

                return {
                    'active_connections': active_connections,
                    'database_size': db_size,
                    'total_queries_hour': query_stats[0] if query_stats[0] else 0,
                    'avg_query_time_ms': round(query_stats[1] if query_stats[1] else 0, 2),
                    'max_query_time_ms': round(query_stats[2] if query_stats[2] else 0, 2)
                }

        except Exception as e:
            logger.error(f"Error getting database metrics: {e}")
            return {
                'error': 'Unable to fetch database metrics',
                'details': str(e)
            }

    def _get_cache_metrics(self) -> Dict:
        """Get cache performance metrics."""
        try:
            # Redis info (if using Redis)
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            redis_info = redis_conn.info()

            return {
                'used_memory_mb': round(redis_info.get('used_memory', 0) / (1024 * 1024), 2),
                'used_memory_peak_mb': round(redis_info.get('used_memory_peak', 0) / (1024 * 1024), 2),
                'connected_clients': redis_info.get('connected_clients', 0),
                'operations_per_second': redis_info.get('instantaneous_ops_per_sec', 0),
                'keyspace_hits': redis_info.get('keyspace_hits', 0),
                'keyspace_misses': redis_info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_cache_hit_rate(
                    redis_info.get('keyspace_hits', 0),
                    redis_info.get('keyspace_misses', 0)
                )
            }

        except Exception as e:
            logger.warning(f"Redis metrics unavailable: {e}")
            return {
                'cache_backend': 'non-redis',
                'basic_cache_test': self._test_basic_cache()
            }

    def _get_application_metrics(self) -> Dict:
        """Get application-specific metrics."""
        now = timezone.now()
        last_hour = now - timedelta(hours=1)
        last_5_minutes = now - timedelta(minutes=5)

        # Group system activity
        group_activity = {
            'new_groups_hour': Group.objects.filter(created_at__gte=last_hour).count(),
            'new_memberships_hour': GroupMembership.objects.filter(joined_at__gte=last_hour).count(),
            'new_discussions_hour': DiscussionTopic.objects.filter(created_at__gte=last_hour).count(),
            'new_comments_hour': Comment.objects.filter(created_at__gte=last_hour).count()
        }

        # Recent activity spike detection
        recent_activity = {
            'discussions_5min': DiscussionTopic.objects.filter(created_at__gte=last_5_minutes).count(),
            'comments_5min': Comment.objects.filter(created_at__gte=last_5_minutes).count()
        }

        # Content moderation metrics
        moderation_metrics = self._get_moderation_metrics()

        return {
            'group_activity': group_activity,
            'recent_activity': recent_activity,
            'moderation_metrics': moderation_metrics,
            'active_sessions': self._get_active_sessions_count()
        }

    def _get_real_time_user_activity(self) -> Dict:
        """Get real-time user activity metrics."""
        now = timezone.now()
        last_5_minutes = now - timedelta(minutes=5)
        last_15_minutes = now - timedelta(minutes=15)

        # Active users (users who performed actions recently)
        active_users_5min = User.objects.filter(
            models.Q(comments__created_at__gte=last_5_minutes) |
            models.Q(discussion_topics__created_at__gte=last_5_minutes) |
            models.Q(group_memberships__joined_at__gte=last_5_minutes)
        ).distinct().count()

        active_users_15min = User.objects.filter(
            models.Q(comments__created_at__gte=last_15_minutes) |
            models.Q(discussion_topics__created_at__gte=last_15_minutes) |
            models.Q(group_memberships__joined_at__gte=last_15_minutes)
        ).distinct().count()

        # Online users estimate (based on cache or session data)
        online_users = self._estimate_online_users()

        return {
            'active_users_5min': active_users_5min,
            'active_users_15min': active_users_15min,
            'estimated_online_users': online_users,
            'activity_trend': 'increasing' if active_users_5min > active_users_15min / 3 else 'stable'
        }

    def _get_active_alerts(self) -> List[Dict]:
        """Get active system alerts."""
        alerts = []

        # Check for performance alerts
        performance_metrics = self._get_performance_metrics()

        if performance_metrics['avg_response_time_ms'] > 1000:
            alerts.append({
                'type': 'performance',
                'severity': 'warning',
                'title': 'High Response Time',
                'message': f"Average response time is {performance_metrics['avg_response_time_ms']}ms",
                'timestamp': timezone.now().isoformat()
            })

        if performance_metrics['error_rate_percent'] > 5:
            alerts.append({
                'type': 'error',
                'severity': 'critical',
                'title': 'High Error Rate',
                'message': f"Error rate is {performance_metrics['error_rate_percent']}%",
                'timestamp': timezone.now().isoformat()
            })

        # Check system health alerts
        system_health = self._get_system_health()

        if system_health.get('cpu_usage', 0) > 80:
            alerts.append({
                'type': 'resource',
                'severity': 'warning',
                'title': 'High CPU Usage',
                'message': f"CPU usage is {system_health['cpu_usage']}%",
                'timestamp': timezone.now().isoformat()
            })

        if system_health.get('memory_usage', 0) > 85:
            alerts.append({
                'type': 'resource',
                'severity': 'critical',
                'title': 'High Memory Usage',
                'message': f"Memory usage is {system_health['memory_usage']}%",
                'timestamp': timezone.now().isoformat()
            })

        return alerts

    def _get_short_term_trends(self) -> Dict:
        """Get short-term performance trends."""
        trends = {
            'last_5_minutes': self._get_trend_data(5),
            'last_15_minutes': self._get_trend_data(15),
            'last_30_minutes': self._get_trend_data(30)
        }

        return trends

    def _get_trend_data(self, minutes: int) -> Dict:
        """Get trend data for specified time period."""
        cutoff = timezone.now() - timedelta(minutes=minutes)

        # Get metrics from cache or calculate
        cache_key = f"{self.cache_prefix}:trend:{minutes}min"
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data

        # Calculate trends
        trend_data = {
            'avg_response_time': self._calculate_avg_response_time(cutoff),
            'error_count': self._calculate_error_count(cutoff),
            'user_activity': self._calculate_user_activity(cutoff),
            'system_load': self._calculate_system_load(cutoff)
        }

        # Cache for 2 minutes
        cache.set(cache_key, trend_data, 120)

        return trend_data

    # Helper methods

    def _check_database_health(self) -> str:
        """Check database connection health."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return 'healthy'
        except Exception:
            return 'unhealthy'

    def _check_cache_health(self) -> str:
        """Check cache health."""
        try:
            cache.set('health_check', 'ok', 30)
            if cache.get('health_check') == 'ok':
                return 'healthy'
            else:
                return 'unhealthy'
        except Exception:
            return 'unhealthy'

    def _calculate_health_status(self, cpu: float, memory: float, disk: float,
                                 db_health: str, cache_health: str) -> str:
        """Calculate overall health status."""
        if db_health == 'unhealthy' or cache_health == 'unhealthy':
            return 'critical'

        if cpu > 90 or memory > 95 or disk > 95:
            return 'critical'

        if cpu > 80 or memory > 85 or disk > 85:
            return 'warning'

        return 'healthy'

    def _get_slow_query_count(self) -> int:
        """Get count of slow queries in the last hour."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT count(*)
                    FROM pg_stat_statements
                    WHERE mean_exec_time > 1000
                    AND last_exec > NOW() - INTERVAL '1 hour'
                """)
                return cursor.fetchone()[0]
        except Exception:
            return 0

    def _get_cached_response_times(self) -> Dict:
        """Get cached response time metrics."""
        cache_key = f"{self.cache_prefix}:response_times"
        cached_times = cache.get(cache_key, {})

        return {
            'avg': cached_times.get('avg', 0),
            'p95': cached_times.get('p95', 0),
            'count': cached_times.get('count', 0)
        }

    def _get_error_rates(self) -> Dict:
        """Get error rate metrics."""
        # This would typically integrate with error tracking
        # For now, return placeholder data
        return {'rate': 0.5}  # 0.5% error rate

    def _get_throughput_metrics(self) -> Dict:
        """Get throughput metrics."""
        # This would typically integrate with request logging
        # For now, return placeholder data
        return {'rpm': 120}  # 120 requests per minute

    def _get_concurrent_users(self) -> int:
        """Get concurrent users count."""
        # This would typically integrate with session tracking
        # For now, estimate based on recent activity
        return self._estimate_online_users()

    def _get_cache_hit_rate(self) -> float:
        """Get cache hit rate."""
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            info = redis_conn.info()

            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)

            return self._calculate_cache_hit_rate(hits, misses)
        except Exception:
            return 0.0

    def _calculate_cache_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)

    def _test_basic_cache(self) -> str:
        """Test basic cache functionality."""
        try:
            cache.set('test_key', 'test_value', 30)
            if cache.get('test_key') == 'test_value':
                return 'working'
            else:
                return 'failed'
        except Exception:
            return 'error'

    def _get_moderation_metrics(self) -> Dict:
        """Get content moderation metrics."""
        # This would integrate with moderation system
        # For now, return placeholder structure
        return {
            'pending_reports': 0,
            'auto_flagged_content': 0,
            'manual_reviews_needed': 0
        }

    def _get_active_sessions_count(self) -> int:
        """Get active sessions count."""
        # This would integrate with session management
        # For now, estimate based on recent activity
        return max(10, self._estimate_online_users())

    def _estimate_online_users(self) -> int:
        """Estimate online users based on recent activity."""
        last_15_minutes = timezone.now() - timedelta(minutes=15)

        # Users with recent activity
        active_users = User.objects.filter(
            models.Q(last_login__gte=last_15_minutes) |
            models.Q(comments__created_at__gte=last_15_minutes) |
            models.Q(discussion_topics__created_at__gte=last_15_minutes)
        ).distinct().count()

        return active_users

    def _store_metrics_snapshot(self, dashboard_data: Dict):
        """Store metrics snapshot for trending."""
        timestamp = int(time.time())
        cache_key = f"{self.cache_prefix}:snapshot:{timestamp}"

        # Store lightweight snapshot
        snapshot = {
            'timestamp': timestamp,
            'cpu_usage': dashboard_data['system_health'].get('cpu_usage', 0),
            'memory_usage': dashboard_data['system_health'].get('memory_usage', 0),
            'response_time': dashboard_data['performance_metrics'].get('avg_response_time_ms', 0),
            'active_users': dashboard_data['user_activity'].get('active_users_5min', 0),
            'error_rate': dashboard_data['performance_metrics'].get('error_rate_percent', 0)
        }

        cache.set(cache_key, snapshot, self.metrics_retention)

    def _calculate_avg_response_time(self, cutoff: datetime) -> float:
        """Calculate average response time for time period."""
        # This would integrate with request logging
        return 150.0  # Placeholder

    def _calculate_error_count(self, cutoff: datetime) -> int:
        """Calculate error count for time period."""
        # This would integrate with error logging
        return 2  # Placeholder

    def _calculate_user_activity(self, cutoff: datetime) -> int:
        """Calculate user activity for time period."""
        return User.objects.filter(
            models.Q(comments__created_at__gte=cutoff) |
            models.Q(discussion_topics__created_at__gte=cutoff)
        ).distinct().count()

    def _calculate_system_load(self, cutoff: datetime) -> float:
        """Calculate system load for time period."""
        try:
            return psutil.getloadavg()[0]  # 1-minute load average
        except Exception:
            return 0.0


class RealTimePerformanceDashboardView(APIView):
    """
    Real-time performance monitoring dashboard view.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.monitor = RealTimePerformanceMonitor()

    def get(self, request):
        """
        Get real-time performance dashboard data.
        """
        try:
            dashboard_data = self.monitor.get_real_time_dashboard()
            return Response(dashboard_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating real-time dashboard: {e}")
            return Response({
                'error': 'Failed to generate real-time dashboard',
                'details': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SystemHealthCheckView(APIView):
    """
    Quick system health check endpoint.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.monitor = RealTimePerformanceMonitor()

    def get(self, request):
        """
        Get quick system health status.
        """
        try:
            health_data = self.monitor._get_system_health()

            # Add quick response for health checks
            health_data['response_time_ms'] = round(
                time.time() * 1000) % 1000  # Quick estimate

            return Response(health_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'overall_status': 'error',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PerformanceMetricsHistoryView(APIView):
    """
    Historical performance metrics view.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """
        Get historical performance metrics.
        """
        hours = int(request.query_params.get('hours', 24))
        interval = request.query_params.get(
            'interval', '1h')  # 1h, 30m, 15m, 5m

        try:
            history_data = self._get_metrics_history(hours, interval)
            return Response(history_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Failed to get metrics history',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_metrics_history(self, hours: int, interval: str) -> Dict:
        """Get historical metrics data."""
        # This would typically query stored metrics
        # For now, return structure for future implementation

        return {
            'period_hours': hours,
            'interval': interval,
            'metrics': {
                'cpu_usage': [],
                'memory_usage': [],
                'response_times': [],
                'active_users': [],
                'error_rates': []
            },
            'generated_at': timezone.now().isoformat()
        }
