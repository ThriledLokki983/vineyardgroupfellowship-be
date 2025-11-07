"""
URL configuration for messaging app.

Maps ViewSets to URL patterns using DRF routers.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DiscussionViewSet,
    CommentViewSet,
    ReactionViewSet,
    FeedViewSet,
    NotificationPreferenceViewSet,
    ContentReportViewSet,
    PrayerRequestViewSet,
    TestimonyViewSet,
    ScriptureViewSet,
)

app_name = 'messaging'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'discussions', DiscussionViewSet, basename='discussion')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'reactions', ReactionViewSet, basename='reaction')
router.register(r'feed', FeedViewSet, basename='feed')
router.register(r'preferences', NotificationPreferenceViewSet,
                basename='preference')
router.register(r'reports', ContentReportViewSet, basename='report')

# Phase 2: Faith Features
router.register(r'prayer-requests', PrayerRequestViewSet,
                basename='prayer-request')
router.register(r'testimonies', TestimonyViewSet, basename='testimony')
router.register(r'scriptures', ScriptureViewSet, basename='scripture')

urlpatterns = [
    path('', include(router.urls)),
]
