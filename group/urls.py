"""
Group app URL configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import GroupViewSet

router = DefaultRouter()
router.register(r'', GroupViewSet, basename='group')

app_name = 'group'

urlpatterns = [
    path('', include(router.urls)),
]
