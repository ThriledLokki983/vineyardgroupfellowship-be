"""
Minimal URL configuration for monitoring app.

This includes only the core monitoring functionality that doesn't depend
on the groups app. Full functionality will be available once groups app
is implemented.
"""

from django.urls import path
from . import views

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
]