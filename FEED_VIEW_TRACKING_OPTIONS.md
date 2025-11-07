# Feed Item View Tracking - Implementation Options

## Overview

This document explores different architectural approaches for tracking which users have viewed which feed items in the messaging app. The goal is to add a `has_viewed` field to feed item API responses that indicates whether the current user has seen each item.

## Use Case

**Current Behavior:**
```json
GET /api/v1/messaging/feed/?group={group_id}

Response: [
  {
    "id": "uuid",
    "title": "Prayer request...",
    "content_type": "prayer",
    ...
  }
]
```

**Desired Behavior:**
```json
Response: [
  {
    "id": "uuid",
    "title": "Prayer request...",
    "content_type": "prayer",
    "has_viewed": true,  // ← NEW: User has seen this item
    ...
  }
]
```

---

## Option 1: Separate `FeedItemView` Model ⭐ RECOMMENDED

### Architecture

Create a dedicated model to track view events:

```python
class FeedItemView(models.Model):
    """Track which users have viewed which feed items."""
    feed_item = models.ForeignKey(
        FeedItem,
        on_delete=models.CASCADE,
        related_name='views'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messaging_feed_item_view'
        unique_together = ['feed_item', 'user']
        indexes = [
            models.Index(fields=['user', '-viewed_at']),
            models.Index(fields=['feed_item', 'user']),
        ]

    def __str__(self):
        return f"{self.user.email} viewed {self.feed_item.title}"
```

### Implementation

**1. Serializer Update:**
```python
class FeedItemSerializer(serializers.ModelSerializer):
    has_viewed = serializers.SerializerMethodField()

    class Meta:
        model = FeedItem
        fields = [
            # ... existing fields ...
            'has_viewed',
        ]

    def get_has_viewed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # Uses prefetch_related to avoid N+1
        return any(view.user_id == request.user.id for view in obj.views.all())
```

**2. ViewSet Optimization:**
```python
class FeedViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        user = self.request.user
        queryset = FeedItem.objects.filter(...)

        # Optimize: prefetch only current user's views
        queryset = queryset.prefetch_related(
            Prefetch(
                'views',
                queryset=FeedItemView.objects.filter(user=user),
                to_attr='user_views'
            )
        )
        return queryset
```

**3. Mark as Viewed Endpoint:**
```python
@action(detail=True, methods=['post'], url_path='mark-viewed')
def mark_viewed(self, request, pk=None):
    """Mark a feed item as viewed by current user."""
    feed_item = self.get_object()
    view, created = FeedItemView.objects.get_or_create(
        feed_item=feed_item,
        user=request.user
    )
    return Response({
        'detail': 'Marked as viewed',
        'viewed_at': view.viewed_at
    })

@action(detail=False, methods=['post'], url_path='mark-all-viewed')
def mark_all_viewed(self, request):
    """Mark all feed items in current queryset as viewed."""
    feed_items = self.filter_queryset(self.get_queryset())

    # Bulk create view records (efficient)
    views = [
        FeedItemView(feed_item=item, user=request.user)
        for item in feed_items
    ]
    FeedItemView.objects.bulk_create(views, ignore_conflicts=True)

    return Response({
        'detail': f'Marked {len(views)} items as viewed'
    })
```

### Pros ✅

- **Clean separation of concerns** - View tracking is separate from feed items
- **Granular tracking** - Know exactly when each user viewed each item
- **Timestamps included** - Can show "viewed 2 hours ago"
- **Supports analytics** - Track engagement, most viewed posts, etc.
- **Easy to implement "unread"** - Just delete the view record
- **No impact on existing queries** - FeedItem table unchanged
- **Efficient with prefetch_related** - Avoids N+1 queries
- **Can clean up old data** - Delete views older than X days to save space

### Cons ❌

- **Additional table** - One more model to maintain
- **Extra JOIN required** - Slight performance overhead
- **More write operations** - Creates a record per view per user
- **Database growth** - Table grows with users × feed items viewed

### Performance Characteristics

- **Read Performance**: Fast with `prefetch_related` optimization (~1-2ms overhead)
- **Write Performance**: Single insert per view (~5-10ms)
- **Storage Growth**: ~100 bytes per view record
- **Scaling**: Works well up to 10M+ view records with proper indexing

### When to Use

- ✅ Need per-item, per-user tracking
- ✅ Want view timestamps
- ✅ Building engagement analytics
- ✅ Small to medium scale (<100k daily active users)
- ✅ Need "mark as unread" functionality

---

## Option 2: ManyToMany Field on FeedItem

### Architecture

Add a ManyToMany relationship directly on FeedItem:

```python
class FeedItem(models.Model):
    # ... existing fields ...

    viewed_by = models.ManyToManyField(
        User,
        related_name='viewed_feed_items',
        blank=True,
        help_text='Users who have viewed this feed item'
    )
```

### Implementation

**Serializer:**
```python
class FeedItemSerializer(serializers.ModelSerializer):
    has_viewed = serializers.SerializerMethodField()

    def get_has_viewed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.viewed_by.filter(id=request.user.id).exists()
```

**Mark as viewed:**
```python
@action(detail=True, methods=['post'])
def mark_viewed(self, request, pk=None):
    feed_item = self.get_object()
    feed_item.viewed_by.add(request.user)
    return Response({'detail': 'Marked as viewed'})
```

### Pros ✅

- **Simple to implement** - Django handles the through table automatically
- **Less code** - No separate model to manage
- **Built-in methods** - `.add()`, `.remove()`, `.clear()` available
- **Easy queries** - `feed_item.viewed_by.all()` or `user.viewed_feed_items.all()`

### Cons ❌

- **No timestamps** - Can't track when it was viewed
- **No view metadata** - Can't track IP, device, source, etc.
- **Hidden through table** - Less control over indexing and optimization
- **Harder to analyze** - Can't track view history or patterns
- **Can't track multiple views** - Only binary viewed/not viewed
- **Database bloat** - Through table grows but harder to clean up
- **No "mark as unread"** - Would need custom logic

### When to Use

- ✅ Simple read/unread tracking only
- ✅ Don't need timestamps
- ✅ Don't need analytics
- ✅ Prototype/MVP phase

---

## Option 3: Redis/Cache-Based Tracking

### Architecture

Store view status in Redis cache:

```python
# Key patterns:
# "feed_view:{user_id}:{feed_item_id}" -> True
# OR
# "feed_views:{user_id}" -> Set(feed_item_ids)
```

### Implementation

**Cache Service:**
```python
class FeedViewCache:
    @staticmethod
    def mark_viewed(user_id, feed_item_id):
        cache_key = f"feed_view:{user_id}:{feed_item_id}"
        cache.set(cache_key, True, timeout=None)

    @staticmethod
    def has_viewed(user_id, feed_item_id):
        cache_key = f"feed_view:{user_id}:{feed_item_id}"
        return cache.get(cache_key, False)

    @staticmethod
    def mark_all_viewed(user_id, feed_item_ids):
        """Batch mark multiple items as viewed."""
        pipeline = cache._cache.pipeline()  # Redis pipeline
        for item_id in feed_item_ids:
            key = f"feed_view:{user_id}:{item_id}"
            pipeline.set(key, True)
        pipeline.execute()
```

**Serializer:**
```python
class FeedItemSerializer(serializers.ModelSerializer):
    has_viewed = serializers.SerializerMethodField()

    def get_has_viewed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return FeedViewCache.has_viewed(request.user.id, str(obj.id))
```

### Pros ✅

- **EXTREMELY fast** - Redis reads in <1ms
- **No database load** - Zero impact on PostgreSQL
- **No database bloat** - View data not in DB
- **Can implement TTL** - Auto-expire old views (e.g., 30 days)
- **High throughput** - Can handle millions of views/sec
- **Perfect for high-traffic** - Scales horizontally

### Cons ❌

- **Data loss risk** - If Redis crashes (unless using persistence)
- **No permanent record** - Can't analyze historical data
- **Can't query reverse** - "Who viewed this item?" is harder
- **Need fallback** - Should have database backup for critical data
- **Cache warming** - Need to populate cache on cold start
- **Memory cost** - Redis memory can be expensive

### When to Use

- ✅ High-volume applications (>100k daily active users)
- ✅ View tracking is ephemeral (doesn't need permanent storage)
- ✅ Need sub-millisecond response times
- ✅ Have Redis infrastructure already
- ❌ DON'T use for critical business logic

---

## Option 4: Hybrid Approach (Database + Cache) ⭐ BEST FOR SCALE

### Architecture

Combine database persistence with Redis caching:

1. **Write to database** - Permanent record in FeedItemView model
2. **Cache in Redis** - Fast reads
3. **Warm cache from DB** - Populate cache on miss

### Implementation

**Service Layer:**
```python
class FeedViewTracker:
    CACHE_TTL = 3600  # 1 hour

    @staticmethod
    def mark_viewed(feed_item_id, user_id):
        """Mark item as viewed (database + cache)."""
        # Write to database
        view, created = FeedItemView.objects.get_or_create(
            feed_item_id=feed_item_id,
            user_id=user_id
        )

        # Update cache
        cache_key = f"feed_view:{user_id}:{feed_item_id}"
        cache.set(cache_key, True, timeout=FeedViewTracker.CACHE_TTL)

        return view

    @staticmethod
    def has_viewed(feed_item_id, user_id):
        """Check if user has viewed item (cache-first)."""
        cache_key = f"feed_view:{user_id}:{feed_item_id}"

        # Try cache first
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Check database
        exists = FeedItemView.objects.filter(
            feed_item_id=feed_item_id,
            user_id=user_id
        ).exists()

        # Cache the result
        cache.set(cache_key, exists, timeout=FeedViewTracker.CACHE_TTL)
        return exists

    @staticmethod
    def bulk_check_viewed(feed_item_ids, user_id):
        """Check multiple items efficiently."""
        # Try to get all from cache first
        cache_keys = [f"feed_view:{user_id}:{fid}" for fid in feed_item_ids]
        cached_results = cache.get_many(cache_keys)

        # Find items not in cache
        uncached_ids = [
            fid for i, fid in enumerate(feed_item_ids)
            if cache_keys[i] not in cached_results
        ]

        # Query database for uncached items
        if uncached_ids:
            viewed_ids = set(FeedItemView.objects.filter(
                feed_item_id__in=uncached_ids,
                user_id=user_id
            ).values_list('feed_item_id', flat=True))

            # Cache the results
            to_cache = {
                f"feed_view:{user_id}:{fid}": fid in viewed_ids
                for fid in uncached_ids
            }
            cache.set_many(to_cache, timeout=FeedViewTracker.CACHE_TTL)

        # Combine results
        results = {}
        for i, fid in enumerate(feed_item_ids):
            if cache_keys[i] in cached_results:
                results[fid] = cached_results[cache_keys[i]]
            else:
                results[fid] = fid in viewed_ids

        return results
```

### Pros ✅

- **Best of both worlds** - Fast reads + permanent storage
- **High performance** - Cache provides speed
- **Data durability** - Database ensures no data loss
- **Supports analytics** - Database enables complex queries
- **Graceful degradation** - Falls back to DB if cache fails
- **Production-ready** - Used by major platforms (Twitter, Reddit, etc.)

### Cons ❌

- **Most complex** - More code to maintain
- **Cache invalidation** - Need to handle cache updates carefully
- **Two systems** - Both Redis and PostgreSQL required
- **Initial setup** - More infrastructure to configure

### When to Use

- ✅ Production applications at scale
- ✅ Need both speed and durability
- ✅ Building analytics features
- ✅ Have >50k daily active users
- ✅ Can maintain Redis infrastructure

---

## Option 5: Lightweight "Last Fetch" Timestamp

### Architecture

Track when user last fetched the feed, mark items created before that as "viewed":

```python
class GroupMembership(models.Model):
    # ... existing fields ...
    last_feed_fetch = models.DateTimeField(null=True, blank=True)
```

### Implementation

**Update on feed fetch:**
```python
class FeedViewSet(viewsets.ReadOnlyModelViewSet):
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # Update last_feed_fetch for user's group memberships
        group_id = request.query_params.get('group')
        if group_id:
            GroupMembership.objects.filter(
                user=request.user,
                group_id=group_id
            ).update(last_feed_fetch=timezone.now())

        return response
```

**Determine has_viewed:**
```python
class FeedItemSerializer(serializers.ModelSerializer):
    has_viewed = serializers.SerializerMethodField()

    def get_has_viewed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        membership = GroupMembership.objects.filter(
            user=request.user,
            group=obj.group
        ).first()

        if not membership or not membership.last_feed_fetch:
            return False

        # If created before last fetch, consider it viewed
        return obj.created_at < membership.last_feed_fetch
```

### Pros ✅

- **No new models** - Uses existing GroupMembership
- **Very simple** - Minimal code changes
- **No extra storage** - Just one timestamp per membership
- **Efficient** - Single field update per feed fetch
- **Good for "mark all as read"** - Natural behavior

### Cons ❌

- **Not granular** - Can't track individual items
- **All or nothing** - Must view entire feed to mark as read
- **Can't "unread" items** - No way to mark specific items unread
- **Less accurate** - Assumes user saw everything
- **No view history** - Can't track engagement patterns

### When to Use

- ✅ Simple "mark all as read" functionality
- ✅ Don't need per-item tracking
- ✅ Minimalist approach for MVP
- ❌ DON'T use if need granular control

---

## Comparison Matrix

| Feature | Option 1: FeedItemView | Option 2: ManyToMany | Option 3: Redis | Option 4: Hybrid | Option 5: Last Fetch |
|---------|----------------------|---------------------|-----------------|------------------|---------------------|
| **Granular Tracking** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **View Timestamps** | ✅ Yes | ❌ No | ⚠️ Optional | ✅ Yes | ⚠️ Last fetch only |
| **Performance** | ⚠️ Good | ⚠️ Good | ✅ Excellent | ✅ Excellent | ✅ Excellent |
| **Scalability** | ⚠️ Medium | ⚠️ Medium | ✅ High | ✅ High | ✅ High |
| **Implementation Complexity** | ⚠️ Medium | ✅ Simple | ⚠️ Medium | ❌ Complex | ✅ Simple |
| **Analytics Support** | ✅ Excellent | ⚠️ Limited | ❌ None | ✅ Excellent | ❌ None |
| **Data Durability** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes |
| **Mark as Unread** | ✅ Easy | ⚠️ Possible | ✅ Easy | ✅ Easy | ❌ Hard |
| **Storage Cost** | ⚠️ Medium | ⚠️ Medium | ⚠️ Redis RAM | ⚠️ Both | ✅ Minimal |

---

## Recommendations by Use Case

### **Startup/MVP (< 1k users)**
→ **Option 1 (FeedItemView)** - Clean, flexible, room to grow

### **Small-Medium App (1k - 50k users)**
→ **Option 1 (FeedItemView)** - Proven at this scale

### **Large App (50k - 500k users)**
→ **Option 4 (Hybrid)** - Add caching for performance

### **High-Scale App (500k+ users)**
→ **Option 4 (Hybrid)** - Essential for performance

### **Need Simple Solution**
→ **Option 5 (Last Fetch)** - Minimal complexity

### **Don't Need Timestamps**
→ **Option 2 (ManyToMany)** - Django built-in

### **Already Have Redis**
→ **Option 3 or 4** - Leverage existing infrastructure

---

## Recommended Implementation Plan

### Phase 1: Initial Implementation (Week 1)
1. Create `FeedItemView` model (Option 1)
2. Add migration
3. Update `FeedItemSerializer` with `has_viewed` field
4. Add `mark_viewed` endpoint
5. Write tests

### Phase 2: Optimization (Week 2-3)
1. Add `prefetch_related` optimization to queries
2. Add bulk operations for marking multiple items
3. Monitor database performance

### Phase 3: Scaling (Future)
1. Add Redis caching layer (upgrade to Option 4)
2. Implement cache warming on user login
3. Add analytics queries

---

## Database Migration Example

```python
# messaging/migrations/XXXX_add_feed_item_view.py

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0XXX_previous_migration'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeedItemView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('viewed_at', models.DateTimeField(auto_now_add=True)),
                ('feed_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='views', to='messaging.feeditem')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'messaging_feed_item_view',
            },
        ),
        migrations.AddIndex(
            model_name='feeditemview',
            index=models.Index(fields=['user', '-viewed_at'], name='messaging_f_user_id_abc123_idx'),
        ),
        migrations.AddIndex(
            model_name='feeditemview',
            index=models.Index(fields=['feed_item', 'user'], name='messaging_f_feed_it_def456_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='feeditemview',
            unique_together={('feed_item', 'user')},
        ),
    ]
```

---

## Testing Strategy

### Unit Tests
```python
def test_mark_feed_item_as_viewed():
    user = User.objects.create(email='test@example.com')
    feed_item = FeedItem.objects.create(...)

    # Mark as viewed
    view = FeedItemView.objects.create(feed_item=feed_item, user=user)

    assert FeedItemView.objects.filter(feed_item=feed_item, user=user).exists()
    assert view.viewed_at is not None

def test_has_viewed_field_in_serializer():
    user = User.objects.create(email='test@example.com')
    feed_item = FeedItem.objects.create(...)

    # Not viewed yet
    serializer = FeedItemSerializer(feed_item, context={'request': mock_request(user)})
    assert serializer.data['has_viewed'] is False

    # Mark as viewed
    FeedItemView.objects.create(feed_item=feed_item, user=user)

    # Should show as viewed
    serializer = FeedItemSerializer(feed_item, context={'request': mock_request(user)})
    assert serializer.data['has_viewed'] is True
```

### Performance Tests
```python
def test_feed_query_performance():
    # Create 100 feed items
    feed_items = [FeedItem.objects.create(...) for _ in range(100)]

    # Query with prefetch (should be ~1-2 queries)
    with self.assertNumQueries(2):
        queryset = FeedItem.objects.all().prefetch_related(
            Prefetch('views', queryset=FeedItemView.objects.filter(user=user))
        )
        list(queryset)  # Force evaluation
```

---

## Monitoring & Analytics Queries

```python
# Most viewed feed items this week
FeedItemView.objects.filter(
    viewed_at__gte=timezone.now() - timezone.timedelta(days=7)
).values('feed_item__title').annotate(
    view_count=Count('id')
).order_by('-view_count')[:10]

# User engagement metrics
user_views = FeedItemView.objects.filter(user=user).count()
avg_views_per_day = user_views / ((timezone.now() - user.date_joined).days or 1)

# Unread count per group
unread_count = FeedItem.objects.filter(
    group=group,
    is_deleted=False
).exclude(
    views__user=user
).count()
```

---

## Conclusion

**For your use case (Vineyard Group Fellowship backend):**

Start with **Option 1 (FeedItemView model)**:
- ✅ Clean architecture
- ✅ Supports all your requirements
- ✅ Room to optimize later with caching
- ✅ Proven pattern used by major apps
- ✅ Enables future analytics features

When you reach scale (>50k users), upgrade to **Option 4 (Hybrid)** by adding Redis caching layer on top of Option 1.

---

**Implementation Priority:**
1. ✅ Create FeedItemView model
2. ✅ Add has_viewed to serializer
3. ✅ Add mark_viewed endpoint
4. ✅ Write tests
5. ⏳ Add Redis caching (future optimization)
