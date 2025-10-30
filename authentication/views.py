"""
Authentication views for Vineyard Group Fellowship platform.

This module provides a clean interface for authentication views that have been
organized into logical modules within the view_modules/ directory structure.

Views Organization:
- authentication.py: Core auth (registration, login, logout)
- password.py: Password management (change, reset)
- email.py: Email verification
- tokens.py: JWT token management
- health.py: Health check endpoints

Note: Onboarding-related views are handled by the dedicated onboarding app.
"""

# Import organized authentication views from modules
from .view_modules.authentication import (
    register_view as UserRegistrationView,
    login_view as LoginView,
    logout_view as LogoutView
)

from .view_modules.tokens import (
    RefreshTokenView,
    ExchangeTokenView,
    TokenVerifyView
)

from .view_modules.password import (
    change_password_view as PasswordChangeView,
    password_reset_request_view as PasswordResetRequestView,
    PasswordResetConfirmView
)

from .view_modules.email import (
    EmailVerificationView,
    EmailVerificationResendView
)

from .view_modules.sessions import (
    list_sessions_view as ListSessionsView,
    terminate_session_view as TerminateSessionView,
    terminate_all_sessions_view as TerminateAllSessionsView
)

from .view_modules.health import (
    health_check_view as HealthCheckView
)

# Export all authentication views for module-level imports
__all__ = [
    # Core authentication views
    'UserRegistrationView',
    'LoginView',
    'LogoutView',

    # Password management views
    'PasswordChangeView',
    'PasswordResetRequestView',
    'PasswordResetConfirmView',

    # Email verification views
    'EmailVerificationView',
    'EmailVerificationResendView',

    # Token management views
    'RefreshTokenView',
    'ExchangeTokenView',
    'TokenVerifyView',

    # Session management views
    'ListSessionsView',
    'TerminateSessionView',
    'TerminateAllSessionsView',

    # Health check views
    'HealthCheckView',
]
