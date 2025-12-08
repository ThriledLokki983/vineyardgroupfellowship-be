"""
Mobile client detection utilities.

This module provides utilities to detect if a request is coming from a mobile
app client vs a web browser client, enabling conditional response formatting.
"""

import logging
import structlog
from typing import Optional
from django.http import HttpRequest

logger = structlog.get_logger(__name__)


def is_mobile_client(request: HttpRequest) -> bool:
    """
    Detect if the request is from a mobile app client.
    
    Mobile clients are identified by:
    1. Explicit X-Client-Type header set to 'mobile' (primary method)
    2. User-Agent patterns indicating React Native or mobile app (fallback)
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        bool: True if request is from mobile app, False if from web browser
        
    Examples:
        >>> # Mobile app request
        >>> request.headers['X-Client-Type'] = 'mobile'
        >>> is_mobile_client(request)
        True
        
        >>> # Web browser request
        >>> is_mobile_client(request)
        False
    """
    # Primary detection: Explicit X-Client-Type header
    client_type = request.headers.get('X-Client-Type', '').lower()
    if client_type == 'mobile':
        logger.debug(
            "Mobile client detected via X-Client-Type header",
            path=request.path,
            method=request.method
        )
        return True
    
    # Fallback: User-Agent pattern detection
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    # Mobile app indicators in User-Agent
    mobile_indicators = [
        'vineyardgf',           # Our mobile app identifier
        'vineyard-mobile',      # Alternative app identifier
        'react-native',         # React Native framework
        'expo',                 # Expo framework
        'mobile-app',           # Generic mobile app indicator
    ]
    
    for indicator in mobile_indicators:
        if indicator in user_agent:
            logger.debug(
                "Mobile client detected via User-Agent pattern",
                path=request.path,
                method=request.method,
                user_agent_snippet=user_agent[:100]
            )
            return True
    
    # Default: Not a mobile client
    logger.debug(
        "Web client detected",
        path=request.path,
        method=request.method
    )
    return False


def get_client_type(request: HttpRequest) -> str:
    """
    Get a string representation of the client type.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        str: 'mobile' or 'web'
        
    Example:
        >>> get_client_type(request)
        'mobile'
    """
    return 'mobile' if is_mobile_client(request) else 'web'


def should_use_cookie_auth(request: HttpRequest) -> bool:
    """
    Determine if this request should use cookie-based authentication.
    
    Web clients use httpOnly cookies for refresh tokens (XSS protection).
    Mobile clients use request headers (no cookie support in native apps).
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        bool: True if should use cookies (web), False if should use headers (mobile)
        
    Example:
        >>> should_use_cookie_auth(request)
        False  # Mobile client - use headers
    """
    return not is_mobile_client(request)


def log_client_info(request: HttpRequest, event: str, **extra_context) -> None:
    """
    Log client information for monitoring and debugging.
    
    Includes client type, platform info, and custom context.
    
    Args:
        request: Django HttpRequest object
        event: Event description
        **extra_context: Additional context to log
        
    Example:
        >>> log_client_info(request, "authentication_success", user_id="123")
    """
    client_type = get_client_type(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    
    logger.info(
        event,
        client_type=client_type,
        user_agent=user_agent[:200],  # Truncate long user agents
        ip_address=get_client_ip(request),
        path=request.path,
        **extra_context
    )


def get_client_ip(request: HttpRequest) -> Optional[str]:
    """
    Get client IP address, handling proxies and load balancers.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        str: Client IP address or None
    """
    # Check for forwarded IP (behind proxy/load balancer)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP in the chain
        return x_forwarded_for.split(',')[0].strip()
    
    # Check for real IP header
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip
    
    # Fallback to remote address
    return request.META.get('REMOTE_ADDR')
