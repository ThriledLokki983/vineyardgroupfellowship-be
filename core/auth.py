"""
Custom authentication classes for Vineyard Group Fellowship API.

Implements secure cookie-based JWT authentication for enhanced security.
"""

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT authentication using httpOnly cookies for enhanced security.

    This prevents XSS attacks by storing tokens in httpOnly cookies
    instead of localStorage/sessionStorage.
    """

    def authenticate(self, request):
        """
        Authenticate using JWT token from httpOnly cookie with Phase 4 security enhancements.

        Returns:
            tuple: (user, token) if authentication successful, None otherwise
        """
        # First try standard Authorization header
        header_auth = super().authenticate(request)
        if header_auth is not None:
            user, token = header_auth
            # Validate token is not blacklisted
            if self._is_token_blacklisted(token):
                raise InvalidToken('Token is blacklisted')
            return user, token

        # Fall back to cookie-based authentication
        raw_token = self.get_raw_token_from_cookie(request)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        # Additional validation for blacklisted tokens
        if self._is_token_blacklisted(validated_token):
            raise InvalidToken('Token is blacklisted')

        # Check for token reuse (if this is a refresh token operation)
        if hasattr(request, 'resolver_match') and request.resolver_match:
            view_name = getattr(request.resolver_match, 'view_name', '')
            if 'refresh' in view_name.lower():
                token_jti = validated_token.payload.get('jti')
                user_id = validated_token.payload.get('user_id')
                if token_jti and user_id:
                    from core.utils_package.jwt import EnhancedJWTToken
                    if not EnhancedJWTToken.validate_token_reuse(token_jti, user_id):
                        raise InvalidToken('Token reuse detected')

        return self.get_user(validated_token), validated_token

    def _is_token_blacklisted(self, token) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: Validated JWT token

        Returns:
            True if token is blacklisted
        """
        try:
            from authentication.models import TokenBlacklist
            jti = token.payload.get('jti')
            if jti:
                return TokenBlacklist.is_blacklisted(jti)
        except Exception:
            # If we can't check blacklist, allow the token
            # (fail open for availability)
            pass
        return False

    def get_raw_token_from_cookie(self, request):
        """
        Extract JWT token from httpOnly cookie using Phase 4 enhanced configuration.

        Args:
            request: Django request object

        Returns:
            bytes: Raw token from cookie, None if not found
        """
        # Use Phase 4 enhanced cookie configuration
        cookie_settings = getattr(settings, 'JWT_COOKIE_SETTINGS', {})
        cookie_name = cookie_settings.get(
            'ACCESS_TOKEN_COOKIE_NAME', 'access_token')

        raw_token = request.COOKIES.get(cookie_name)
        if raw_token is None:
            return None

        return raw_token.encode('utf-8')


def set_jwt_cookies(response, user, access_token=None, refresh_token=None):
    """
    Set JWT tokens as httpOnly cookies using Phase 4 enhanced configuration.

    Args:
        response: Django response object
        user: User instance
        access_token: AccessToken instance (optional, will generate if None)
        refresh_token: RefreshToken instance (optional, will generate if None)
    """
    if refresh_token is None:
        refresh_token = RefreshToken.for_user(user)

    if access_token is None:
        access_token = refresh_token.access_token

    # Use enhanced cookie configuration
    cookie_settings = getattr(settings, 'JWT_COOKIE_SETTINGS', {})

    # Base cookie configuration
    base_cookie_config = {
        'httponly': cookie_settings.get('COOKIE_HTTPONLY', True),
        'secure': cookie_settings.get('COOKIE_SECURE', False),
        'samesite': cookie_settings.get('COOKIE_SAMESITE', 'Lax'),
    }

    # Add domain if specified
    if cookie_settings.get('COOKIE_DOMAIN'):
        base_cookie_config['domain'] = cookie_settings['COOKIE_DOMAIN']

    # Set access token cookie
    access_cookie_name = cookie_settings.get(
        'ACCESS_TOKEN_COOKIE_NAME', 'access_token')
    access_cookie_config = base_cookie_config.copy()
    access_cookie_config.update({
        'path': cookie_settings.get('ACCESS_TOKEN_COOKIE_PATH', '/api/v1/'),
        'max_age': cookie_settings.get('ACCESS_TOKEN_COOKIE_MAX_AGE', 10 * 60),
    })

    response.set_cookie(
        access_cookie_name,
        str(access_token),
        **access_cookie_config
    )

    # Set refresh token cookie
    refresh_cookie_name = cookie_settings.get(
        'REFRESH_TOKEN_COOKIE_NAME', 'refresh_token')
    refresh_cookie_config = base_cookie_config.copy()
    refresh_cookie_config.update({
        'path': cookie_settings.get('REFRESH_TOKEN_COOKIE_PATH', '/api/v1/auth/token/'),
        'max_age': cookie_settings.get('REFRESH_TOKEN_COOKIE_MAX_AGE', 14 * 24 * 60 * 60),
    })

    response.set_cookie(
        refresh_cookie_name,
        str(refresh_token),
        **refresh_cookie_config
    )

    return response


def clear_jwt_cookies(response):
    """
    Clear JWT cookies from response using Phase 4 enhanced configuration.

    Args:
        response: Django response object
    """
    # Use enhanced cookie configuration
    cookie_settings = getattr(settings, 'JWT_COOKIE_SETTINGS', {})

    # Clear access token cookie
    access_cookie_name = cookie_settings.get(
        'ACCESS_TOKEN_COOKIE_NAME', 'access_token')
    clear_kwargs = {
        'path': cookie_settings.get('ACCESS_TOKEN_COOKIE_PATH', '/api/v1/'),
        'httponly': cookie_settings.get('COOKIE_HTTPONLY', True),
        'secure': cookie_settings.get('COOKIE_SECURE', False),
        'samesite': cookie_settings.get('COOKIE_SAMESITE', 'Lax'),
    }

    # Add domain if specified
    if cookie_settings.get('COOKIE_DOMAIN'):
        clear_kwargs['domain'] = cookie_settings['COOKIE_DOMAIN']

    response.set_cookie(
        access_cookie_name,
        value='',
        max_age=0,
        **clear_kwargs
    )

    # Clear refresh token cookie
    refresh_cookie_name = cookie_settings.get(
        'REFRESH_TOKEN_COOKIE_NAME', 'refresh_token')
    clear_kwargs['path'] = cookie_settings.get(
        'REFRESH_TOKEN_COOKIE_PATH', '/api/v1/auth/token/')

    response.set_cookie(
        refresh_cookie_name,
        value='',
        max_age=0,
        **clear_kwargs
    )

    return response
