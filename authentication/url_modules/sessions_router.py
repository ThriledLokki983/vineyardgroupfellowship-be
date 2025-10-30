"""
Session management URL router configuration.

This module provides RESTful URL routing for session management endpoints
using DRF routers for proper CRUD operations on sessions.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import the DeviceManagementViewSet from profiles app since it contains
# the advanced session management functionality
from profiles.views import DeviceManagementViewSet

app_name = 'sessions_router'

# Create router for session management
router = DefaultRouter()
router.register(r'', DeviceManagementViewSet, basename='sessions')

urlpatterns = [
    # RESTful session management routes
    # This will create:
    # GET /sessions/ - List all sessions
    # GET /sessions/{id}/ - Retrieve specific session
    # PUT /sessions/{id}/ - Update session
    # PATCH /sessions/{id}/ - Partial update session
    # DELETE /sessions/{id}/ - Delete session
    # POST /sessions/{id}/terminate/ - Custom action to terminate session
    # POST /sessions/{id}/revoke_device/ - Custom action to revoke device
    # GET /sessions/analytics/ - Custom action for analytics
    # GET /sessions/current/ - Custom action for current session
    # POST /sessions/cleanup_old/ - Custom action to cleanup old sessions
    # POST /sessions/revoke_all/ - Custom action to revoke all devices
    # POST /sessions/terminate_all/ - Custom action to terminate all sessions
    path('', include(router.urls)),
]
