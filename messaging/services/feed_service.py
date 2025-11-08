"""
Feed service for optimized feed queries with Redis caching.

This service handles feed retrieval with caching, pagination,
and efficient database queries using select_related and prefetch_related.
"""

from django.core.cache import cache
from django.db.models import Prefetch, Q
from ..models import FeedItem, Reaction
from .cache_service import CacheService
import logging

logger = logging.getLogger(__name__)


class FeedService:
    """Optimized feed service with caching and pagination."""

    PAGE_SIZE = 25
    MAX_PAGE_SIZE = 100

    @classmethod
    def get_feed(cls, group_id, page=1, page_size=None, content_type=None, user=None):
        """
        Get paginated feed with caching.

        Args:
            group_id: UUID of the group
            page: Page number (1-indexed, default: 1)
            page_size: Items per page (default: 25, max: 100)
            content_type: Optional filter by content type (discussion, prayer, testimony, scripture)
            user: Optional user for permission checks

        Returns:
            dict: Paginated feed data with cache status
                {
                    'items': List of feed items,
                    'pagination': Pagination metadata,
                    'from_cache': bool
                }
        """
        # Validate and normalize page_size
        if page_size is None:
            page_size = cls.PAGE_SIZE
        elif page_size > cls.MAX_PAGE_SIZE:
            page_size = cls.MAX_PAGE_SIZE

        # Validate page number
        if page < 1:
            page = 1

        # Generate cache key
        filters = {}
        if content_type:
            filters['content_type'] = content_type

        cache_key = CacheService.get_feed_key(
            group_id, page, page_size, filters)

        # Try cache first
        cached_feed = CacheService.get(cache_key)
        if cached_feed:
            logger.debug(f"Cache HIT: {cache_key}")
            cached_feed['from_cache'] = True
            return cached_feed

        logger.debug(f"Cache MISS: {cache_key} - Querying database")

        # Calculate pagination offsets
        start = (page - 1) * page_size
        end = start + page_size

        # Build optimized query
        queryset = cls._build_feed_queryset(group_id, content_type)

        # Get paginated items with optimized prefetching
        feed_items = list(queryset[start:end])

        # Get total count for pagination
        total_count = queryset.count()

        # Serialize for caching
        result = {
            'items': [cls._serialize_feed_item(item) for item in feed_items],
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size,
                'has_next': end < total_count,
                'has_previous': page > 1,
            },
            'from_cache': False,
        }

        # Cache for 5 minutes
        CacheService.set_with_timeout(
            cache_key, result, CacheService.FEED_TIMEOUT)
        logger.info(
            f"Cached feed for group {group_id}, page {page} (size: {page_size})")

        return result

    @classmethod
    def _build_feed_queryset(cls, group_id, content_type=None):
        """
        Build optimized queryset for feed items.

        Uses select_related and prefetch_related to minimize database queries.

        Args:
            group_id: UUID of the group
            content_type: Optional content type filter

        Returns:
            QuerySet: Optimized feed item queryset
        """
        # Base query with group filter
        queryset = FeedItem.objects.filter(
            group_id=group_id,
            is_deleted=False  # Don't show soft-deleted items
        )

        # Apply content type filter if provided
        if content_type:
            queryset = queryset.filter(content_type=content_type)

        # Optimize with select_related for foreign keys
        queryset = queryset.select_related(
            'author',  # User model
            'author__basic_profile',  # BasicProfile for display name/avatar
        )

        # Optimize with prefetch_related for reverse relations
        queryset = queryset.prefetch_related(
            Prefetch(
                'reactions',
                queryset=Reaction.objects.select_related('user')
            ),
            # Prefetch comments count is already denormalized in comment_count
        )

        # Order by most recent first
        queryset = queryset.order_by('-created_at')

        return queryset

    @classmethod
    def _serialize_feed_item(cls, item):
        """
        Serialize FeedItem for JSON caching.

        Args:
            item: FeedItem instance

        Returns:
            dict: Serialized feed item
        """
        # Get author display name
        author_display_name = item.author.get_full_name() if hasattr(
            item.author, 'get_full_name') else item.author.username

        # Get author avatar if basic_profile exists
        author_avatar = None
        if hasattr(item.author, 'basic_profile') and item.author.basic_profile:
            if item.author.basic_profile.profile_picture:
                author_avatar = item.author.basic_profile.profile_picture.url

        return {
            'id': str(item.id),
            'content_type': item.content_type,
            'content_id': str(item.content_id),
            'title': item.title,
            'preview': item.preview,
            'author': {
                'id': str(item.author.id),
                'username': item.author.username,
                'display_name': author_display_name,
                'avatar_url': author_avatar,
            },
            'created_at': item.created_at.isoformat(),
            'updated_at': item.updated_at.isoformat() if item.updated_at else None,
            'comment_count': item.comment_count,
            'reaction_count': item.reaction_count,
            'is_pinned': item.is_pinned,
        }

    @classmethod
    def invalidate_group_feed(cls, group_id):
        """
        Invalidate all cached feed pages for a group.

        This should be called when:
        - New content is created
        - Content is updated or deleted
        - Reactions or comments change counts

        Args:
            group_id: UUID of the group
        """
        CacheService.invalidate_feed(group_id)
        logger.info(f"Invalidated feed cache for group {group_id}")

    @classmethod
    def get_feed_stats(cls, group_id):
        """
        Get cached feed statistics for a group.

        Args:
            group_id: UUID of the group

        Returns:
            dict: Feed statistics (total items by type, recent activity)
        """
        cache_key = CacheService.get_group_stats_key(group_id)

        # Try cache first
        cached_stats = CacheService.get(cache_key)
        if cached_stats:
            logger.debug(f"Cache HIT: {cache_key}")
            return cached_stats

        logger.debug(f"Cache MISS: {cache_key} - Calculating stats")

        # Calculate stats
        queryset = FeedItem.objects.filter(group_id=group_id, is_deleted=False)

        stats = {
            'total_items': queryset.count(),
            'discussions': queryset.filter(content_type='discussion').count(),
            'prayers': queryset.filter(content_type='prayer').count(),
            'testimonies': queryset.filter(content_type='testimony').count(),
            'scriptures': queryset.filter(content_type='scripture').count(),
            'most_recent_at': None,
        }

        # Get most recent item timestamp
        most_recent = queryset.order_by('-created_at').first()
        if most_recent:
            stats['most_recent_at'] = most_recent.created_at.isoformat()

        # Cache for 10 minutes
        CacheService.set_with_timeout(
            cache_key, stats, CacheService.GROUP_STATS_TIMEOUT)
        logger.info(f"Cached feed stats for group {group_id}")

        return stats

    @classmethod
    def warm_cache(cls, group_id, pages=3):
        """
        Pre-warm cache for first N pages of a group's feed.

        Useful after deployment or cache clear to prevent cold cache slowdown.

        Args:
            group_id: UUID of the group
            pages: Number of pages to warm (default: 3)
        """
        logger.info(f"Warming cache for group {group_id}, {pages} pages")

        for page in range(1, pages + 1):
            try:
                cls.get_feed(group_id, page=page)
                logger.debug(f"Warmed page {page} for group {group_id}")
            except Exception as e:
                logger.error(
                    f"Failed to warm page {page} for group {group_id}: {e}")

        # Also warm stats
        try:
            cls.get_feed_stats(group_id)
        except Exception as e:
            logger.error(f"Failed to warm stats for group {group_id}: {e}")
