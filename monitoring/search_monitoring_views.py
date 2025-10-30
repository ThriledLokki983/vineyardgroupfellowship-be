"""
Search performance monitoring views for admin dashboard.

Provides endpoints for monitoring search performance, cache effectiveness,
and system health for admin users. Enhanced with Phase 5 analytics.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import json

from groups.services.search_performance_monitor import SearchPerformanceMonitor
from groups.services.search_cache_service import SearchCacheService
from groups.services.enhanced_search_analytics import EnhancedSearchAnalyticsService


class SearchPerformanceDashboardView(APIView):
    """
    Admin dashboard view for search performance monitoring.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.performance_monitor = SearchPerformanceMonitor()
        self.cache_service = SearchCacheService()

    def get(self, request):
        """
        Get comprehensive search performance dashboard data.
        """
        # Get time period from query params
        hours = int(request.query_params.get('hours', 24))

        # Gather performance data
        dashboard_data = {
            'overview': self._get_performance_overview(hours),
            'cache_effectiveness': self._get_cache_effectiveness(),
            'slow_queries': self._get_slow_queries(hours),
            'system_health': self._get_system_health(),
            'trends': self._get_performance_trends(hours)
        }

        return Response(dashboard_data, status=status.HTTP_200_OK)

    def _get_performance_overview(self, hours: int) -> dict:
        """Get performance overview statistics."""
        summary = self.performance_monitor.get_performance_summary(hours)

        overview = {
            'period_hours': hours,
            'total_operations': 0,
            'average_response_time': 0,
            'cache_hit_rate': 0,
            'error_rate': 0,
            'operations_by_type': {}
        }

        total_requests = 0
        total_duration = 0
        total_cache_hits = 0
        total_errors = 0

        for operation_type, stats in summary['operations'].items():
            requests = stats['total_requests']
            if requests > 0:
                total_requests += requests
                total_duration += stats['total_duration_ms']
                total_cache_hits += stats['cache_hits']
                total_errors += stats['errors']

                overview['operations_by_type'][operation_type] = {
                    'requests': requests,
                    'avg_response_time': stats['avg_duration_ms'],
                    'cache_hit_rate': stats['cache_hit_rate'],
                    'error_rate': stats['error_rate']
                }

        if total_requests > 0:
            overview['total_operations'] = total_requests
            overview['average_response_time'] = round(
                total_duration / total_requests, 2)
            overview['cache_hit_rate'] = round(
                (total_cache_hits / total_requests) * 100, 2)
            overview['error_rate'] = round(
                (total_errors / total_requests) * 100, 2)

        return overview

    def _get_cache_effectiveness(self) -> dict:
        """Get cache effectiveness analysis."""
        return self.performance_monitor.get_cache_effectiveness()

    def _get_slow_queries(self, hours: int) -> list:
        """Get slow queries list."""
        return self.performance_monitor.get_slow_queries(hours, limit=20)

    def _get_system_health(self) -> dict:
        """Get overall system health status."""
        health = {
            'status': 'healthy',
            'cache_connection': 'unknown',
            'database_connection': 'unknown',
            'redis_memory_usage': 'unknown',
            'recommendations': []
        }

        # Test cache connection
        try:
            cache.set('health_check', 'ok', timeout=60)
            if cache.get('health_check') == 'ok':
                health['cache_connection'] = 'healthy'
            else:
                health['cache_connection'] = 'error'
                health['status'] = 'degraded'
        except Exception:
            health['cache_connection'] = 'error'
            health['status'] = 'unhealthy'

        # Test database connection
        try:
            from groups.models import Group
            Group.objects.exists()
            health['database_connection'] = 'healthy'
        except Exception:
            health['database_connection'] = 'error'
            health['status'] = 'unhealthy'

        # Get Redis memory info if available
        try:
            redis_stats = self.cache_service.get_cache_stats()
            if redis_stats:
                health['redis_memory_usage'] = 'monitored'
        except Exception:
            health['redis_memory_usage'] = 'unavailable'

        # Generate recommendations based on health
        if health['cache_connection'] != 'healthy':
            health['recommendations'].append({
                'type': 'cache_issue',
                'message': 'Cache connection issues detected. Check Redis connectivity.',
                'priority': 'high'
            })

        if health['database_connection'] != 'healthy':
            health['recommendations'].append({
                'type': 'database_issue',
                'message': 'Database connection issues detected.',
                'priority': 'critical'
            })

        return health

    def _get_performance_trends(self, hours: int) -> dict:
        """Get performance trends over time."""
        trends = {
            'hourly_request_volume': [],
            'hourly_response_times': [],
            'hourly_cache_hit_rates': [],
            'hourly_error_rates': []
        }

        now = timezone.now()

        # Get hourly data for the period
        for hour_offset in range(min(hours, 24)):  # Limit to 24 hours for trends
            hour_time = now - timedelta(hours=hour_offset)
            hour_key = hour_time.strftime('%Y%m%d%H')
            hour_label = hour_time.strftime('%H:00')

            # Aggregate data for all operation types
            total_requests = 0
            total_duration = 0
            total_cache_hits = 0
            total_errors = 0

            for operation_type in ['search', 'suggestions', 'analytics']:
                requests = cache.get(
                    f"hourly_requests:{operation_type}:{hour_key}", 0)
                duration = cache.get(
                    f"hourly_duration:{operation_type}:{hour_key}", 0)
                hits = cache.get(
                    f"hourly_cache_hits:{operation_type}:{hour_key}", 0)
                errors = cache.get(
                    f"hourly_errors:{operation_type}:{hour_key}", 0)

                total_requests += requests
                total_duration += duration
                total_cache_hits += hits
                total_errors += errors

            # Calculate hourly metrics
            avg_response_time = round(
                total_duration / total_requests, 2) if total_requests > 0 else 0
            cache_hit_rate = round(
                (total_cache_hits / total_requests) * 100, 2) if total_requests > 0 else 0
            error_rate = round((total_errors / total_requests)
                               * 100, 2) if total_requests > 0 else 0

            trends['hourly_request_volume'].append({
                'hour': hour_label,
                'requests': total_requests
            })
            trends['hourly_response_times'].append({
                'hour': hour_label,
                'avg_ms': avg_response_time
            })
            trends['hourly_cache_hit_rates'].append({
                'hour': hour_label,
                'hit_rate': cache_hit_rate
            })
            trends['hourly_error_rates'].append({
                'hour': hour_label,
                'error_rate': error_rate
            })

        # Reverse to show oldest to newest
        for trend_list in trends.values():
            trend_list.reverse()

        return trends


class CacheManagementView(APIView):
    """
    Admin view for cache management operations.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.cache_service = SearchCacheService()

    def get(self, request):
        """Get cache statistics and status."""
        stats = self.cache_service.get_cache_stats()

        return Response({
            'cache_stats': stats,
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """Perform cache management operations."""
        action = request.data.get('action')

        if action == 'clear_all':
            self.cache_service.clear_all_caches()
            return Response({
                'message': 'All search caches cleared successfully'
            }, status=status.HTTP_200_OK)

        elif action == 'warm_cache':
            # Warm cache with popular searches
            result = self.cache_service.warm_cache()
            return Response({
                'message': 'Cache warming completed',
                'warmed_items': result
            }, status=status.HTTP_200_OK)

        elif action == 'clear_type':
            cache_type = request.data.get('cache_type')
            if cache_type in ['search', 'suggestions', 'tags']:
                self.cache_service.clear_cache_type(cache_type)
                return Response({
                    'message': f'{cache_type} cache cleared successfully'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid cache type'
                }, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({
                'error': 'Invalid action'
            }, status=status.HTTP_400_BAD_REQUEST)


class SearchAnalyticsView(APIView):
    """
    Enhanced search analytics view for admin insights (Phase 5).
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.enhanced_analytics = EnhancedSearchAnalyticsService()

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, request):
        """Get enhanced search analytics and insights."""
        hours = int(request.query_params.get('hours', 24))
        days = max(1, hours // 24)  # Convert hours to days

        try:
            analytics = self.enhanced_analytics.get_search_overview_dashboard(
                days=days)

            # Add performance trends
            analytics['performance_trends'] = self.enhanced_analytics.get_search_performance_trends(
                days=days)

            return Response(analytics, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Failed to generate enhanced search analytics',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SearchOptimizationInsightsView(APIView):
    """
    Search optimization insights and recommendations view.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.enhanced_analytics = EnhancedSearchAnalyticsService()

    def get(self, request):
        """Get search optimization insights and actionable recommendations."""
        days = int(request.query_params.get('days', 30))

        try:
            # Get comprehensive analytics
            overview = self.enhanced_analytics.get_search_overview_dashboard(
                days=days)

            # Extract optimization-focused data
            optimization_data = {
                'period_days': days,
                'optimization_score': self._calculate_optimization_score(overview),
                'recommendations': overview['optimization_recommendations'],
                'performance_metrics': overview['performance_metrics'],
                'content_gaps': overview['content_effectiveness']['content_gaps'],
                'query_analysis': overview['query_analysis'],
                'actionable_insights': self._generate_actionable_insights(overview)
            }

            return Response(optimization_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Failed to generate optimization insights',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _calculate_optimization_score(self, overview: dict) -> dict:
        """Calculate an overall optimization score."""
        metrics = overview['performance_metrics']

        # Calculate individual scores (0-100)
        effectiveness_score = metrics.get('effectiveness_score', 0)

        # Zero result rate (inverted - lower is better)
        zero_result_rate = overview['query_analysis']['query_statistics'].get(
            'zero_result_rate', 100)
        zero_result_score = max(0, 100 - zero_result_rate)

        # Filter usage score
        search_volume = overview['search_volume']['volume_statistics']
        searches_with_filters = sum(
            1 for f in overview['query_analysis']['filter_usage']['most_used_filters'].values())
        filter_score = min(100, (searches_with_filters /
                           max(search_volume['total_searches'], 1)) * 1000)

        # Overall score (weighted average)
        overall_score = round(
            (effectiveness_score * 0.4 +
             zero_result_score * 0.4 + filter_score * 0.2), 1
        )

        # Determine status
        if overall_score >= 80:
            status = 'excellent'
        elif overall_score >= 60:
            status = 'good'
        elif overall_score >= 40:
            status = 'needs_improvement'
        else:
            status = 'poor'

        return {
            'overall_score': overall_score,
            'status': status,
            'component_scores': {
                'search_effectiveness': effectiveness_score,
                'result_relevance': zero_result_score,
                'filter_adoption': filter_score
            }
        }

    def _generate_actionable_insights(self, overview: dict) -> list:
        """Generate specific actionable insights."""
        insights = []

        # Query analysis insights
        popular_queries = overview['query_analysis']['popular_queries'][:5]
        for query_data in popular_queries:
            if query_data['avg_results'] < 3:
                insights.append({
                    'type': 'content_opportunity',
                    'title': f'Popular query "{query_data["query"]}" needs more content',
                    'description': f'This query is searched {query_data["count"]} times but averages only {query_data["avg_results"]:.1f} results',
                    'action': 'Create or improve groups related to this topic',
                    'impact': 'high' if query_data['count'] > 10 else 'medium'
                })

        # Zero result insights
        zero_result_rate = overview['query_analysis']['query_statistics']['zero_result_rate']
        if zero_result_rate > 25:
            insights.append({
                'type': 'search_algorithm',
                'title': 'High zero-result rate detected',
                'description': f'{zero_result_rate:.1f}% of searches return no results',
                'action': 'Review search algorithm sensitivity and expand search terms',
                'impact': 'high'
            })

        # Filter usage insights
        filter_usage = overview['query_analysis']['filter_usage']
        if filter_usage['total_searches_with_filters'] < overview['search_volume']['volume_statistics']['total_searches'] * 0.2:
            insights.append({
                'type': 'user_experience',
                'title': 'Low filter adoption',
                'description': 'Users are not effectively using search filters',
                'action': 'Improve filter UI visibility and add guided search features',
                'impact': 'medium'
            })

        return insights


class SearchVisualizationDataView(APIView):
    """
    Provide data specifically formatted for visualization components.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.enhanced_analytics = EnhancedSearchAnalyticsService()

    def get(self, request):
        """Get search data formatted for charts and visualizations."""
        days = int(request.query_params.get('days', 30))
        chart_type = request.query_params.get('type', 'overview')

        try:
            if chart_type == 'volume_trends':
                data = self._get_volume_trends_data(days)
            elif chart_type == 'query_themes':
                data = self._get_query_themes_data(days)
            elif chart_type == 'performance_metrics':
                data = self._get_performance_metrics_data(days)
            elif chart_type == 'user_behavior':
                data = self._get_user_behavior_data(days)
            else:
                # Default overview data
                overview = self.enhanced_analytics.get_search_overview_dashboard(
                    days=days)
                data = {
                    'daily_volume': overview['search_volume']['daily_volume'],
                    'hourly_patterns': overview['search_volume']['hourly_patterns'],
                    'query_themes': overview['query_analysis']['query_themes'],
                    'result_distribution': overview['performance_metrics']['result_buckets']
                }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Failed to generate visualization data',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_volume_trends_data(self, days: int) -> dict:
        """Get data for volume trend charts."""
        overview = self.enhanced_analytics.get_search_overview_dashboard(
            days=days)
        return {
            'daily_volume': overview['search_volume']['daily_volume'],
            'hourly_patterns': overview['search_volume']['hourly_patterns'],
            'weekly_patterns': overview['search_volume']['weekly_patterns']
        }

    def _get_query_themes_data(self, days: int) -> dict:
        """Get data for query theme analysis charts."""
        overview = self.enhanced_analytics.get_search_overview_dashboard(
            days=days)
        return {
            'themes': overview['query_analysis']['query_themes'],
            'popular_queries': overview['query_analysis']['popular_queries'][:10],
            'query_length_distribution': overview['query_analysis']['query_statistics']['query_length_distribution']
        }

    def _get_performance_metrics_data(self, days: int) -> dict:
        """Get data for performance metrics charts."""
        overview = self.enhanced_analytics.get_search_overview_dashboard(
            days=days)
        trends = self.enhanced_analytics.get_search_performance_trends(
            days=days)
        return {
            'result_distribution': overview['performance_metrics']['result_buckets'],
            'weekly_trends': trends['weekly_trends'],
            'effectiveness_score': overview['performance_metrics']['effectiveness_score']
        }

    def _get_user_behavior_data(self, days: int) -> dict:
        """Get data for user behavior analysis charts."""
        overview = self.enhanced_analytics.get_search_overview_dashboard(
            days=days)
        return {
            'search_frequency': overview['user_behavior']['user_search_frequency'],
            'session_patterns': overview['user_behavior']['session_patterns'],
            'filter_usage': overview['query_analysis']['filter_usage']
        }
