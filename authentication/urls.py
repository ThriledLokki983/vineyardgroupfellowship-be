"""
Authentication Core URL Configuration.

This module provides URL patterns for core authentication operations:
- User registration and login
- Password management
- Email verification
- JWT token management

Resource-specific endpoints (profiles, GDPR, sessions, security) are handled
by separate modules in url_modules/ to maintain clean resource-based URL structure.
"""

from django.urls import path, include

from .views import (
    UserRegistrationView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    EmailVerificationView,
    EmailVerificationResendView,
    ExchangeTokenView,
    TokenVerifyView,
    RefreshTokenView,
    HealthCheckView,
)
from .csrf_views import csrf_token_api

app_name = 'authentication'

urlpatterns = [
    # ================================================================
    # Core Authentication Operations
    # ================================================================

    # CSRF Token for SPA
    path('csrf/', csrf_token_api, name='csrf-token'),

    # Health Check
    path('health/', HealthCheckView, name='health-check'),

    # User registration
    path('register/', UserRegistrationView, name='register'),

    # User login/logout
    path('login/', LoginView, name='login'),
    path('logout/', LogoutView, name='logout'),

    # Password Management
    path('password/change/', PasswordChangeView, name='password-change'),
    path('password/reset/', PasswordResetRequestView,
         name='password-reset-request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(),
         name='password-reset-confirm'),
    path('password/reset/confirm/<str:uidb64>/<str:token>/',
         PasswordResetConfirmView.as_view(), name='password-reset-confirm-link'),

    # Email Verification
    path('email/verify/', EmailVerificationView.as_view(), name='email-verify'),
    path('email/verify/<str:uidb64>/<str:token>/',
         EmailVerificationView.as_view(), name='email-verify-link'),
    path('email/resend/', EmailVerificationResendView.as_view(), name='email-resend'),

    # Token Exchange (for secure authentication flows)
    path('exchange-token/', ExchangeTokenView.as_view(), name='exchange-token'),

    # Token Management
    path('token/refresh/', RefreshTokenView.as_view(), name='token-refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token-verify'),

    # Session Management URLs
    path('sessions/', include('authentication.url_modules.sessions', namespace='sessions')),
]
