"""
URL configuration for vineyard_group_fellowship project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'),
         name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API Routes
    path('api/v1/auth/', include('authentication.urls')),
    path('api/v1/sessions/', include('authentication.url_modules.sessions_router')),
    path('api/v1/profiles/', include('profiles.urls')),
    path('api/v1/privacy/', include('privacy.urls')),
    path('api/v1/monitoring/', include('monitoring.urls')),
    path('api/v1/security/', include('core.urls.security', namespace='security-api')),

    # ================================================================
    # Management endpoints (production only)
    # ================================================================
    path('api/v1/management/', include('core.urls.management')),

    # ================================================================
    # Security Headers and Monitoring
    # ================================================================
    path('', include('core.urls.security', namespace='security-core')),
    path('api/v1/health/', include('authentication.url_modules.health')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
