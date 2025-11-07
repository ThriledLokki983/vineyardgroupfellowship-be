# Messaging App

Group messaging functionality for Vineyard Group Fellowship.

## Phase 1 Models (Current)

### Core Content Models
- **Discussion** - Top-level posts in groups (leaders only)
- **Comment** - Threaded comments on discussions
- **Reaction** - Emoji reactions (👍, ❤️, 🙏, 🔥, 👏, 😊, 💯)
- **FeedItem** - Denormalized feed for performance (auto-populated via signals)
- **CommentHistory** - Edit tracking (accountability)

### Notification Models
- **NotificationPreference** - User notification settings (GDPR/CAN-SPAM compliance)
- **NotificationLog** - Notification tracking (rate limiting, debugging)

## Features

✅ **Discussion Boards** - Category-based discussions
✅ **Threaded Comments** - Reply to comments
✅ **Emoji Reactions** - 7 reaction types
✅ **Edit Window** - 15-minute edit window for comments
✅ **Edit History** - Full accountability
✅ **Soft Delete** - Discussions and comments
✅ **Pinned Posts** - Leaders can pin important discussions
✅ **Performance Optimized** - FeedItem model prevents N+1 queries
✅ **Atomic Counts** - F() expressions prevent race conditions
✅ **Notification Preferences** - Quiet hours, rate limiting
✅ **Feed Caching** - Redis caching with auto-invalidation

## Database Schema

```
messaging_discussion
├── id (UUID, PK)
├── group_id (FK to group.Group)
├── author_id (FK to User)
├── title (varchar 200)
├── content (text)
├── category (varchar 20)
├── comment_count (int)
├── reaction_count (int)
├── is_pinned (bool)
├── is_deleted (bool)
├── created_at, updated_at, deleted_at

messaging_comment
├── id (UUID, PK)
├── discussion_id (FK to Discussion)
├── author_id (FK to User)
├── parent_id (FK to self, nullable)
├── content (text)
├── reaction_count (int)
├── is_edited (bool)
├── edited_at (datetime)
├── is_deleted (bool)
├── created_at, updated_at, deleted_at

messaging_feed_item
├── id (UUID, PK)
├── group_id (FK to Group)
├── content_type (varchar 20: discussion|prayer|testimony|scripture)
├── content_id (UUID)
├── author_id (FK to User)
├── title (varchar 500)
├── preview (text 300)
├── comment_count (int)
├── reaction_count (int)
├── is_pinned (bool)
├── is_deleted (bool)
├── created_at, updated_at
```

## Signals

The app uses Django signals for automatic behavior:

- **FeedItem Auto-Population** - Creates/updates FeedItem when Discussion changes
- **Count Updates** - Atomic increment/decrement via F() expressions
- **Comment History** - Saves previous content before edit
- **Cache Invalidation** - Clears feed cache on content changes

## Admin Interface

All models are registered in Django admin with:
- List displays with key fields
- Filters for common queries
- Search functionality
- Readonly fields for auto-managed data
- Bulk actions (pin/unpin, soft delete)

## Next Steps (Phase 2)

- [ ] PrayerRequest model
- [ ] Testimony model
- [ ] Scripture model
- [ ] Bible API integration
- [ ] Enhanced NotificationService
- [ ] Email templates

## Dependencies

See `requirements.txt` for full list.

Key packages:
- Django 5.2+
- PostgreSQL with PostGIS
- Redis (for caching)
- Celery (for cleanup tasks)

## Testing

Run tests:
```bash
python manage.py test messaging
```

## Performance

- **Feed queries:** < 10 database queries via `select_related()`/`prefetch_related()`
- **Feed caching:** 5-minute TTL, automatic invalidation
- **Target:** < 200ms response time for 1000+ feed items
