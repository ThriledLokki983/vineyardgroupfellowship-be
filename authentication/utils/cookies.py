"""
Cookie management utilities for JWT refresh tokens.

Provides reusable functions for setting, reading, and clearing
httpOnly cookies for secure token management.

Security Features:
- HttpOnly: Prevents JavaScript access (XSS protection)
- Secure: HTTPS only in production
- SameSite=Lax: CSRF protection while allowing navigation
- Token Rotation: New refresh token issued on each refresh
"""

from django.conf import settings
from django.http import HttpResponse
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def set_refresh_token_cookie(
    response: HttpResponse,
    refresh_token: str,
    max_age: Optional[int] = None
) -> HttpResponse:
    """
    Set refresh token as httpOnly cookie on response.

    This function sets the JWT refresh token as an httpOnly cookie,
    making it inaccessible to JavaScript and providing XSS protection.

    Args:
        response: Django HttpResponse object to attach cookie to
        refresh_token: JWT refresh token string
        max_age: Cookie max age in seconds (defaults to settings)

    Returns:
        Modified response with cookie set

    Example:
        >>> response = Response({'access': str(access_token)})
        >>> response = set_refresh_token_cookie(response, str(refresh_token))
    """
    if max_age is None:
        max_age = getattr(
            settings,
            'REFRESH_TOKEN_COOKIE_MAX_AGE',
            14 * 24 * 60 * 60  # 14 days default
        )

    cookie_name = getattr(
        settings,
        'REFRESH_TOKEN_COOKIE_NAME',
        'refresh_token'
    )

    # Get security settings from configuration
    httponly = getattr(settings, 'REFRESH_TOKEN_COOKIE_HTTPONLY', True)
    secure = getattr(settings, 'REFRESH_TOKEN_COOKIE_SECURE', True)
    samesite = getattr(settings, 'REFRESH_TOKEN_COOKIE_SAMESITE', 'Lax')
    path = getattr(settings, 'REFRESH_TOKEN_COOKIE_PATH', '/')

    response.set_cookie(
        key=cookie_name,
        value=refresh_token,
        max_age=max_age,
        httponly=httponly,
        secure=secure,
        samesite=samesite,
        path=path,
    )

    logger.debug(
        f"Refresh token cookie set: {cookie_name} "
        f"(httponly={httponly}, secure={secure}, samesite={samesite})"
    )

    return response


def get_refresh_token_from_cookie(request) -> Optional[str]:
    """
    Extract refresh token from request cookies.

    This function safely retrieves the JWT refresh token from the
    httpOnly cookie if present.

    Args:
        request: Django HttpRequest object

    Returns:
        Refresh token string or None if not found

    Example:
        >>> token = get_refresh_token_from_cookie(request)
        >>> if token:
        >>>     refresh = RefreshToken(token)
    """
    cookie_name = getattr(
        settings,
        'REFRESH_TOKEN_COOKIE_NAME',
        'refresh_token'
    )

    token = request.COOKIES.get(cookie_name)

    if token:
        logger.debug(f"Refresh token found in cookie: {cookie_name}")
    else:
        logger.debug(f"No refresh token in cookie: {cookie_name}")

    return token


def clear_refresh_token_cookie(response: HttpResponse) -> HttpResponse:
    """
    Clear refresh token cookie from response.

    This function removes the refresh token cookie by setting it with
    an empty value and max_age=0, effectively deleting it from the browser.

    Args:
        response: Django HttpResponse object

    Returns:
        Modified response with cookie cleared

    Example:
        >>> response = Response({'message': 'Logged out successfully'})
        >>> response = clear_refresh_token_cookie(response)
    """
    cookie_name = getattr(
        settings,
        'REFRESH_TOKEN_COOKIE_NAME',
        'refresh_token'
    )

    # Delete cookie by setting empty value and max_age=0
    response.delete_cookie(
        key=cookie_name,
        path=getattr(settings, 'REFRESH_TOKEN_COOKIE_PATH', '/'),
        samesite=getattr(settings, 'REFRESH_TOKEN_COOKIE_SAMESITE', 'Lax'),
    )

    logger.debug(f"Refresh token cookie cleared: {cookie_name}")

    return response


def get_refresh_token_from_request(request) -> Optional[str]:
    """
    Get refresh token from request (header, cookie, or body).

    Supports multiple token delivery methods for web and mobile clients.
    
    Priority:
        1. X-Refresh-Token header (mobile apps - most secure for native apps)
        2. Cookie (web browsers - secure with httpOnly)
        3. Request body (legacy method, for backward compatibility)

    Args:
        request: Django HttpRequest object

    Returns:
        Refresh token string or None

    Example:
        >>> token = get_refresh_token_from_request(request)
        >>> if not token:
        >>>     raise ValidationError("No refresh token provided")
    """
    # First try X-Refresh-Token header (mobile apps)
    token = request.headers.get('X-Refresh-Token')
    if token:
        logger.debug("Using refresh token from X-Refresh-Token header (mobile client)")
        return token
    
    # Then try cookie (web browsers - more secure)
    token = get_refresh_token_from_cookie(request)
    if token:
        logger.debug("Using refresh token from cookie (web client)")
        return token

    # Fallback to body (old method) for backward compatibility
    if hasattr(request, 'data') and 'refresh' in request.data:
        token = request.data.get('refresh')
        logger.debug("Using refresh token from request body (legacy method)")
        logger.warning(
            "Refresh token sent in request body. "
            "Please migrate to cookie-based or header-based authentication for better security."
        )
        return token

    logger.warning("No refresh token found in header, cookie, or body")
    return None


def set_csrf_cookie(response: HttpResponse) -> HttpResponse:
    """
    Set CSRF token cookie for frontend.

    Args:
        response: Django HttpResponse object

    Returns:
        Modified response with CSRF cookie set
    """
    from django.middleware.csrf import get_token
    from django.http import HttpRequest

    # For setting CSRF cookie, we need a request object
    # This is typically done in middleware or views where request is available
    # For now, we'll set a basic CSRF cookie configuration

    response.set_cookie(
        'csrftoken',
        '',  # Will be set by Django's CSRF middleware
        httponly=False,  # CSRF token needs to be readable by JavaScript
        secure=getattr(settings, 'CSRF_COOKIE_SECURE', False),
        samesite='Lax'
    )

    return response


def clear_csrf_cookie(response: HttpResponse) -> HttpResponse:
    """
    Clear CSRF token cookie.

    Args:
        response: Django HttpResponse object

    Returns:
        Modified response with CSRF cookie cleared
    """
    response.delete_cookie('csrftoken')
    return response


def get_csrf_token_from_cookie(request) -> Optional[str]:
    """
    Get CSRF token from cookie.

    Args:
        request: Django request object

    Returns:
        CSRF token string or None
    """
    return request.COOKIES.get('csrftoken')


def set_security_headers(response: HttpResponse) -> HttpResponse:
    """
    Set security headers on response.

    Args:
        response: Django HttpResponse object

    Returns:
        Modified response with security headers set
    """
    # Set various security headers
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Frame-Options'] = 'DENY'
    response['X-XSS-Protection'] = '1; mode=block'
    response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Only set HSTS in production with HTTPS
    if getattr(settings, 'SECURE_SSL_REDIRECT', False):
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response


def create_secure_response(data: dict, refresh_token: str = None) -> HttpResponse:
    """
    Create a secure response with authentication tokens.

    Args:
        data: Response data dictionary
        refresh_token: Optional refresh token to set as cookie

    Returns:
        HttpResponse with security headers and cookies
    """
    from django.http import JsonResponse

    response = JsonResponse(data)

    # Set security headers
    response = set_security_headers(response)

    # Set refresh token cookie if provided
    if refresh_token:
        response = set_refresh_token_cookie(response, refresh_token)

    # Set CSRF cookie
    response = set_csrf_cookie(response)

    return response


def clear_all_auth_cookies(response: HttpResponse) -> HttpResponse:
    """
    Clear all authentication-related cookies.

    Args:
        response: Django HttpResponse object

    Returns:
        Modified response with all auth cookies cleared
    """
    response = clear_refresh_token_cookie(response)
    response = clear_csrf_cookie(response)

    return response
