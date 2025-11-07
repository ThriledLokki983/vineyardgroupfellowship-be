# Messaging App - Frontend Integration Guide

**Last Updated:** November 6, 2025
**API Version:** 1.0
**Base URL:** `/api/messaging/`

---

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [Discussions](#discussions)
3. [Comments](#comments)
4. [Reactions](#reactions)
5. [Feed](#feed)
6. [Prayer Requests](#prayer-requests)
7. [Testimonies](#testimonies)
8. [Scriptures](#scriptures)
9. [Content Reports](#content-reports)
10. [Notification Preferences](#notification-preferences)
11. [Error Handling](#error-handling)

---

## 🔐 Authentication

**All endpoints require authentication.** Include JWT token in headers:

```
Authorization: Bearer <access_token>
```

**Permissions:**
- `IsAuthenticated` - User must be logged in
- `IsGroupMember` - User must be active member of the group
- `IsAuthorOrReadOnly` - Only author can edit/delete
- `IsGroupLeader` - Leader-only actions (pin, approve, etc.)

---

## 💬 Discussions

### List Discussions
**GET** `/api/messaging/discussions/`

**Query Parameters:**
- `group` (required) - UUID of group
- `is_pinned` - Filter by pinned status (true/false)
- `search` - Search in title and content
- `ordering` - Sort by: `-created_at`, `-updated_at`, `-comment_count`

**Response:**
```json
{
  "count": 25,
  "next": "http://api/messaging/discussions/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "group": "group-uuid",
      "author": {
        "id": "user-uuid",
        "username": "john_doe",
        "first_name": "John",
        "last_name": "Doe"
      },
      "title": "Bible Study This Week",
      "content": "Let's discuss Romans 8...",
      "is_pinned": false,
      "comment_count": 12,
      "reaction_count": 5,
      "created_at": "2025-11-06T10:30:00Z",
      "updated_at": "2025-11-06T15:45:00Z"
    }
  ]
}
```

---

### Create Discussion
**POST** `/api/messaging/discussions/`

**Payload:**
```json
{
  "group": "group-uuid",
  "title": "Bible Study This Week",
  "content": "Let's discuss Romans 8..."
}
```

**Response:** `201 Created`
```json
{
  "id": "new-uuid",
  "group": "group-uuid",
  "author": { "id": "user-uuid", "username": "john_doe" },
  "title": "Bible Study This Week",
  "content": "Let's discuss Romans 8...",
  "is_pinned": false,
  "comment_count": 0,
  "reaction_count": 0,
  "created_at": "2025-11-06T10:30:00Z",
  "updated_at": "2025-11-06T10:30:00Z"
}
```

---

### Get Discussion Detail
**GET** `/api/messaging/discussions/{id}/`

**Response:** Same as create response

---

### Update Discussion
**PATCH** `/api/messaging/discussions/{id}/`

**Payload (partial update):**
```json
{
  "title": "Updated Title",
  "content": "Updated content..."
}
```

**Permissions:** Author only

---

### Delete Discussion
**DELETE** `/api/messaging/discussions/{id}/`

**Response:** `204 No Content`

**Permissions:** Author only

---

### Pin/Unpin Discussion
**POST** `/api/messaging/discussions/{id}/pin/`
**POST** `/api/messaging/discussions/{id}/unpin/`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "is_pinned": true,
  "message": "Discussion pinned successfully"
}
```

**Permissions:** Group leader only

---

## 💭 Comments

### List Comments
**GET** `/api/messaging/comments/`

**Query Parameters:**
- `discussion` - Filter by discussion UUID
- `parent` - Filter by parent comment (for threading)
- `ordering` - Sort by: `created_at`, `-created_at`

**Response:**
```json
{
  "count": 12,
  "results": [
    {
      "id": "uuid",
      "discussion": "discussion-uuid",
      "author": {
        "id": "user-uuid",
        "username": "jane_smith"
      },
      "parent": null,
      "content": "Great point about Romans 8!",
      "is_edited": false,
      "edit_count": 0,
      "created_at": "2025-11-06T11:00:00Z",
      "updated_at": "2025-11-06T11:00:00Z"
    }
  ]
}
```

---

### Create Comment
**POST** `/api/messaging/comments/`

**Payload:**
```json
{
  "discussion": "discussion-uuid",
  "content": "Great point about Romans 8!",
  "parent": null  // Optional: UUID for reply
}
```

**Response:** `201 Created` (same structure as list)

---

### Update Comment
**PATCH** `/api/messaging/comments/{id}/`

**Payload:**
```json
{
  "content": "Updated comment text..."
}
```

**Note:** Comments can be edited within 15 minutes of creation. Edit history is tracked.

---

### Delete Comment
**DELETE** `/api/messaging/comments/{id}/`

**Response:** `204 No Content`

**Permissions:** Author only

---

## ❤️ Reactions

### Add Reaction
**POST** `/api/messaging/reactions/`

**Payload:**
```json
{
  "discussion": "discussion-uuid",
  "reaction_type": "pray"
}
```

**Reaction Types:**
- `like` - 👍 Like
- `love` - ❤️ Love
- `pray` - 🙏 Praying
- `amen` - 🙌 Amen

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "user": "user-uuid",
  "discussion": "discussion-uuid",
  "reaction_type": "pray",
  "created_at": "2025-11-06T12:00:00Z"
}
```

**Note:** One reaction per user per discussion. Creating a new reaction replaces the old one.

---

### Remove Reaction
**DELETE** `/api/messaging/reactions/{id}/`

**Response:** `204 No Content`

---

### List Reactions
**GET** `/api/messaging/reactions/`

**Query Parameters:**
- `discussion` - Filter by discussion UUID
- `reaction_type` - Filter by type

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": "uuid",
      "user": {
        "id": "user-uuid",
        "username": "john_doe"
      },
      "discussion": "discussion-uuid",
      "reaction_type": "pray",
      "created_at": "2025-11-06T12:00:00Z"
    }
  ]
}
```

---

## 📰 Feed

### Get Activity Feed
**GET** `/api/messaging/feed/`

**Query Parameters:**
- `group` (required) - UUID of group
- `content_type` - Filter by type: `discussion`, `prayer_request`, `testimony`, `scripture`

**Response:**
```json
{
  "count": 50,
  "next": "http://api/messaging/feed/?page=2",
  "results": [
    {
      "id": "uuid",
      "group": "group-uuid",
      "content_type": "discussion",
      "content_id": "content-uuid",
      "author": {
        "id": "user-uuid",
        "username": "john_doe"
      },
      "title": "Bible Study This Week",
      "preview": "Let's discuss Romans 8...",
      "comment_count": 12,
      "reaction_count": 5,
      "is_pinned": false,
      "created_at": "2025-11-06T10:30:00Z",
      "updated_at": "2025-11-06T15:45:00Z"
    },
    {
      "id": "uuid",
      "content_type": "prayer_request",
      "title": "🔥 URGENT: Prayer for healing",
      "preview": "Please pray for my friend...",
      "is_pinned": true,
      "created_at": "2025-11-06T09:00:00Z"
    }
  ]
}
```

**Note:** Feed is ordered by pinned first, then by creation date (newest first).

---

## 🙏 Prayer Requests

### List Prayer Requests
**GET** `/api/messaging/prayer-requests/`

**Query Parameters:**
- `group` (required) - UUID of group
- `urgency` - Filter by: `normal`, `urgent`, `critical`
- `category` - Filter by: `personal`, `family`, `health`, `work`, `ministry`, `salvation`, `other`
- `is_answered` - Filter by answered status (true/false)
- `search` - Search in title, content, answer_description
- `ordering` - Sort by: `-urgency`, `-created_at`, `-prayer_count`

**Response:**
```json
{
  "count": 15,
  "results": [
    {
      "id": "uuid",
      "group": "group-uuid",
      "author": {
        "id": "user-uuid",
        "username": "jane_smith"
      },
      "title": "Prayer for healing",
      "content": "Please pray for my friend who is sick...",
      "urgency": "urgent",
      "category": "health",
      "is_answered": false,
      "answer_description": null,
      "answered_at": null,
      "prayer_count": 23,
      "comment_count": 5,
      "created_at": "2025-11-06T08:00:00Z",
      "updated_at": "2025-11-06T14:30:00Z"
    }
  ]
}
```

---

### Create Prayer Request
**POST** `/api/messaging/prayer-requests/`

**Payload:**
```json
{
  "group": "group-uuid",
  "title": "Prayer for healing",
  "content": "Please pray for my friend who is sick...",
  "urgency": "urgent",
  "category": "health"
}
```

**Urgency Levels:**
- `normal` - Regular prayer request
- `urgent` - Needs immediate prayer (auto-pinned in feed)
- `critical` - Emergency prayer need

**Categories:**
- `personal`, `family`, `health`, `work`, `ministry`, `salvation`, `other`

**Response:** `201 Created` (same structure as list)

---

### Mark Prayer as Answered
**PATCH** `/api/messaging/prayer-requests/{id}/mark_answered/`

**Payload:**
```json
{
  "answer_description": "God healed my friend! Praise the Lord!"
}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "is_answered": true,
  "answer_description": "God healed my friend! Praise the Lord!",
  "answered_at": "2025-11-06T16:00:00Z"
}
```

**Permissions:** Author only

---

### Add Prayer (Increment Count)
**POST** `/api/messaging/prayer-requests/{id}/pray/`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "prayer_count": 24,
  "message": "Prayer count incremented"
}
```

---

## 📢 Testimonies

### List Testimonies
**GET** `/api/messaging/testimonies/`

**Query Parameters:**
- `group` (required) - UUID of group
- `is_public` - Filter public testimonies (true/false)
- `is_public_approved` - Filter approved public testimonies
- `answered_prayer` - Filter by linked prayer UUID
- `search` - Search in title and content

**Response:**
```json
{
  "count": 8,
  "results": [
    {
      "id": "uuid",
      "group": "group-uuid",
      "author": {
        "id": "user-uuid",
        "username": "john_doe"
      },
      "title": "God healed my friend",
      "content": "After weeks of prayer, God performed a miracle...",
      "answered_prayer": "prayer-uuid",
      "is_public": true,
      "is_public_approved": true,
      "approved_by": {
        "id": "leader-uuid",
        "username": "group_leader"
      },
      "approved_at": "2025-11-06T15:00:00Z",
      "comment_count": 8,
      "created_at": "2025-11-06T14:00:00Z"
    }
  ]
}
```

---

### Create Testimony
**POST** `/api/messaging/testimonies/`

**Payload:**
```json
{
  "group": "group-uuid",
  "title": "God healed my friend",
  "content": "After weeks of prayer, God performed a miracle...",
  "answered_prayer": "prayer-uuid"  // Optional: link to answered prayer
}
```

**Response:** `201 Created` (same structure as list)

**Note:** Testimonies start as private to group by default.

---

### Request Public Sharing
**PATCH** `/api/messaging/testimonies/{id}/share_public/`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "is_public": true,
  "is_public_approved": false,
  "message": "Testimony submitted for public approval"
}
```

**Permissions:** Author only

**Note:** Requires leader approval before publicly visible.

---

### Approve for Public Sharing
**PATCH** `/api/messaging/testimonies/{id}/approve_public/`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "is_public": true,
  "is_public_approved": true,
  "approved_by": "leader-uuid",
  "approved_at": "2025-11-06T15:00:00Z",
  "message": "Testimony approved for public sharing"
}
```

**Permissions:** Group leader only

---

## 📖 Scriptures

### List Scripture Shares
**GET** `/api/messaging/scriptures/`

**Query Parameters:**
- `group` (required) - UUID of group
- `translation` - Filter by translation: `KJV`, `NIV`, `ESV`, `NLT`, `NKJV`, `NASB`, `MSG`
- `search` - Search in reference, verse_text, reflection

**Response:**
```json
{
  "count": 12,
  "results": [
    {
      "id": "uuid",
      "group": "group-uuid",
      "author": {
        "id": "user-uuid",
        "username": "jane_smith"
      },
      "reference": "John 3:16",
      "verse_text": "For God so loved the world...",
      "translation": "NIV",
      "reflection": "This verse reminds me of God's incredible love...",
      "bible_api_source": "bible-api.com",
      "comment_count": 3,
      "created_at": "2025-11-06T13:00:00Z"
    }
  ]
}
```

---

### Create Scripture Share
**POST** `/api/messaging/scriptures/`

**Payload:**
```json
{
  "group": "group-uuid",
  "reference": "John 3:16",
  "translation": "NIV",
  "reflection": "This verse reminds me of God's incredible love..."
}
```

**Note:** Verse text is automatically fetched from Bible API based on reference.

**Response:** `201 Created` (same structure as list)

---

### Lookup Bible Verse
**GET** `/api/messaging/scriptures/verse_lookup/`

**Query Parameters:**
- `reference` (required) - e.g., "John 3:16"
- `translation` - Default: "KJV"

**Response:** `200 OK`
```json
{
  "reference": "John 3:16",
  "verse_text": "For God so loved the world, that he gave his only begotten Son...",
  "translation": "KJV",
  "source": "bible-api.com"
}
```

**Supported Translations:**
- `KJV` - King James Version
- `NIV` - New International Version
- `ESV` - English Standard Version
- `NLT` - New Living Translation
- `NKJV` - New King James Version
- `NASB` - New American Standard Bible
- `MSG` - The Message

---

## 🚩 Content Reports

### Create Report
**POST** `/api/messaging/reports/`

**Payload:**
```json
{
  "content_type": "discussion",
  "content_id": "discussion-uuid",
  "reason": "inappropriate",
  "description": "This content contains offensive language..."
}
```

**Reason Options:**
- `spam` - Spam or irrelevant content
- `harassment` - Harassment or bullying
- `inappropriate` - Inappropriate content
- `misinformation` - False information
- `other` - Other reason (requires description)

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "reporter": "user-uuid",
  "content_type": "discussion",
  "content_id": "discussion-uuid",
  "reason": "inappropriate",
  "description": "This content contains offensive language...",
  "status": "pending",
  "created_at": "2025-11-06T16:00:00Z"
}
```

---

### List Reports (Leaders Only)
**GET** `/api/messaging/reports/`

**Query Parameters:**
- `status` - Filter by: `pending`, `reviewed`, `resolved`, `dismissed`
- `reason` - Filter by reason

**Permissions:** Group leader only

---

## 🔔 Notification Preferences

### Get User Preferences
**GET** `/api/messaging/preferences/`

**Response:**
```json
{
  "id": "uuid",
  "user": "user-uuid",
  "email_enabled": true,
  "email_new_discussion": true,
  "email_new_comment": true,
  "email_new_reaction": false,
  "email_discussion_pinned": true,
  "email_new_prayer": true,
  "email_urgent_prayer": true,
  "email_prayer_answered": true,
  "email_testimony_shared": true,
  "email_testimony_approved": true,
  "email_scripture_shared": false,
  "quiet_hours_enabled": true,
  "quiet_hours_start": "22:00:00",
  "quiet_hours_end": "08:00:00"
}
```

---

### Update Preferences
**PATCH** `/api/messaging/preferences/`

**Payload (partial update):**
```json
{
  "email_urgent_prayer": false,
  "quiet_hours_start": "23:00:00"
}
```

**Response:** `200 OK` (same structure as GET)

---

## ⚠️ Error Handling

### Standard Error Response
```json
{
  "detail": "Error message here"
}
```

### HTTP Status Codes

**Success:**
- `200 OK` - Request successful
- `201 Created` - Resource created
- `204 No Content` - Deletion successful

**Client Errors:**
- `400 Bad Request` - Invalid payload
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded

**Server Errors:**
- `500 Internal Server Error` - Server error

### Rate Limiting

**Throttle Classes:**
- **Anonymous:** 100 requests/hour
- **Authenticated:** 1000 requests/hour
- **Post Creation:** 10 posts/hour
- **Comment Creation:** 30 comments/hour

**Rate Limit Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 997
X-RateLimit-Reset: 1699286400
```

**Rate Limit Error:**
```json
{
  "detail": "Request was throttled. Expected available in 3600 seconds."
}
```

---

## 🎯 Common Patterns

### Pagination
All list endpoints support pagination:
```
GET /api/messaging/discussions/?page=2&page_size=25
```

**Default:** 25 items per page
**Maximum:** 100 items per page

---

### Filtering & Search
Use query parameters:
```
GET /api/messaging/discussions/?group=uuid&search=bible&is_pinned=true
```

---

### Ordering
Use `ordering` parameter:
```
GET /api/messaging/discussions/?ordering=-created_at
```

Prefix with `-` for descending order.

---

## 📱 Frontend Integration Tips

### 1. **Feed Updates**
Poll the feed endpoint every 30-60 seconds or implement WebSocket for real-time updates.

### 2. **Optimistic UI**
Show immediate feedback (e.g., increment prayer count) before server confirms.

### 3. **Error Handling**
Always handle 401 (reauth), 403 (permission denied), and 429 (rate limit).

### 4. **Caching**
Cache user preferences, group membership, and static data.

### 5. **Offline Support**
Queue actions (comments, reactions) when offline, sync when online.

### 6. **Notifications**
Check notification preferences before showing UI toggles.

---

## 🚀 Quick Start Example

**Fetch group feed with prayer requests:**
```javascript
// 1. Get activity feed
const feed = await fetch('/api/messaging/feed/?group=group-uuid', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// 2. Get prayer requests
const prayers = await fetch('/api/messaging/prayer-requests/?group=group-uuid&urgency=urgent', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// 3. Create new discussion
const discussion = await fetch('/api/messaging/discussions/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    group: 'group-uuid',
    title: 'Bible Study',
    content: 'Let's discuss...'
  })
});

// 4. Add reaction
const reaction = await fetch('/api/messaging/reactions/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    discussion: 'discussion-uuid',
    reaction_type: 'pray'
  })
});
```

---

## 📞 Support

For questions or issues:
- Check API documentation: `/api/schema/` (Swagger UI)
- Backend team contact: [Your contact info]

**Last Updated:** November 6, 2025
