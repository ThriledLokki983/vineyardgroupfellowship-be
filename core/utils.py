"""
Utility functions for Vineyard Group Fellowship application.

Common helper functions used across the project.
"""

import re
import uuid
from typing import Optional, Dict, Any
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class SettingsManager:
    """Centralized settings management with caching and environment safety."""

    CACHE_TIMEOUT = 300  # 5 minutes

    @classmethod
    def get_setting(cls, key: str, default: Any = None, setting_type: str = 'string') -> Any:
        """
        Get a setting value with caching and fallbacks.

        Args:
            key: Setting key to retrieve
            default: Default value if setting not found
            setting_type: Expected type for validation

        Returns:
            Parsed setting value or default
        """
        # Check cache first
        cache_key = f'system_setting_{key}'
        cached_value = cache.get(cache_key)

        if cached_value is not None:
            return cached_value

        try:
            # Import here to avoid circular imports
            from core.models import SystemSetting

            setting = SystemSetting.objects.filter(
                key=key,
                is_active=True
            ).first()

            if setting:
                # Check environment restriction
                current_env = getattr(settings, 'ENVIRONMENT', 'development')
                if (setting.environment_restriction != 'any' and
                        setting.environment_restriction != current_env):
                    logger.warning(
                        f"Setting {key} restricted to {setting.environment_restriction}, "
                        f"current environment is {current_env}. Using default."
                    )
                    cache.set(cache_key, default, cls.CACHE_TIMEOUT)
                    return default

                value = setting.get_parsed_value()
                cache.set(cache_key, value, cls.CACHE_TIMEOUT)
                return value

        except Exception as e:
            logger.error(f"Error retrieving setting {key}: {e}")

        # Fallback to default
        cache.set(cache_key, default, cls.CACHE_TIMEOUT)
        return default

    @classmethod
    def is_throttling_enabled(cls) -> bool:
        """Check if API throttling is enabled."""
        return cls.get_setting('throttling_enabled', True, 'boolean')

    @classmethod
    def get_rate_limit_multiplier(cls) -> float:
        """Get the rate limit multiplier for testing."""
        return cls.get_setting('rate_limit_multiplier', 1.0, 'float')

    @classmethod
    def is_csrf_protection_enabled(cls) -> bool:
        """Check if CSRF protection is enabled."""
        return cls.get_setting('csrf_protection_enabled', True, 'boolean')

    @classmethod
    def bypass_throttling_for_admin(cls) -> bool:
        """Check if admin users should bypass throttling."""
        return cls.get_setting('bypass_throttling_for_admin', False, 'boolean')

    @classmethod
    def get_login_rate_override(cls) -> Optional[str]:
        """Get login rate limit override (e.g., '1000/hour')."""
        return cls.get_setting('login_rate_limit_override', None, 'string')

    @classmethod
    def clear_cache(cls):
        """Clear all settings cache."""
        # Get all settings keys and clear their cache
        try:
            from core.models import SystemSetting
            for setting in SystemSetting.objects.all():
                cache.delete(f'system_setting_{setting.key}')
            cache.delete('all_system_settings')
        except Exception as e:
            logger.error(f"Error clearing settings cache: {e}")


def generate_secure_token():
    """Generate a cryptographically secure random token."""
    return str(uuid.uuid4()).replace('-', '')


def normalize_email(email: str) -> str:
    """
    Normalize email address to lowercase and strip whitespace.

    Args:
        email: Email address to normalize

    Returns:
        str: Normalized email address
    """
    if not email:
        return email
    return email.lower().strip()


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength beyond Django's built-in validators.

    Args:
        password: Password to validate

    Returns:
        dict: Validation result with 'is_valid' boolean and 'errors' list
    """
    errors = []

    # Length check (additional to Django's validator)
    if len(password) < 12:
        errors.append("Password must be at least 12 characters long.")

    # Character variety checks
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter.")

    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter.")

    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number.")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character.")

    # Common patterns to avoid
    common_patterns = [
        r'(.)\1{2,}',  # Three or more repeated characters
        r'(123|234|345|456|567|678|789|890)',  # Sequential numbers
        # Sequential letters
        r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',
    ]

    for pattern in common_patterns:
        if re.search(pattern, password.lower()):
            errors.append(
                "Password contains common patterns that should be avoided.")
            break

    return {
        'is_valid': len(errors) == 0,
        'errors': errors
    }


def calculate_days_between(start_date: datetime, end_date: Optional[datetime] = None) -> int:
    """
    Calculate days between two dates.

    Args:
        start_date: Start date
        end_date: End date (defaults to now)

    Returns:
        int: Number of days between dates
    """
    if end_date is None:
        end_date = timezone.now()

    if hasattr(start_date, 'date'):
        start_date = start_date.date()
    if hasattr(end_date, 'date'):
        end_date = end_date.date()

    return (end_date - start_date).days


def format_duration(days: int) -> str:
    """
    Format duration in days to human-readable string.

    Args:
        days: Number of days

    Returns:
        str: Formatted duration string
    """
    if days < 0:
        return "Invalid duration"
    elif days == 0:
        return "Less than a day"
    elif days == 1:
        return "1 day"
    elif days < 7:
        return f"{days} days"
    elif days < 30:
        weeks = days // 7
        remaining_days = days % 7
        if weeks == 1:
            week_str = "1 week"
        else:
            week_str = f"{weeks} weeks"

        if remaining_days == 0:
            return week_str
        elif remaining_days == 1:
            return f"{week_str}, 1 day"
        else:
            return f"{week_str}, {remaining_days} days"
    elif days < 365:
        months = days // 30
        remaining_days = days % 30
        if months == 1:
            month_str = "1 month"
        else:
            month_str = f"{months} months"

        if remaining_days < 7:
            return month_str
        else:
            weeks = remaining_days // 7
            if weeks == 1:
                return f"{month_str}, 1 week"
            else:
                return f"{month_str}, {weeks} weeks"
    else:
        years = days // 365
        remaining_days = days % 365
        if years == 1:
            year_str = "1 year"
        else:
            year_str = f"{years} years"

        if remaining_days < 30:
            return year_str
        else:
            months = remaining_days // 30
            if months == 1:
                return f"{year_str}, 1 month"
            else:
                return f"{year_str}, {months} months"


def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input by removing potentially harmful content.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length

    Returns:
        str: Sanitized text
    """
    if not text:
        return ""

    # Convert to string if not already
    text = str(text)

    # Remove potential script tags and other harmful content
    text = re.sub(r'<script[^>]*>.*?</script>', '',
                  text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<iframe[^>]*>.*?</iframe>', '',
                  text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<svg[^>]*>.*?</svg>', '', text,
                  flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<img[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<div[^>]*onclick[^>]*>.*?</div>', '',
                  text, flags=re.IGNORECASE | re.DOTALL)

    # Remove javascript protocols and event handlers
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    text = re.sub(r'onerror\s*=', '', text, flags=re.IGNORECASE)
    text = re.sub(r'onload\s*=', '', text, flags=re.IGNORECASE)
    text = re.sub(r'onclick\s*=', '', text, flags=re.IGNORECASE)

    # Remove HTML tags entirely for user input fields
    text = re.sub(r'<[^>]+>', '', text)

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length].strip()

    return text.strip()


def get_client_ip(request) -> Optional[str]:
    """
    Get client IP address from request, handling proxies.

    Args:
        request: Django request object

    Returns:
        str: Client IP address or None
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP in the chain
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    return ip


def is_safe_redirect_url(url: str, allowed_hosts: list = None) -> bool:
    """
    Check if URL is safe for redirects (prevents open redirect attacks).

    Args:
        url: URL to check
        allowed_hosts: List of allowed hosts

    Returns:
        bool: True if URL is safe for redirects
    """
    if not url:
        return False

    # Relative URLs are generally safe
    if url.startswith('/') and not url.startswith('//'):
        return True

    # Check against allowed hosts if provided
    if allowed_hosts:
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return parsed.netloc in allowed_hosts
        except Exception:
            return False

    return False
