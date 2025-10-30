"""
Timezone Middleware for Vineyard Group Fellowship

Automatically detects and sets the user's timezone based on:
1. User profile timezone preference (if authenticated)
2. Request headers (X-Timezone, Accept-Language)
3. GeoIP detection (optional)
4. Falls back to system default

This ensures all timestamps are displayed in the user's local timezone
while maintaining UTC storage in the database.
"""

import pytz
import logging
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.contrib.gis.geoip2 import GeoIP2
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings


logger = logging.getLogger(__name__)


class TimezoneMiddleware(MiddlewareMixin):
    """
    Middleware to automatically detect and activate user's timezone.

    Timezone Detection Priority:
    1. User profile timezone (authenticated users)
    2. X-Timezone header
    3. X-User-Timezone header
    4. Accept-Language header (country-based)
    5. GeoIP detection (optional)
    6. System default timezone
    """

    def process_request(self, request):
        """Detect and activate user's timezone for this request."""

        # Try to get timezone from various sources
        user_timezone = self._get_timezone_from_sources(request)

        if user_timezone:
            try:
                # Validate and activate the timezone
                tz = pytz.timezone(user_timezone)
                timezone.activate(tz)

                # Store in request for later use
                request.user_timezone = user_timezone
                request.user_timezone_object = tz

                logger.debug(
                    f"Activated timezone: {user_timezone} for request")

            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(
                    f"Invalid timezone '{user_timezone}' detected, using default")
                self._use_default_timezone(request)
        else:
            self._use_default_timezone(request)

    def process_response(self, request, response):
        """Clean up timezone activation after request."""
        # Deactivate timezone to prevent leakage to other requests
        timezone.deactivate()
        return response

    def _get_timezone_from_sources(self, request):
        """Try to determine timezone from various sources in priority order."""

        # 1. User profile timezone (highest priority)
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_tz = self._get_user_profile_timezone(request.user)
            if user_tz:
                return user_tz

        # 2. X-Timezone header (explicit client setting)
        header_tz = request.META.get('HTTP_X_TIMEZONE')
        if header_tz:
            return header_tz

        # 3. X-User-Timezone header (alternative)
        alt_header_tz = request.META.get('HTTP_X_USER_TIMEZONE')
        if alt_header_tz:
            return alt_header_tz

        # 4. Accept-Language header (country-based detection)
        language_tz = self._get_timezone_from_language(request)
        if language_tz:
            return language_tz

        # 5. GeoIP detection (if enabled and available)
        if getattr(settings, 'ENABLE_GEOIP_TIMEZONE', False):
            geoip_tz = self._get_timezone_from_geoip(request)
            if geoip_tz:
                return geoip_tz

        # 6. Fall back to None (will use system default)
        return None

    def _get_user_profile_timezone(self, user):
        """Get timezone from user's profile if available."""
        try:
            if hasattr(user, 'profile') and hasattr(user.profile, 'timezone'):
                return user.profile.timezone
        except Exception as e:
            logger.warning(f"Error getting user timezone: {e}")
        return None

    def _get_timezone_from_language(self, request):
        """Extract timezone from Accept-Language header."""
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')

        # Common language to timezone mappings
        language_timezone_map = {
            # English variants
            'en-US': 'America/New_York',
            'en-GB': 'Europe/London',
            'en-AU': 'Australia/Sydney',
            'en-CA': 'America/Toronto',
            'en-NZ': 'Pacific/Auckland',
            'en-IE': 'Europe/Dublin',

            # Spanish variants
            'es-ES': 'Europe/Madrid',
            'es-MX': 'America/Mexico_City',
            'es-AR': 'America/Buenos_Aires',
            'es-CL': 'America/Buenos_Aires',
            'es-CO': 'America/Sao_Paulo',

            # French variants
            'fr-FR': 'Europe/Paris',
            'fr-CA': 'America/Toronto',
            'fr-BE': 'Europe/Amsterdam',
            'fr-CH': 'Europe/Berlin',

            # German variants
            'de-DE': 'Europe/Berlin',
            'de-AT': 'Europe/Berlin',
            'de-CH': 'Europe/Berlin',

            # Dutch variants
            'nl-NL': 'Europe/Amsterdam',
            'nl-BE': 'Europe/Amsterdam',  # Flemish

            # Italian variants
            'it-IT': 'Europe/Rome',
            'it-CH': 'Europe/Berlin',

            # Portuguese variants
            'pt-BR': 'America/Sao_Paulo',
            'pt-PT': 'Europe/Madrid',

            # Nordic languages
            'sv-SE': 'Europe/Stockholm',  # Swedish
            'no-NO': 'Europe/Stockholm',  # Norwegian
            'da-DK': 'Europe/Stockholm',  # Danish
            'fi-FI': 'Europe/Stockholm',  # Finnish

            # Other European languages
            'ru-RU': 'Europe/Moscow',
            'pl-PL': 'Europe/Berlin',
            'cs-CZ': 'Europe/Berlin',     # Czech
            'hu-HU': 'Europe/Berlin',     # Hungarian
            'sk-SK': 'Europe/Berlin',     # Slovak
            'sl-SI': 'Europe/Berlin',     # Slovenian
            'hr-HR': 'Europe/Berlin',     # Croatian
            'el-GR': 'Europe/Berlin',     # Greek (mapped to Central European)

            # Asian languages
            'ja-JP': 'Asia/Tokyo',
            'ko-KR': 'Asia/Seoul',
            'zh-CN': 'Asia/Shanghai',
            'zh-TW': 'Asia/Taipei',
            'zh-HK': 'Asia/Hong_Kong',
            'hi-IN': 'Asia/Kolkata',
            'th-TH': 'Asia/Bangkok',
            'ar-SA': 'Asia/Dubai',
            'ar-AE': 'Asia/Dubai',
            'ar-EG': 'Africa/Cairo',
        }

        # Parse first language preference
        if accept_language:
            primary_lang = accept_language.split(',')[0].strip()
            return language_timezone_map.get(primary_lang)

        return None

    def _get_timezone_from_geoip(self, request):
        """Get timezone based on client IP using GeoIP2 (optional)."""
        try:
            if not getattr(settings, 'GEOIP_PATH', None):
                return None

            client_ip = self._get_client_ip(request)
            if not client_ip or self._is_private_ip(client_ip):
                return None

            g = GeoIP2()
            country_code = g.country_code(client_ip)

            # Map country codes to timezones (comprehensive mapping)
            country_timezone_map = {
                # North America
                'US': 'America/New_York',        # United States (Eastern)
                'CA': 'America/Toronto',         # Canada (Eastern)
                'MX': 'America/Mexico_City',     # Mexico

                # Europe
                'GB': 'Europe/London',           # United Kingdom
                'IE': 'Europe/Dublin',           # Ireland
                'FR': 'Europe/Paris',            # France
                'DE': 'Europe/Berlin',           # Germany
                'NL': 'Europe/Amsterdam',        # Netherlands
                # Belgium (same as Netherlands)
                'BE': 'Europe/Amsterdam',
                # Luxembourg (same as Netherlands)
                'LU': 'Europe/Amsterdam',
                'IT': 'Europe/Rome',             # Italy
                'ES': 'Europe/Madrid',           # Spain
                # Portugal (same timezone as Spain)
                'PT': 'Europe/Madrid',
                # Switzerland (same as Germany)
                'CH': 'Europe/Berlin',
                'AT': 'Europe/Berlin',           # Austria (same as Germany)
                'SE': 'Europe/Stockholm',        # Sweden
                'NO': 'Europe/Stockholm',        # Norway (same as Sweden)
                'DK': 'Europe/Stockholm',        # Denmark (same as Sweden)
                'FI': 'Europe/Stockholm',        # Finland (same as Sweden)
                'IS': 'Europe/London',           # Iceland (same as UK)
                'RU': 'Europe/Moscow',           # Russia (Moscow time)
                'PL': 'Europe/Berlin',           # Poland (same as Germany)
                # Czech Republic (same as Germany)
                'CZ': 'Europe/Berlin',
                'HU': 'Europe/Berlin',           # Hungary (same as Germany)
                'SK': 'Europe/Berlin',           # Slovakia (same as Germany)
                'SI': 'Europe/Berlin',           # Slovenia (same as Germany)
                'HR': 'Europe/Berlin',           # Croatia (same as Germany)
                # Greece (but fallback to Berlin if Athens not available)
                'GR': 'Europe/Athens',
                'BG': 'Europe/Berlin',           # Bulgaria (same as Germany)
                'RO': 'Europe/Berlin',           # Romania (same as Germany)
                'EE': 'Europe/Stockholm',        # Estonia (same as Sweden)
                'LV': 'Europe/Stockholm',        # Latvia (same as Sweden)
                'LT': 'Europe/Stockholm',        # Lithuania (same as Sweden)
                'MT': 'Europe/Rome',             # Malta (same as Italy)
                # Cyprus (closer to Middle East time)
                'CY': 'Asia/Dubai',

                # Asia Pacific
                'JP': 'Asia/Tokyo',              # Japan
                'KR': 'Asia/Seoul',              # South Korea
                'CN': 'Asia/Shanghai',           # China
                'HK': 'Asia/Hong_Kong',          # Hong Kong
                'TW': 'Asia/Shanghai',           # Taiwan (same as China)
                'SG': 'Asia/Singapore',          # Singapore
                'MY': 'Asia/Singapore',          # Malaysia (same as Singapore)
                'TH': 'Asia/Bangkok',            # Thailand
                'VN': 'Asia/Bangkok',            # Vietnam (same as Thailand)
                # Philippines (closer to China time)
                'PH': 'Asia/Shanghai',
                # Indonesia (main islands, same as Thailand)
                'ID': 'Asia/Bangkok',
                'IN': 'Asia/Kolkata',            # India
                'PK': 'Asia/Kolkata',            # Pakistan (close to India)
                'BD': 'Asia/Kolkata',            # Bangladesh (close to India)
                'LK': 'Asia/Kolkata',            # Sri Lanka (same as India)
                'AE': 'Asia/Dubai',              # United Arab Emirates
                'SA': 'Asia/Dubai',              # Saudi Arabia (same as UAE)
                'QA': 'Asia/Dubai',              # Qatar (same as UAE)
                'KW': 'Asia/Dubai',              # Kuwait (same as UAE)
                'BH': 'Asia/Dubai',              # Bahrain (same as UAE)
                'OM': 'Asia/Dubai',              # Oman (same as UAE)
                'JO': 'Asia/Dubai',              # Jordan (same as UAE)
                'IL': 'Asia/Dubai',              # Israel (same as UAE)
                'TR': 'Europe/Berlin',           # Turkey (same as Germany)
                'IR': 'Asia/Dubai',              # Iran (close to UAE)
                'IQ': 'Asia/Dubai',              # Iraq (same as UAE)
                'AU': 'Australia/Sydney',        # Australia (Eastern)
                'NZ': 'Pacific/Auckland',        # New Zealand

                # Africa
                'EG': 'Africa/Cairo',            # Egypt
                'ZA': 'Africa/Johannesburg',     # South Africa
                'NG': 'Africa/Cairo',            # Nigeria (same as Egypt)
                'KE': 'Africa/Cairo',            # Kenya (same as Egypt)
                'GH': 'Africa/Cairo',            # Ghana (same as Egypt)
                'ET': 'Africa/Cairo',            # Ethiopia (same as Egypt)
                'TZ': 'Africa/Cairo',            # Tanzania (same as Egypt)
                'UG': 'Africa/Cairo',            # Uganda (same as Egypt)
                'MA': 'Europe/London',           # Morocco (same as UK)
                'DZ': 'Europe/Paris',            # Algeria (same as France)
                'TN': 'Europe/Paris',            # Tunisia (same as France)
                'LY': 'Africa/Cairo',            # Libya (same as Egypt)
                'SD': 'Africa/Cairo',            # Sudan (same as Egypt)

                # South America
                'BR': 'America/Sao_Paulo',      # Brazil
                'AR': 'America/Buenos_Aires',    # Argentina
                'CL': 'America/Buenos_Aires',    # Chile (same as Argentina)
                'CO': 'America/Sao_Paulo',      # Colombia (same as Brazil)
                'PE': 'America/Sao_Paulo',      # Peru (same as Brazil)
                'VE': 'America/Sao_Paulo',      # Venezuela (same as Brazil)
                'EC': 'America/Sao_Paulo',      # Ecuador (same as Brazil)
                'BO': 'America/Sao_Paulo',      # Bolivia (same as Brazil)
                'UY': 'America/Buenos_Aires',    # Uruguay (same as Argentina)
                'PY': 'America/Sao_Paulo',      # Paraguay (same as Brazil)

                # Caribbean & Central America
                'GT': 'America/Mexico_City',     # Guatemala (same as Mexico)
                'BZ': 'America/Mexico_City',     # Belize (same as Mexico)
                'SV': 'America/Mexico_City',     # El Salvador (same as Mexico)
                'HN': 'America/Mexico_City',     # Honduras (same as Mexico)
                'NI': 'America/Mexico_City',     # Nicaragua (same as Mexico)
                'CR': 'America/Mexico_City',     # Costa Rica (same as Mexico)
                'PA': 'America/Mexico_City',     # Panama (same as Mexico)
                'JM': 'America/New_York',        # Jamaica (same as US Eastern)
                'CU': 'America/New_York',        # Cuba (same as US Eastern)
                # Dominican Republic (same as US Eastern)
                'DO': 'America/New_York',
                'HT': 'America/New_York',        # Haiti (same as US Eastern)
                # Trinidad and Tobago (same as US Eastern)
                'TT': 'America/New_York',
            }

            return country_timezone_map.get(country_code)

        except (ImproperlyConfigured, Exception) as e:
            logger.debug(f"GeoIP timezone detection failed: {e}")
            return None

    def _get_client_ip(self, request):
        """Get the real client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _is_private_ip(self, ip):
        """Check if IP is private/local."""
        import ipaddress
        try:
            return ipaddress.ip_address(ip).is_private
        except ValueError:
            return True

    def _use_default_timezone(self, request):
        """Activate the default timezone."""
        default_tz = getattr(settings, 'TIME_ZONE', 'UTC')
        try:
            tz = pytz.timezone(default_tz)
            timezone.activate(tz)
            request.user_timezone = default_tz
            request.user_timezone_object = tz
        except pytz.exceptions.UnknownTimeZoneError:
            # Ultimate fallback to UTC
            timezone.activate(pytz.UTC)
            request.user_timezone = 'UTC'
            request.user_timezone_object = pytz.UTC
