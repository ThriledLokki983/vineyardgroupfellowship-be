"""
Distance calculation utilities for location-based features.

Uses PostGIS for efficient geographic distance calculations.
"""

import logging
from typing import List, Optional
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D  # D for Distance
from django.db.models import Q

logger = logging.getLogger(__name__)


def calculate_distance(
    point1: Point,
    point2: Point,
    unit: str = 'km'
) -> float:
    """
    Calculate distance between two geographic points.

    Args:
        point1: First geographic point
        point2: Second geographic point
        unit: Unit of measurement ('km', 'mi', 'm', 'ft')

    Returns:
        Distance in the specified unit.

    Example:
        >>> from django.contrib.gis.geos import Point
        >>> point1 = Point(-77.0365, 38.8977, srid=4326)  # Washington DC
        >>> point2 = Point(-74.0060, 40.7128, srid=4326)  # New York
        >>> distance = calculate_distance(point1, point2, 'mi')
        >>> print(f"Distance: {distance:.2f} miles")
    """
    if not point1 or not point2:
        logger.warning(
            "Cannot calculate distance: one or both points are None")
        return 0.0

    # Calculate distance using geography (considers Earth's curvature)
    distance_m = point1.distance(point2) * 100000  # Convert to meters

    # Convert to requested unit
    conversions = {
        'm': 1.0,
        'km': 0.001,
        'mi': 0.000621371,
        'ft': 3.28084,
    }

    conversion_factor = conversions.get(unit.lower(), 1.0)
    return distance_m * conversion_factor


def find_nearby_groups(
    user_location: Point,
    radius_km: float = 5.0,
    limit: Optional[int] = None,
    exclude_online: bool = True,
    max_radius_km: float = 10.0
) -> 'QuerySet':
    """
    Find groups within a specified radius of a location.

    Args:
        user_location: Geographic point representing user's location
        radius_km: Search radius in kilometers (default: 5km, max: 10km)
        limit: Maximum number of results to return (optional)
        exclude_online: Whether to exclude online-only groups (default: True)
        max_radius_km: Maximum allowed search radius (default: 10km)

    Returns:
        QuerySet of Group objects annotated with 'distance' field,
        ordered by distance from user_location.

    Example:
        >>> from django.contrib.gis.geos import Point
        >>> user_point = Point(-77.0365, 38.8977, srid=4326)
        >>> groups = find_nearby_groups(user_point, radius_km=5)
        >>> for group in groups:
        ...     print(f"{group.name}: {group.distance.km:.2f} km away")
    """
    from group.models import Group  # Import here to avoid circular imports

    if not user_location:
        logger.warning("Cannot find nearby groups: user_location is None")
        return Group.objects.none()

    # Enforce maximum radius limit
    if radius_km > max_radius_km:
        logger.warning(
            f"Requested radius {radius_km}km exceeds maximum {max_radius_km}km. "
            f"Using {max_radius_km}km instead."
        )
        radius_km = max_radius_km

    # Build query
    queryset = Group.objects.filter(
        coordinates__isnull=False,  # Only groups with coordinates
        is_active=True,  # Only active groups
        is_open=True,  # Only groups accepting members
        archived_at__isnull=True,  # Exclude archived groups
    )

    # Exclude online-only groups if requested
    if exclude_online:
        queryset = queryset.exclude(location_type='online')

    # Filter by distance and annotate with distance
    queryset = queryset.filter(
        coordinates__distance_lte=(user_location, D(km=radius_km))
    ).annotate(
        distance=Distance('coordinates', user_location)
    ).order_by('distance')

    # Apply limit if specified
    if limit:
        queryset = queryset[:limit]

    return queryset


def find_nearby_users(
    group_location: Point,
    radius_km: float = 50.0,
    limit: Optional[int] = None
) -> 'QuerySet':
    """
    Find users within a specified radius of a group's location.

    Args:
        group_location: Geographic point representing group's location
        radius_km: Search radius in kilometers (default: 50km)
        limit: Maximum number of results to return (optional)

    Returns:
        QuerySet of UserProfileBasic objects annotated with 'distance' field,
        ordered by distance from group_location.

    Example:
        >>> from django.contrib.gis.geos import Point
        >>> group_point = Point(-77.0365, 38.8977, srid=4326)
        >>> users = find_nearby_users(group_point, radius_km=10)
        >>> for user in users:
        ...     print(f"{user.display_name}: {user.distance.km:.2f} km away")
    """
    from profiles.models import UserProfileBasic  # Import here to avoid circular imports

    if not group_location:
        logger.warning("Cannot find nearby users: group_location is None")
        return UserProfileBasic.objects.none()

    # Build query
    queryset = UserProfileBasic.objects.filter(
        coordinates__isnull=False,  # Only users with coordinates
        profile_visibility__in=['public', 'community'],  # Respect privacy
    )

    # Filter by distance and annotate with distance
    queryset = queryset.filter(
        coordinates__distance_lte=(group_location, D(km=radius_km))
    ).annotate(
        distance=Distance('coordinates', group_location)
    ).order_by('distance')

    # Apply limit if specified
    if limit:
        queryset = queryset[:limit]

    return queryset


def get_groups_in_bounding_box(
    min_lat: float,
    max_lat: float,
    min_lng: float,
    max_lng: float
) -> 'QuerySet':
    """
    Get all groups within a bounding box (for map display).

    Args:
        min_lat: Minimum latitude (south)
        max_lat: Maximum latitude (north)
        min_lng: Minimum longitude (west)
        max_lng: Maximum longitude (east)

    Returns:
        QuerySet of Group objects within the bounding box.

    Example:
        >>> # Washington DC area bounding box
        >>> groups = get_groups_in_bounding_box(
        ...     min_lat=38.79, max_lat=38.99,
        ...     min_lng=-77.12, max_lng=-76.91
        ... )
    """
    from group.models import Group

    return Group.objects.filter(
        latitude__gte=min_lat,
        latitude__lte=max_lat,
        longitude__gte=min_lng,
        longitude__lte=max_lng,
        is_active=True,
        archived_at__isnull=True,
    )


def geocode_and_save_group(group: 'Group', force: bool = False) -> bool:
    """
    Geocode a group's location and save coordinates.

    Args:
        group: Group instance to geocode
        force: Force geocoding even if coordinates already exist

    Returns:
        True if geocoding succeeded, False otherwise.

    Example:
        >>> from group.models import Group
        >>> group = Group.objects.get(name="Downtown Fellowship")
        >>> if geocode_and_save_group(group):
        ...     print(f"Geocoded: {group.latitude}, {group.longitude}")
    """
    from django.utils import timezone
    from group.utils.geocoding import geocode_address

    # Skip if coordinates already exist and not forcing
    if not force and group.latitude and group.longitude:
        logger.debug(f"Group '{group.name}' already has coordinates, skipping")
        return True

    # Skip online-only groups
    if group.location_type == 'online':
        logger.debug(
            f"Group '{group.name}' is online-only, skipping geocoding")
        return True

    # Skip if no location
    if not group.location or not group.location.strip():
        logger.warning(f"Group '{group.name}' has no location to geocode")
        return False

    try:
        # Attempt geocoding
        result = geocode_address(group.location)

        if result:
            lat, lng, display_name = result
            group.latitude = lat
            group.longitude = lng
            group.geocoded_address = display_name
            group.geocoded_at = timezone.now()
            group.save(update_fields=[
                'latitude', 'longitude', 'coordinates',
                'geocoded_address', 'geocoded_at', 'updated_at'
            ])

            logger.info(
                f"Geocoded group '{group.name}': ({lat}, {lng}) - {display_name}"
            )
            return True
        else:
            logger.warning(
                f"Failed to geocode group '{group.name}': {group.location}")
            return False

    except Exception as e:
        logger.error(f"Error geocoding group '{group.name}': {e}")
        return False


def geocode_and_save_profile(profile: 'UserProfileBasic', force: bool = False) -> bool:
    """
    Geocode a user profile's location and save coordinates.

    Args:
        profile: UserProfileBasic instance to geocode
        force: Force geocoding even if coordinates already exist

    Returns:
        True if geocoding succeeded, False otherwise.
    """
    from django.utils import timezone
    from group.utils.geocoding import geocode_address

    # Skip if coordinates already exist and not forcing
    if not force and profile.latitude and profile.longitude:
        logger.debug(
            f"Profile for '{profile.user.email}' already has coordinates, skipping"
        )
        return True

    # Build address from location and post_code
    location_parts = []
    if profile.location:
        location_parts.append(profile.location)
    if profile.post_code:
        location_parts.append(profile.post_code)

    if not location_parts:
        logger.warning(
            f"Profile for '{profile.user.email}' has no location to geocode"
        )
        return False

    address = ", ".join(location_parts)

    try:
        # Attempt geocoding
        result = geocode_address(address)

        if result:
            lat, lng, display_name = result
            profile.latitude = lat
            profile.longitude = lng
            profile.geocoded_address = display_name
            profile.geocoded_at = timezone.now()
            profile.save(update_fields=[
                'latitude', 'longitude', 'coordinates',
                'geocoded_address', 'geocoded_at', 'updated_at'
            ])

            logger.info(
                f"Geocoded profile for '{profile.user.email}': "
                f"({lat}, {lng}) - {display_name}"
            )
            return True
        else:
            logger.warning(
                f"Failed to geocode profile for '{profile.user.email}': {address}"
            )
            return False

    except Exception as e:
        logger.error(
            f"Error geocoding profile for '{profile.user.email}': {e}")
        return False
