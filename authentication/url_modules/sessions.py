"""
Session management URL configuration.
"""

from django.urls import path

from ..view_modules.sessions import (
    list_sessions_view,
    terminate_session_view,
    terminate_all_sessions_view
)

app_name = 'sessions'

urlpatterns = [
    # Session Management
    path('', list_sessions_view, name='list'),
    path('terminate/', terminate_session_view, name='terminate'),
    path('terminate-all/', terminate_all_sessions_view, name='terminate_all'),
]
