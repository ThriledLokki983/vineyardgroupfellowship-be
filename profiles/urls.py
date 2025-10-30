"""
Profiles URL configuration.
"""

from django.urls import path, include

from .views import (
    UserProfileViewSet,
    ProfilePhotoViewSet,
    profile_completeness_view,
    refresh_completeness_view,
    privacy_settings_view,
    update_privacy_settings_view,
    public_profile_view,
)

app_name = 'profiles'

urlpatterns = [
    # Current user profile management
    path('me/', UserProfileViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update'
    }), name='profile-detail'),

    # Photo management
    path('me/photo/', ProfilePhotoViewSet.as_view({
        'get': 'me'
    }), name='photo-info'),

    path('me/photo/upload/', ProfilePhotoViewSet.as_view({
        'post': 'upload',
        'put': 'upload'
    }), name='photo-upload'),

    path('me/photo/delete/', ProfilePhotoViewSet.as_view({
        'delete': 'delete'
    }), name='photo-delete'),

    # Profile completeness
    path('me/completeness/', profile_completeness_view,
         name='profile-completeness'),
    path('me/completeness/refresh/', refresh_completeness_view,
         name='completeness-refresh'),

    # Privacy settings
    path('me/privacy/', privacy_settings_view, name='privacy-settings'),
    path('me/privacy/update/', update_privacy_settings_view, name='privacy-update'),

    # Public profiles
    path('<int:user_id>/', public_profile_view, name='public-profile'),
]
