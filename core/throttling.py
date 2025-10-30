"""
Custom throttling classes for Vineyard Group Fellowship platform.

This module contains DRF throttling classes for:
- Authentication endpoint protection
- Rate limiting for security-sensitive operations
- Recovery-specific rate controls
- Enhanced endpoint-specific throttling
- Dynamic throttling based on admin settings
"""

import sys
from rest_framework.throttling import UserRateThrottle as DRFUserRateThrottle, AnonRateThrottle as DRFAnonRateThrottle


class DynamicThrottleMixin:
    """Mixin that makes throttles respect admin settings."""

    def allow_request(self, request, view):
        """Check admin settings before applying throttling."""

        # Import here to avoid circular imports
        from core.utils import SettingsManager

        # Global throttling disable
        if not SettingsManager.is_throttling_enabled():
            return True

        # Admin user bypass
        if (request.user and request.user.is_authenticated and
            request.user.is_superuser and
                SettingsManager.bypass_throttling_for_admin()):
            return True

        # Apply normal throttling with possible rate modification
        return super().allow_request(request, view)

    def get_rate(self):
        """Get rate with possible multiplier applied."""
        base_rate = super().get_rate()

        if not base_rate:
            return base_rate

        # Import here to avoid circular imports
        from core.utils import SettingsManager

        # Check for specific override for this throttle scope
        override_key = f'{self.scope}_rate_limit_override'
        override = SettingsManager.get_setting(override_key, None, 'string')
        if override and override.strip():
            return override

        # Apply global multiplier
        multiplier = SettingsManager.get_rate_limit_multiplier()
        if multiplier != 1.0:
            # Parse the rate and apply multiplier
            try:
                rate_parts = base_rate.split('/')
                if len(rate_parts) == 2:
                    number = int(rate_parts[0])
                    period = rate_parts[1]
                    new_number = int(number * multiplier)
                    return f'{new_number}/{period}'
            except (ValueError, IndexError):
                pass

        return base_rate


class TestAwareThrottle:
    """
    Mixin to disable throttling during tests.
    """

    def allow_request(self, request, view):
        # Disable throttling during tests
        if 'test' in sys.argv:
            return True
        return super().allow_request(request, view)

    def get_rate(self):
        # Return a dummy rate during tests to avoid errors
        if 'test' in sys.argv:
            return "1000/min"
        return super().get_rate()


# Test-aware versions of standard DRF throttles
class UserRateThrottle(DRFUserRateThrottle):
    """Test-aware version of DRF UserRateThrottle."""
    scope = 'user'

    def allow_request(self, request, view):
        # Disable throttling during tests
        if 'test' in sys.argv:
            return True
        return super().allow_request(request, view)

    def get_rate(self):
        # Return a dummy rate during tests to avoid errors
        if 'test' in sys.argv:
            return "1000/min"
        return super().get_rate()


class AnonRateThrottle(DRFAnonRateThrottle):
    """Test-aware version of DRF AnonRateThrottle."""
    scope = 'anon'

    def allow_request(self, request, view):
        # Disable throttling during tests
        if 'test' in sys.argv:
            return True
        return super().allow_request(request, view)

    def get_rate(self):
        # Return a dummy rate during tests to avoid errors
        if 'test' in sys.argv:
            return "1000/min"
        return super().get_rate()


class AuthenticationRateThrottle(AnonRateThrottle, TestAwareThrottle):
    """
    Throttle for authentication endpoints (login, etc.)

    More restrictive than standard anonymous throttle to prevent
    brute force attacks.
    """
    scope = 'auth'


class RegistrationRateThrottle(AnonRateThrottle, TestAwareThrottle):
    """
    Throttle for user registration.

    Prevents automated account creation while allowing
    legitimate users to register.
    """
    scope = 'registration'


class PasswordResetRateThrottle(AnonRateThrottle, TestAwareThrottle):
    """
    Throttle for password reset requests.

    Prevents email enumeration and spam while allowing
    legitimate password reset requests.
    """
    scope = 'password_reset'


class EmailVerificationRateThrottle(UserRateThrottle, TestAwareThrottle):
    """
    Throttle for email verification attempts.
    Uses user-based throttling to prevent abuse per account.
    """
    scope = 'email_verification'


class LoginRateThrottle(AnonRateThrottle, TestAwareThrottle):
    """
    Specific throttle for login attempts.

    More restrictive than general auth throttle to prevent
    brute force attacks on login endpoint specifically.
    """
    scope = 'login'


class TokenRefreshRateThrottle(AnonRateThrottle, TestAwareThrottle):
    """
    Throttle for JWT token refresh requests.

    Allows reasonable refresh frequency while preventing
    token refresh abuse.
    """
    scope = 'token_refresh'


class EmailVerificationConfirmRateThrottle(AnonRateThrottle, TestAwareThrottle):
    """
    Throttle for email verification confirmation (via link).

    IP-based throttling for verification confirmations to prevent
    verification link abuse.
    """
    scope = 'email_verification_confirm'


class PasswordResetConfirmRateThrottle(AnonRateThrottle, TestAwareThrottle):
    """
    Throttle for password reset confirmation.

    IP-based throttling for password reset confirmations.
    """
    scope = 'password_reset_confirm'


class DeviceManagementRateThrottle(UserRateThrottle, TestAwareThrottle):
    """
    Throttle for device/session management operations.
    """
    scope = 'device_management'


class ContentModerationRateThrottle(UserRateThrottle, TestAwareThrottle):
    """
    Throttle for content creation and moderation actions.
    """
    scope = 'content_moderation'


# ============================================================================
# DYNAMIC THROTTLE CLASSES (Admin-Controllable)
# ============================================================================

class DynamicLoginRateThrottle(DynamicThrottleMixin, LoginRateThrottle):
    """Login throttle that respects admin settings."""
    pass


class DynamicRegistrationRateThrottle(DynamicThrottleMixin, RegistrationRateThrottle):
    """Registration throttle that respects admin settings."""
    pass


class DynamicAnonRateThrottle(DynamicThrottleMixin, AnonRateThrottle):
    """Anonymous throttle that respects admin settings."""
    pass


class DynamicUserRateThrottle(DynamicThrottleMixin, UserRateThrottle):
    """User throttle that respects admin settings."""
    pass


class DynamicAuthenticationRateThrottle(DynamicThrottleMixin, AuthenticationRateThrottle):
    """Authentication throttle that respects admin settings."""
    pass


class DynamicPasswordResetRateThrottle(DynamicThrottleMixin, PasswordResetRateThrottle):
    """Password reset throttle that respects admin settings."""
    pass


class DynamicTokenRefreshRateThrottle(DynamicThrottleMixin, TokenRefreshRateThrottle):
    """Token refresh throttle that respects admin settings."""
    pass


class DynamicEmailVerificationRateThrottle(DynamicThrottleMixin, EmailVerificationRateThrottle):
    """Email verification throttle that respects admin settings."""
    pass
