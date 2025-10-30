"""
Timezone utilities for Vineyard Group Fellowship

Provides helper functions for timezone-aware datetime operations,
localization, and frontend integration.
"""

import pytz
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from rest_framework import serializers


class TimezoneAwareDateTimeField(serializers.DateTimeField):
    """
    DRF DateTimeField that automatically converts to user's timezone.

    Usage in serializers:
        created_at = TimezoneAwareDateTimeField(read_only=True)
    """

    def to_representation(self, value):
        """Convert datetime to user's timezone for output."""
        if value is None:
            return None

        # Get user timezone from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user_timezone_object'):
            user_tz = request.user_timezone_object
            if value.tzinfo is None:
                # Assume UTC if no timezone info
                value = pytz.UTC.localize(value)
            # Convert to user's timezone
            value = value.astimezone(user_tz)

        return super().to_representation(value)


def get_user_timezone(request_or_user):
    """
    Get the appropriate timezone for a user or request.

    Args:
        request_or_user: Either a request object or user object

    Returns:
        pytz.timezone object
    """
    # Check if it's a request object (has META attribute)
    if hasattr(request_or_user, 'META'):
        request = request_or_user

        # First check for timezone object set by middleware
        if hasattr(request, 'user_timezone_object'):
            return request.user_timezone_object

        # Then check for timezone string and convert it
        if hasattr(request, 'user_timezone'):
            try:
                return pytz.timezone(request.user_timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                pass

        user = getattr(request, 'user', None)
    else:
        # Assume it's a user object
        user = request_or_user

    # Try to get from user profile
    if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
        try:
            if hasattr(user, 'profile') and hasattr(user.profile, 'timezone'):
                return pytz.timezone(user.profile.timezone)
        except (AttributeError, pytz.exceptions.UnknownTimeZoneError):
            pass

    # Fall back to system default
    return pytz.timezone(getattr(settings, 'TIME_ZONE', 'UTC'))


def now_in_user_timezone(request_or_user):
    """
    Get current datetime in user's timezone.

    Args:
        request_or_user: Either a request object or user object

    Returns:
        datetime object in user's timezone
    """
    user_tz = get_user_timezone(request_or_user)
    return timezone.now().astimezone(user_tz)


def convert_to_user_timezone(dt, request_or_user):
    """
    Convert a datetime to user's timezone.

    Args:
        dt: datetime object to convert
        request_or_user: Either a request object or user object

    Returns:
        datetime object in user's timezone
    """
    if dt is None:
        return None

    user_tz = get_user_timezone(request_or_user)

    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = pytz.UTC.localize(dt)

    return dt.astimezone(user_tz)


def format_datetime_for_user(dt, request_or_user, format_string=None):
    """
    Format datetime in user's timezone with locale-appropriate formatting.

    Args:
        dt: datetime object to format
        request_or_user: Either a request object or user object
        format_string: Optional custom format string

    Returns:
        Formatted datetime string
    """
    if dt is None:
        return None

    user_dt = convert_to_user_timezone(dt, request_or_user)

    if format_string:
        return user_dt.strftime(format_string)

    # Default format with timezone abbreviation
    return user_dt.strftime('%Y-%m-%d %H:%M:%S %Z')


def get_timezone_choices():
    """
    Get list of common timezone choices for forms/serializers.

    Returns:
        List of (timezone_key, display_name) tuples
    """
    common_timezones = [
        # North America
        'America/New_York',
        'America/Chicago',
        'America/Denver',
        'America/Los_Angeles',
        'America/Toronto',
        'America/Vancouver',
        'America/Mexico_City',

        # Europe
        'Europe/London',
        'Europe/Dublin',
        'Europe/Paris',
        'Europe/Berlin',
        'Europe/Rome',
        'Europe/Madrid',
        'Europe/Amsterdam',
        'Europe/Stockholm',
        'Europe/Moscow',

        # Asia Pacific
        'Asia/Tokyo',
        'Asia/Seoul',
        'Asia/Shanghai',
        'Asia/Hong_Kong',
        'Asia/Singapore',
        'Asia/Bangkok',
        'Asia/Kolkata',
        'Asia/Dubai',
        'Australia/Sydney',
        'Australia/Melbourne',
        'Pacific/Auckland',

        # Other
        'Africa/Cairo',
        'Africa/Johannesburg',
        'America/Sao_Paulo',
        'America/Buenos_Aires',
        'UTC',
    ]

    choices = []
    for tz_name in common_timezones:
        try:
            tz = pytz.timezone(tz_name)
            # Create a display name
            display_name = tz_name.replace('_', ' ').replace('/', ' / ')
            choices.append((tz_name, display_name))
        except pytz.exceptions.UnknownTimeZoneError:
            continue

    return sorted(choices, key=lambda x: x[1])


def detect_timezone_from_offset(offset_minutes):
    """
    Detect likely timezone from UTC offset in minutes.

    Args:
        offset_minutes: UTC offset in minutes (e.g., -300 for EST)

    Returns:
        Best guess timezone name or None
    """
    # Common offset to timezone mappings
    offset_map = {
        -480: 'America/Los_Angeles',  # PST
        -420: 'America/Denver',       # MST
        -360: 'America/Chicago',      # CST
        -300: 'America/New_York',     # EST
        0: 'Europe/London',           # GMT
        60: 'Europe/Paris',           # CET
        120: 'Europe/Athens',         # EET
        330: 'Asia/Kolkata',          # IST
        480: 'Asia/Shanghai',         # CST
        540: 'Asia/Tokyo',            # JST
        600: 'Australia/Sydney',      # AEST
        720: 'Pacific/Auckland',      # NZST
    }

    return offset_map.get(offset_minutes)


class TimezoneAwareModelMixin:
    """
    Mixin for Django models to add timezone-aware helper methods.

    Usage:
        class MyModel(TimezoneAwareModelMixin, models.Model):
            created_at = models.DateTimeField(auto_now_add=True)

        # In views:
        obj.created_at_for_user(request)
    """

    def get_datetime_for_user(self, field_name, request_or_user):
        """Get a datetime field converted to user's timezone."""
        dt = getattr(self, field_name)
        return convert_to_user_timezone(dt, request_or_user)

    def format_datetime_for_user(self, field_name, request_or_user, format_string=None):
        """Format a datetime field in user's timezone."""
        dt = getattr(self, field_name)
        return format_datetime_for_user(dt, request_or_user, format_string)


def add_timezone_to_response(response, request):
    """
    Add timezone information to API response headers.

    Args:
        response: DRF Response object
        request: Request object

    Returns:
        Response with timezone headers added
    """
    if hasattr(request, 'user_timezone'):
        response['X-Server-Timezone'] = request.user_timezone
        response['X-Server-UTC-Offset'] = str(
            timezone.now().astimezone(
                pytz.timezone(request.user_timezone)
            ).utcoffset().total_seconds() / 60
        )

    return response
