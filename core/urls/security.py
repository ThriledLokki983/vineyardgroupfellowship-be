"""
Phase 6: Security URL configuration for Vineyard Group Fellowship API.

Defines URL patterns for security monitoring, CSP reporting, and
security management endpoints.
"""

from django.urls import path
from core.security.monitoring import (
    csp_report_view,
    security_status_view,
    security_incident_report_view,
    security_analysis_view,
)

# Import session termination view for security-specific paths
from authentication.view_modules.sessions import terminate_all_sessions_view
from profiles.views import DeviceManagementViewSet
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

# Create a wrapper for terminate_suspicious to make it accessible as a function view


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def terminate_suspicious_sessions_view(request):
    """Security-specific wrapper for terminate suspicious sessions."""
    viewset = DeviceManagementViewSet()
    viewset.request = request
    viewset.format_kwarg = None
    viewset.action = 'terminate_suspicious'
    return viewset.terminate_suspicious(request)


app_name = 'security'

urlpatterns = [
    # Security analysis and monitoring
    path('analysis/', security_analysis_view, name='security-analysis'),

    # CSP violation reporting
    path('csp-report/', csp_report_view, name='csp-report'),

    # Security status monitoring
    path('status/', security_status_view, name='status'),

    # Security incident reporting
    path('incident/', security_incident_report_view, name='incident'),

    # Security-specific session management
    path('sessions/terminate-all/', terminate_all_sessions_view,
         name='terminate-all-sessions'),
    path('sessions/terminate-suspicious/', terminate_suspicious_sessions_view,
         name='terminate-suspicious-sessions'),
]
