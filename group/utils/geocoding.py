"""
Geocoding utilities for converting addresses to coordinates.

Uses Nominatim (OpenStreetMap) geocoding service.
"""

import logging
import time
from typing import Optional, Dict, Any, Tuple
from django.conf import settings
from django.core.cache import cache
import requests

logger = logging.getLogger(__name__)


class GeocodingError(Exception):
    """Base exception for geocoding errors."""
    pass


class GeocodingRateLimitError(GeocodingError):
    """Raised when geocoding rate limit is exceeded."""
    pass


class NominatimGeocoder:
    """
    Nominatim geocoding service wrapper.

    Free geocoding service from OpenStreetMap with usage limits:
    - Max 1 request per second
    - Must include User-Agent header
    - Cache results to minimize requests
    """

    BASE_URL = 'https://nominatim.openstreetmap.org'
    CACHE_TIMEOUT = 60 * 60 * 24 * 30  # Cache for 30 days
    RATE_LIMIT_DELAY = 1.0  # 1 second between requests

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'VineyardGroupFellowship/1.0 (Django Application)',
            'Accept-Language': 'en',
        })
        self._last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting (1 request per second)."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self.RATE_LIMIT_DELAY:
            sleep_time = self.RATE_LIMIT_DELAY - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def geocode(
        self,
        address: str,
        country_code: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Convert address to coordinates.

        Args:
            address: The address to geocode
            country_code: ISO 3166-1alpha2 country code to limit results (e.g., 'US', 'GB')
            use_cache: Whether to use cached results

        Returns:
            Dictionary with geocoding results:
            {
                'latitude': float,
                'longitude': float,
                'display_name': str,  # Full formatted address
                'type': str,  # Type of location (e.g., 'city', 'town', 'building')
                'importance': float,  # Relevance score
                'boundingbox': list,  # [min_lat, max_lat, min_lon, max_lon]
            }

            Returns None if address cannot be geocoded.

        Raises:
            GeocodingError: If geocoding fails
            GeocodingRateLimitError: If rate limit is exceeded
        """
        if not address or not address.strip():
            logger.warning("Empty address provided for geocoding")
            return None

        # Check cache first
        cache_key = f"geocode:{address}:{country_code or 'all'}"
        if use_cache:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Geocoding cache hit for: {address}")
                return cached_result

        # Respect rate limiting
        self._rate_limit()

        # Prepare request parameters
        params = {
            'q': address,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1,
        }

        if country_code:
            params['countrycodes'] = country_code.lower()

        try:
            logger.info(f"Geocoding address: {address}")
            response = self.session.get(
                f"{self.BASE_URL}/search",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            results = response.json()

            if not results:
                logger.warning(f"No geocoding results found for: {address}")
                # Cache negative results to avoid repeated lookups
                if use_cache:
                    cache.set(cache_key, None, self.CACHE_TIMEOUT)
                return None

            # Extract first result
            result = results[0]
            geocoded = {
                'latitude': float(result['lat']),
                'longitude': float(result['lon']),
                'display_name': result.get('display_name', ''),
                'type': result.get('type', ''),
                'importance': float(result.get('importance', 0)),
                'boundingbox': result.get('boundingbox', []),
                'address': result.get('address', {}),
            }

            # Cache the result
            if use_cache:
                cache.set(cache_key, geocoded, self.CACHE_TIMEOUT)

            logger.info(
                f"Geocoded '{address}' -> "
                f"({geocoded['latitude']}, {geocoded['longitude']})"
            )

            return geocoded

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("Geocoding rate limit exceeded")
                raise GeocodingRateLimitError(
                    "Geocoding rate limit exceeded. Please try again later."
                )
            logger.error(f"HTTP error during geocoding: {e}")
            raise GeocodingError(f"Geocoding failed: {e}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during geocoding: {e}")
            raise GeocodingError(f"Geocoding request failed: {e}")

        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing geocoding response: {e}")
            raise GeocodingError(f"Invalid geocoding response: {e}")

    def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        zoom: int = 18,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Convert coordinates to address (reverse geocoding).

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            zoom: Level of detail (0-18, where 18 is most detailed)
            use_cache: Whether to use cached results

        Returns:
            Dictionary with address components and display name.
            Returns None if coordinates cannot be reverse geocoded.

        Raises:
            GeocodingError: If reverse geocoding fails
        """
        # Check cache first
        cache_key = f"reverse_geocode:{latitude}:{longitude}:{zoom}"
        if use_cache:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(
                    f"Reverse geocoding cache hit for: ({latitude}, {longitude})"
                )
                return cached_result

        # Respect rate limiting
        self._rate_limit()

        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'zoom': zoom,
            'addressdetails': 1,
        }

        try:
            logger.info(f"Reverse geocoding: ({latitude}, {longitude})")
            response = self.session.get(
                f"{self.BASE_URL}/reverse",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()

            if 'error' in result:
                logger.warning(
                    f"No reverse geocoding results for: ({latitude}, {longitude})"
                )
                return None

            reversed_data = {
                'display_name': result.get('display_name', ''),
                'address': result.get('address', {}),
                'type': result.get('type', ''),
            }

            # Cache the result
            if use_cache:
                cache.set(cache_key, reversed_data, self.CACHE_TIMEOUT)

            logger.info(
                f"Reverse geocoded ({latitude}, {longitude}) -> "
                f"{reversed_data['display_name']}"
            )

            return reversed_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during reverse geocoding: {e}")
            raise GeocodingError(f"Reverse geocoding request failed: {e}")

        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing reverse geocoding response: {e}")
            raise GeocodingError(f"Invalid reverse geocoding response: {e}")


# Global geocoder instance
_geocoder = NominatimGeocoder()


def geocode_address(
    address: str,
    country_code: Optional[str] = None,
    use_cache: bool = True
) -> Optional[Tuple[float, float, str]]:
    """
    Geocode an address to coordinates.

    Args:
        address: The address to geocode
        country_code: ISO 3166-1alpha2 country code (e.g., 'US', 'GB')
        use_cache: Whether to use cached results

    Returns:
        Tuple of (latitude, longitude, display_name) or None if geocoding fails.

    Example:
        >>> coords = geocode_address("1600 Pennsylvania Avenue NW, Washington, DC", "US")
        >>> if coords:
        ...     lat, lng, name = coords
        ...     print(f"Coordinates: {lat}, {lng}")
        ...     print(f"Address: {name}")
    """
    try:
        result = _geocoder.geocode(address, country_code, use_cache)
        if result:
            return (
                result['latitude'],
                result['longitude'],
                result['display_name']
            )
        return None
    except GeocodingError as e:
        logger.error(f"Geocoding failed for '{address}': {e}")
        return None


def reverse_geocode(
    latitude: float,
    longitude: float,
    use_cache: bool = True
) -> Optional[str]:
    """
    Reverse geocode coordinates to an address.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        use_cache: Whether to use cached results

    Returns:
        Formatted address string or None if reverse geocoding fails.

    Example:
        >>> address = reverse_geocode(38.8977, -77.0365)
        >>> print(address)
        "1600 Pennsylvania Avenue NW, Washington, DC 20500, USA"
    """
    try:
        result = _geocoder.reverse_geocode(
            latitude, longitude, use_cache=use_cache)
        if result:
            return result['display_name']
        return None
    except GeocodingError as e:
        logger.error(
            f"Reverse geocoding failed for ({latitude}, {longitude}): {e}"
        )
        return None
