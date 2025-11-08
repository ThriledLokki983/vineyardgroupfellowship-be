"""
Cache service for managing Redis caching across the messaging app.

This service provides centralized cache key generation and invalidation
for feeds, profiles, memberships, and Bible verses.
"""

from django.core.cache import cache
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class CacheService:
    """Centralized caching service with key management."""

    # Cache timeouts (in seconds)
    FEED_TIMEOUT = 300         # 5 minutes
    VERSE_TIMEOUT = 604800     # 7 days
    PROFILE_TIMEOUT = 900      # 15 minutes
    MEMBERSHIP_TIMEOUT = 300   # 5 minutes
    GROUP_STATS_TIMEOUT = 600  # 10 minutes

    @classmethod
    def get_feed_key(cls, group_id, page=1, page_size=25, filters=None):
        """
        Generate cache key for feed queries.

        Args:
            group_id: UUID of the group
            page: Page number (1-indexed)
            page_size: Number of items per page
            filters: Optional dict of filters (e.g., content_type)

        Returns:
            str: Cache key for the feed
        """
        filter_hash = ''
        if filters:
            # Create deterministic hash of filters
            filter_hash = hashlib.md5(
                json.dumps(filters, sort_keys=True).encode()
            ).hexdigest()[:8]
        return f"feed:g{group_id}:p{page}:s{page_size}:{filter_hash}"

    @classmethod
    def get_verse_key(cls, reference, translation='NIV'):
        """
        Generate cache key for Bible verses.

        Args:
            reference: Bible verse reference (e.g., "John 3:16")
            translation: Bible translation (default: NIV)

        Returns:
            str: Cache key for the verse
        """
        normalized_ref = reference.lower().replace(' ', '_')
        return f"verse:{translation}:{normalized_ref}"

    @classmethod
    def get_profile_key(cls, user_id):
        """
        Generate cache key for user profiles.

        Args:
            user_id: UUID of the user

        Returns:
            str: Cache key for the profile
        """
        return f"profile:u{user_id}"

    @classmethod
    def get_membership_key(cls, user_id, group_id):
        """
        Generate cache key for membership checks.

        Args:
            user_id: UUID of the user
            group_id: UUID of the group

        Returns:
            str: Cache key for the membership
        """
        return f"membership:u{user_id}:g{group_id}"

    @classmethod
    def get_group_stats_key(cls, group_id):
        """
        Generate cache key for group statistics.

        Args:
            group_id: UUID of the group

        Returns:
            str: Cache key for group stats
        """
        return f"group:stats:g{group_id}"

    @classmethod
    def invalidate_feed(cls, group_id):
        """
        Invalidate all feed pages for a group.

        This deletes all cached feed keys matching the group pattern.
        Uses django-redis for pattern-based deletion.

        Args:
            group_id: UUID of the group
        """
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")

            # Include KEY_PREFIX in pattern if configured
            from django.conf import settings
            cache_config = settings.CACHES.get('default', {})
            key_prefix = cache_config.get('KEY_PREFIX', '')

            # Build pattern with prefix
            if key_prefix:
                pattern = f"{key_prefix}:*:feed:g{group_id}:*"
            else:
                pattern = f"*:feed:g{group_id}:*"

            # Use scan_iter for better performance with large keysets
            keys_deleted = 0
            for key in redis_conn.scan_iter(match=pattern, count=100):
                redis_conn.delete(key)
                keys_deleted += 1

            if keys_deleted > 0:
                logger.info(
                    f"Invalidated {keys_deleted} feed cache keys for group {group_id}")
            else:
                logger.debug(f"No feed cache keys found for group {group_id}")
        except ImportError:
            logger.warning(
                "django-redis not installed, falling back to manual invalidation")
            # Fallback: invalidate first few pages manually
            for page in range(1, 10):
                for page_size in [25, 50]:
                    key = cls.get_feed_key(group_id, page, page_size)
                    cache.delete(key)
        except Exception as e:
            logger.warning(f"Cache invalidation failed (non-critical): {e}")
            # Fallback to manual invalidation
            for page in range(1, 10):
                for page_size in [25, 50]:
                    key = cls.get_feed_key(group_id, page, page_size)
                    cache.delete(key)

    @classmethod
    def invalidate_profile(cls, user_id):
        """
        Invalidate user profile cache.

        Args:
            user_id: UUID of the user
        """
        key = cls.get_profile_key(user_id)
        cache.delete(key)
        logger.debug(f"Invalidated profile cache for user {user_id}")

    @classmethod
    def invalidate_membership(cls, user_id, group_id):
        """
        Invalidate membership cache for a user-group pair.

        Args:
            user_id: UUID of the user
            group_id: UUID of the group
        """
        key = cls.get_membership_key(user_id, group_id)
        cache.delete(key)
        logger.debug(
            f"Invalidated membership cache for user {user_id} in group {group_id}")

    @classmethod
    def invalidate_group_stats(cls, group_id):
        """
        Invalidate group statistics cache.

        Args:
            group_id: UUID of the group
        """
        key = cls.get_group_stats_key(group_id)
        cache.delete(key)
        logger.debug(f"Invalidated group stats cache for group {group_id}")

    @classmethod
    def set_with_timeout(cls, key, value, timeout):
        """
        Set cache value with timeout.

        Args:
            key: Cache key
            value: Value to cache
            timeout: Timeout in seconds

        Returns:
            bool: True if successfully cached
        """
        try:
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False

    @classmethod
    def get(cls, key, default=None):
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        try:
            return cache.get(key, default)
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return default

    @classmethod
    def delete(cls, key):
        """
        Delete a cache key.

        Args:
            key: Cache key to delete
        """
        try:
            cache.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")

    @classmethod
    def clear_all(cls):
        """
        Clear all cache (use with caution).
        Should only be used in testing or emergency situations.
        """
        try:
            cache.clear()
            logger.warning("All cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
