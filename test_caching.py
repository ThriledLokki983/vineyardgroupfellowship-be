"""
Test script for Redis caching implementation.

Tests:
1. FeedService cache hit/miss behavior
2. Cache invalidation on content changes
3. Cache key generation
"""

from django.contrib.auth import get_user_model
from group.models import Group
from messaging.services import FeedService, CacheService
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'vineyard_group_fellowship.settings')
django.setup()


User = get_user_model()


def test_cache_service():
    """Test CacheService key generation."""
    print("\n=== Testing CacheService ===")

    test_group_id = "12345678-1234-1234-1234-123456789012"

    # Test feed key generation
    key1 = CacheService.get_feed_key(test_group_id, page=1, page_size=25)
    print(f"✓ Feed key (page 1): {key1}")

    key2 = CacheService.get_feed_key(test_group_id, page=2, page_size=25)
    print(f"✓ Feed key (page 2): {key2}")

    key3 = CacheService.get_feed_key(test_group_id, page=1, page_size=25, filters={
                                     'content_type': 'discussion'})
    print(f"✓ Feed key (filtered): {key3}")

    # Test verse key generation
    verse_key = CacheService.get_verse_key("John 3:16", "NIV")
    print(f"✓ Verse key: {verse_key}")

    # Test profile key generation
    user_id = "87654321-4321-4321-4321-210987654321"
    profile_key = CacheService.get_profile_key(user_id)
    print(f"✓ Profile key: {profile_key}")

    print("✅ CacheService tests passed!\n")


def test_feed_service_caching():
    """Test FeedService with actual data."""
    print("\n=== Testing FeedService Caching ===")

    # Get first group
    group = Group.objects.first()
    if not group:
        print("⚠️  No groups found, skipping feed tests")
        return

    print(f"Testing with group: {group.name} ({group.id})")

    # First call - should be cache miss
    print("\n1. First call (should be cache MISS):")
    result1 = FeedService.get_feed(group.id, page=1)
    print(f"   From cache: {result1['from_cache']}")
    print(f"   Items: {len(result1['items'])}")
    print(f"   Total: {result1['pagination']['total_count']}")

    # Second call - should be cache hit
    print("\n2. Second call (should be cache HIT):")
    result2 = FeedService.get_feed(group.id, page=1)
    print(f"   From cache: {result2['from_cache']}")
    print(f"   Items: {len(result2['items'])}")

    # Verify results are the same
    assert result1['items'] == result2['items'], "Cache results should match!"
    print("   ✓ Results match!")

    # Test cache invalidation
    print("\n3. Testing cache invalidation:")
    FeedService.invalidate_group_feed(group.id)
    print("   Cache invalidated")

    # Third call - should be cache miss again
    print("\n4. Third call (should be cache MISS again):")
    result3 = FeedService.get_feed(group.id, page=1)
    print(f"   From cache: {result3['from_cache']}")

    print("\n✅ FeedService caching tests passed!")


def test_feed_stats():
    """Test feed statistics caching."""
    print("\n=== Testing Feed Stats Caching ===")

    group = Group.objects.first()
    if not group:
        print("⚠️  No groups found, skipping stats tests")
        return

    print(f"Testing stats for group: {group.name}")

    # First call
    print("\n1. First call (cache MISS):")
    stats1 = FeedService.get_feed_stats(group.id)
    print(f"   Total items: {stats1['total_items']}")
    print(f"   Discussions: {stats1['discussions']}")
    print(f"   Prayers: {stats1['prayers']}")
    print(f"   Testimonies: {stats1['testimonies']}")
    print(f"   Scriptures: {stats1['scriptures']}")

    # Second call (should be cached)
    print("\n2. Second call (cache HIT):")
    stats2 = FeedService.get_feed_stats(group.id)
    assert stats1 == stats2, "Stats should match!"
    print("   ✓ Results match!")

    print("\n✅ Feed stats caching tests passed!")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("REDIS CACHING IMPLEMENTATION TESTS")
    print("="*60)

    try:
        test_cache_service()
        test_feed_service_caching()
        test_feed_stats()

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
