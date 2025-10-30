"""
URL configuration for monitoring app.

Provides endpoints for:
- Health checks for container orchestration
- Performance metrics for monitoring dashboards
- System status and real-time metrics
- Search performance monitoring
- Admin analytics dashboard
"""

from django.urls import path, include
from . import views
from .search_monitoring_views import (
    SearchPerformanceDashboardView,
    CacheManagementView,
    SearchAnalyticsView,
    SearchOptimizationInsightsView,
    SearchVisualizationDataView
)
from .analytics_dashboard_views import (
    AdminDashboardOverviewView,
    GroupAnalyticsDetailView,
    UserEngagementAnalyticsView,
    SystemHealthAnalyticsView
)
from .realtime_performance_views import (
    RealTimePerformanceDashboardView,
    SystemHealthCheckView,
    PerformanceMetricsHistoryView
)
from .content_moderation_views import (
    ContentModerationDashboardView,
    ModerationQueueView,
    CommunityHealthView
)
from .user_engagement_views import (
    UserEngagementDetailView,
    IndividualUserAnalyticsView,
    UserRetentionAnalyticsView
)
from .group_health_views import (
    GroupHealthDashboardView,
    IndividualGroupHealthView,
    GroupHealthRankingsView
)
from .predictive_analytics_views import (
    PredictiveAnalyticsDashboardView,
    ChurnPredictionView,
    GrowthForecastView
)

app_name = 'monitoring'

urlpatterns = [
    # Health check endpoints (no authentication required)
    path('health/', views.health_check, name='health-check'),
    # Kubernetes convention
    path('healthz/', views.health_check, name='health-check-k8s'),
    path('ready/', views.readiness_check, name='readiness-check'),

    # Performance metrics endpoints (admin authentication required)
    path('metrics/', views.performance_metrics, name='performance-metrics'),
    path('metrics/endpoints/', views.endpoint_metrics, name='endpoint-metrics'),
    path('metrics/realtime/', views.real_time_metrics, name='realtime-metrics'),
    path('metrics/clear/', views.clear_metrics, name='clear-metrics'),

    # Search performance monitoring (admin only)
    path('search/dashboard/', SearchPerformanceDashboardView.as_view(),
         name='search-dashboard'),
    path('search/cache/', CacheManagementView.as_view(), name='cache-management'),
    path('search/analytics/', SearchAnalyticsView.as_view(),
         name='search-analytics'),
    path('search/optimization/', SearchOptimizationInsightsView.as_view(),
         name='search-optimization'),
    path('search/visualization/', SearchVisualizationDataView.as_view(),
         name='search-visualization'),

    # Admin analytics dashboard (Phase 5)
    path('admin/dashboard/', AdminDashboardOverviewView.as_view(),
         name='admin-dashboard'),
    path('admin/groups/<int:group_id>/',
         GroupAnalyticsDetailView.as_view(), name='group-analytics'),
    path('admin/engagement/', UserEngagementAnalyticsView.as_view(),
         name='engagement-analytics'),
    path('admin/health/', SystemHealthAnalyticsView.as_view(), name='system-health'),

    # Real-time performance monitoring (Phase 5)
    path('realtime/dashboard/', RealTimePerformanceDashboardView.as_view(),
         name='realtime-dashboard'),
    path('realtime/health/', SystemHealthCheckView.as_view(),
         name='realtime-health'),
    path('realtime/history/', PerformanceMetricsHistoryView.as_view(),
         name='performance-history'),

    # Content moderation dashboard (Phase 5)
    path('moderation/dashboard/', ContentModerationDashboardView.as_view(),
         name='moderation-dashboard'),
    path('moderation/queue/', ModerationQueueView.as_view(),
         name='moderation-queue'),
    path('moderation/health/', CommunityHealthView.as_view(),
         name='community-health'),

    # User engagement analytics (Phase 5)
    path('engagement/dashboard/', UserEngagementDetailView.as_view(),
         name='user-engagement-dashboard'),
    path('engagement/users/<int:user_id>/', IndividualUserAnalyticsView.as_view(),
         name='individual-user-analytics'),
    path('engagement/retention/', UserRetentionAnalyticsView.as_view(),
         name='user-retention-analytics'),

    # Group health analytics (Phase 5)
    path('groups/health/dashboard/', GroupHealthDashboardView.as_view(),
         name='group-health-dashboard'),
    path('groups/health/<int:group_id>/', IndividualGroupHealthView.as_view(),
         name='individual-group-health'),
    path('groups/health/rankings/', GroupHealthRankingsView.as_view(),
         name='group-health-rankings'),

    # Predictive analytics (Phase 5)
    path('predictive/dashboard/', PredictiveAnalyticsDashboardView.as_view(),
         name='predictive-analytics-dashboard'),
    path('predictive/churn/', ChurnPredictionView.as_view(),
         name='churn-prediction'),
    path('predictive/growth/', GrowthForecastView.as_view(),
         name='growth-forecast'),
]
