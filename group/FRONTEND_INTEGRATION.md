# Frontend Integration Guide - Group App API

This guide documents all Group API endpoints, request payloads, and response structures for frontend integration.

## Table of Contents
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Endpoints Overview](#endpoints-overview)
- [Endpoint Details](#endpoint-details)
- [Data Models](#data-models)
- [Error Responses](#error-responses)
- [Location-Based Filtering (NEW)](#location-based-filtering-new)

## Authentication

All endpoints require JWT authentication. Include the access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

Get tokens from the authentication endpoints:
- Login: `POST /api/v1/auth/login/`
- Refresh: `POST /api/v1/auth/token/refresh/`

## Base URL

```
Development: http://localhost:8001
Production: https://api.yourdomain.com

All group endpoints: /api/v1/groups/
```

## Endpoints Overview

| Method | Endpoint | Description | Auth Required | Permission |
|--------|----------|-------------|---------------|------------|
| GET | `/` | List all groups | ✅ | Any authenticated user |
| POST | `/` | Create new group | ✅ | User with `can_lead_group` permission |
| GET | `/{id}/` | Get group details | ✅ | Based on visibility settings |
| PATCH | `/{id}/` | Update group | ✅ | Leader or co-leader |
| PUT | `/{id}/` | Update group (full) | ✅ | Leader or co-leader |
| DELETE | `/{id}/` | Delete group | ✅ | Leader only |
| GET | `/{id}/members/` | Get active group members | ✅ | Anyone who can view the group |
| POST | `/{id}/join/` | Request to join group | ✅ | Any authenticated user |
| POST | `/{id}/leave/` | Leave group | ✅ | Current member (not leader) |
| POST | `/{id}/upload_photo/` | Upload group photo | ✅ | Leader or co-leader |
| GET | `/{id}/pending_requests/` | View pending join requests | ✅ | Leader or co-leader |
| POST | `/{id}/approve-request/{membership_id}/` | Approve join request | ✅ | Leader or co-leader |
| POST | `/{id}/reject-request/{membership_id}/` | Reject join request | ✅ | Leader or co-leader |

---

## Endpoint Details

### 1. List Groups

Get a list of all groups visible to the authenticated user.

**Endpoint:** `GET /api/v1/groups/`

**Query Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `location` | string | No | Filter by location (case-insensitive contains) | `?location=downtown` |
| `is_open` | boolean | No | Filter by open/closed status | `?is_open=true` |
| `has_space` | boolean | No | Show only groups with available spots | `?has_space=true` |
| `my_groups` | boolean | No | Show only groups where user is a member, co-leader, leader, or has a pending join request | `?my_groups=true` |
| `nearby` | boolean | No | Filter groups by proximity to user location. Uses user's profile location or provided lat/lng coordinates | `?nearby=true` |
| `radius` | float | No | Search radius in kilometers for nearby groups (default: 5km, max: 10km). Only used when `nearby=true` | `?radius=3` |
| `lat` | float | No | User latitude for location-based search. Overrides profile location when provided | `?lat=38.8977` |
| `lng` | float | No | User longitude for location-based search. Overrides profile location when provided | `?lng=-77.0365` |

**Request Example:**
```http
GET /api/v1/groups/?location=downtown&has_space=true
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Request Example (Get My Groups):**
```http
GET /api/v1/groups/?my_groups=true
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Request Example (Find Nearby Groups):**
```http
# Use user's profile location with default 5km radius
GET /api/v1/groups/?nearby=true
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Find groups within 3km using custom coordinates
GET /api/v1/groups/?nearby=true&radius=3&lat=38.8977&lng=-77.0365
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Combine location filter with other filters
GET /api/v1/groups/?nearby=true&radius=5&is_open=true&has_space=true
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:** `200 OK`

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Young Adults Fellowship",
    "description": "A group for young adults to connect and grow together",
    "location": "Downtown Campus",
    "location_type": "in_person",
    "member_limit": 12,
    "current_member_count": 8,
    "available_spots": 4,
    "is_open": true,
    "is_active": true,
    "leader_info": {
      "id": "user-uuid-1",
      "email": "leader@example.com",
      "display_name": "John Doe"
    },
    "photo_url": "http://localhost:8001/media/group_photos/2024/11/photo.jpg",
    "meeting_day": "wednesday",
    "meeting_time": "19:00:00",
    "meeting_frequency": "weekly",
    "focus_areas": ["worship", "bible_study", "fellowship"],
    "latitude": "38.897700",
    "longitude": "-77.036500",
    "geocoded_address": "1600 Pennsylvania Avenue NW, Washington, DC 20500, USA",
    "distance_km": 2.34,
    "membership_status": null,
    "request_date": null,
    "created_at": "2024-11-01T10:00:00Z"
  },
  {
    "id": "223e4567-e89b-12d3-a456-426614174001",
    "name": "Women's Prayer Group",
    "description": "Weekly prayer and support for women",
    "location": "Online via Zoom",
    "location_type": "virtual",
    "member_limit": 15,
    "current_member_count": 12,
    "available_spots": 3,
    "is_open": true,
    "is_active": true,
    "leader_info": {
      "id": "user-uuid-2",
      "email": "sarah@example.com",
      "display_name": "Sarah Johnson"
    },
    "photo_url": null,
    "meeting_day": "tuesday",
    "meeting_time": "18:00:00",
    "meeting_frequency": "weekly",
    "focus_areas": ["prayer", "women"],
    "membership_status": null,
    "request_date": null,
    "created_at": "2024-10-15T14:30:00Z"
  }
]
```

**Empty Response:** `200 OK`
```json
[]
```

**Field: membership_status**

The `membership_status` field indicates the current user's relationship with each group:

| Value | Description | Use Case |
|-------|-------------|----------|
| `null` | User has no relationship with this group | Show "Join Group" button |
| `"pending"` | User has a pending join request awaiting approval | Show "Request Pending" badge |
| `"active"` | User is an active member | Show "Leave Group" button |
| `"leader"` | User is the group leader | Show "Manage Group" options |
| `"co_leader"` | User is a co-leader | Show "Manage Group" options (limited) |

**Note:** When using `my_groups=true`, the `membership_status` field is especially important to differentiate between active memberships and pending requests.

**Field: request_date**

The `request_date` field shows when the user submitted their join request:

| membership_status | request_date Value | Description |
|------------------|-------------------|-------------|
| `null` | `null` | User has no relationship with this group |
| `"pending"` | ISO 8601 datetime | Timestamp when join request was submitted |
| `"active"` | ISO 8601 datetime | Timestamp when membership was created (or approved from pending) |
| `"leader"` | `null` | Leaders don't have a request date |
| `"co_leader"` | `null` | Co-leaders don't have a request date |

**Usage Example:**
```javascript
// Calculate how long a request has been pending
if (group.membership_status === 'pending' && group.request_date) {
  const requestDate = new Date(group.request_date);
  const now = new Date();
  const daysPending = Math.floor((now - requestDate) / (1000 * 60 * 60 * 24));

  console.log(`Request pending for ${daysPending} days`);
  // Show "Pending for 3 days" badge
}
```

---

### 2. Create Group

Create a new fellowship group. Requires leadership permission.

**Endpoint:** `POST /api/v1/groups/`

**Prerequisites:**
- User must have `leadership_info.can_lead_group: true` in their profile
- User must not have an existing active or pending group membership
- Check via: `GET /api/v1/profiles/me/` → Verify `leadership_info.can_lead_group === true` and `leadership_info.group === null`

**Request Body:**

```json
{
  "name": "Young Adults Fellowship",
  "description": "A group for young adults to connect and grow together",
  "location": "Downtown Campus",
  "location_type": "in_person",
  "member_limit": 12,
  "is_open": true,
  "meeting_day": "wednesday",
  "meeting_time": "19:00:00",
  "meeting_frequency": "weekly",
  "focus_areas": ["worship", "bible_study", "fellowship"],
  "visibility": "public"
}
```

**Field Specifications:**

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `name` | string | ✅ Yes | Max 200 chars | - |
| `description` | string | No | Unlimited | Empty string |
| `location` | string | No | Max 255 chars | Empty string |
| `location_type` | string | No | Choices: `in_person`, `virtual`, `hybrid` | - |
| `member_limit` | integer | No | Min: 2, Max: 100 | 12 |
| `is_open` | boolean | No | - | true |
| `meeting_day` | string | No | Choices: `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday` | - |
| `meeting_time` | string | No | Format: `HH:MM:SS` | - |
| `meeting_frequency` | string | No | Choices: `weekly`, `biweekly`, `monthly` | - |
| `focus_areas` | array | No | Array of strings | `[]` |
| `visibility` | string | No | Choices: `public`, `community`, `private` | `public` |

**Response:** `201 Created`

```json
{
  "id": "323e4567-e89b-12d3-a456-426614174002",
  "name": "Young Adults Fellowship",
  "description": "A group for young adults to connect and grow together",
  "location": "Downtown Campus",
  "location_type": "in_person",
  "member_limit": 12,
  "current_member_count": 1,
  "is_full": false,
  "available_spots": 11,
  "is_open": true,
  "is_active": true,
  "can_accept_members": true,
  "leader": "current-user-uuid",
  "leader_info": {
    "id": "current-user-uuid",
    "email": "you@example.com",
    "display_name": "Your Name"
  },
  "co_leaders": [],
  "co_leaders_info": [],
  "photo": null,
  "photo_url": null,
  "meeting_day": "wednesday",
  "meeting_time": "19:00:00",
  "meeting_frequency": "weekly",
  "focus_areas": ["worship", "bible_study", "fellowship"],
  "visibility": "public",
  "user_membership": {
    "id": "membership-uuid",
    "role": "leader",
    "status": "active",
    "joined_at": "2024-11-01T15:00:00Z"
  },
  "created_at": "2024-11-01T15:00:00Z",
  "updated_at": "2024-11-01T15:00:00Z"
}
```

**Error Response:** `400 Bad Request`

```json
{
  "detail": "You do not have permission to create groups. Please complete leadership onboarding first."
}
```

---

### 3. Get Group Details

Get detailed information about a specific group.

**Endpoint:** `GET /api/v1/groups/{id}/`

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Group ID |

**Request Example:**
```http
GET /api/v1/groups/123e4567-e89b-12d3-a456-426614174000/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:** `200 OK`

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Young Adults Fellowship",
  "description": "A group for young adults to connect and grow together",
  "location": "Downtown Campus",
  "location_type": "in_person",
  "member_limit": 12,
  "current_member_count": 8,
  "is_full": false,
  "available_spots": 4,
  "is_open": true,
  "is_active": true,
  "can_accept_members": true,
  "leader": "user-uuid-1",
  "leader_info": {
    "id": "user-uuid-1",
    "email": "leader@example.com",
    "display_name": "John Doe"
  },
  "co_leaders": ["user-uuid-2", "user-uuid-3"],
  "co_leaders_info": [
    {
      "id": "user-uuid-2",
      "email": "coleader1@example.com",
      "display_name": "Jane Smith"
    },
    {
      "id": "user-uuid-3",
      "email": "coleader2@example.com",
      "display_name": "Mike Johnson"
    }
  ],
  "photo": "group_photos/2024/11/photo.jpg",
  "photo_url": "http://localhost:8001/media/group_photos/2024/11/photo.jpg",
  "meeting_day": "wednesday",
  "meeting_time": "19:00:00",
  "meeting_frequency": "weekly",
  "focus_areas": ["worship", "bible_study", "fellowship"],
  "visibility": "public",
  "user_membership": {
    "id": "membership-uuid",
    "role": "member",
    "status": "active",
    "joined_at": "2024-10-20T12:00:00Z"
  },
  "created_at": "2024-11-01T10:00:00Z",
  "updated_at": "2024-11-01T10:00:00Z"
}
```

**Notes:**
- `user_membership` will be `null` if the authenticated user is not a member
- `photo_url` will be `null` if no photo has been uploaded
- `co_leaders_info` will be empty array if no co-leaders assigned

**Error Response:** `404 Not Found`

```json
{
  "detail": "Not found."
}
```

---

### 4. Update Group

Update group details. Only leader and co-leaders can update.

**Endpoint:** `PATCH /api/v1/groups/{id}/` (partial update)
**Alternative:** `PUT /api/v1/groups/{id}/` (full update)

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Group ID |

**Request Body (PATCH - all fields optional):**

```json
{
  "description": "Updated description with more details",
  "meeting_time": "20:00:00",
  "meeting_frequency": "biweekly",
  "is_open": false
}
```

**Request Body (PUT - all create fields required):**

Same as create endpoint, all fields must be provided.

**Response:** `200 OK`

Returns the updated group object (same structure as Get Group Details).

**Error Response:** `403 Forbidden`

```json
{
  "detail": "Only group leaders can update group details."
}
```

---

### 5. Delete Group

Soft delete a group (sets `is_active` to false). Only the group leader can delete.

**Endpoint:** `DELETE /api/v1/groups/{id}/`

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Group ID |

**Request Example:**
```http
DELETE /api/v1/groups/123e4567-e89b-12d3-a456-426614174000/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:** `204 No Content`

No response body.

**Error Response:** `403 Forbidden`

```json
{
  "detail": "Only the group leader can delete this group."
}
```

---

### 6. Get Group Members

Get a list of all active members in a group.

**Endpoint:** `GET /api/v1/groups/{id}/members/`

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Group ID |

**Request Example:**
```http
GET /api/v1/groups/123e4567-e89b-12d3-a456-426614174000/members/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:** `200 OK`

```json
[
  {
    "id": "membership-uuid-1",
    "user_id": "user-uuid-1",
    "email": "leader@example.com",
    "display_name": "John Doe",
    "role": "leader",
    "status": "active",
    "joined_at": "2024-11-01T10:00:00Z"
  },
  {
    "id": "membership-uuid-2",
    "user_id": "user-uuid-2",
    "email": "coleader@example.com",
    "display_name": "Jane Smith",
    "role": "co_leader",
    "status": "active",
    "joined_at": "2024-11-02T14:00:00Z"
  },
  {
    "id": "membership-uuid-3",
    "user_id": "user-uuid-3",
    "email": "member1@example.com",
    "display_name": "Mike Johnson",
    "role": "member",
    "status": "active",
    "joined_at": "2024-11-05T09:30:00Z"
  },
  {
    "id": "membership-uuid-4",
    "user_id": "user-uuid-4",
    "email": "member2@example.com",
    "display_name": "Sarah Williams",
    "role": "member",
    "status": "active",
    "joined_at": "2024-11-08T16:45:00Z"
  }
]
```

**Notes:**
- Only returns members with `status: "active"`
- Results are ordered by role (leader, co_leader, member) then by join date
- Empty array if no members

---

### 7. Join Group

Request to join a group. **All join requests require leader approval** and are initially set to `pending` status.

**Endpoint:** `POST /api/v1/groups/{id}/join/`

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Group ID |

**Request Body (optional):**

```json
{
  "message": "I'd love to join your group! I'm passionate about worship and fellowship."
}
```

**Field Specifications:**

| Field | Type | Required | Max Length |
|-------|------|----------|------------|
| `message` | string | No | 500 chars |

**Request Example (no message):**
```http
POST /api/v1/groups/123e4567-e89b-12d3-a456-426614174000/join/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{}
```

**Request Example (with message):**
```http
POST /api/v1/groups/123e4567-e89b-12d3-a456-426614174000/join/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "message": "I'd love to join your group!"
}
```

**Response:** `200 OK`

```json
{
  "message": "Join request submitted successfully. Awaiting leader approval.",
  "membership": {
    "id": "new-membership-uuid",
    "user_id": "current-user-uuid",
    "email": "you@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "Your Name",
    "bio": "Passionate about worship and fellowship",
    "photo_url": "http://localhost:8001/media/profile_photos/2024/11/photo.jpg",
    "profile_visibility": "public",
    "role": "member",
    "status": "pending",
    "joined_at": "2024-11-01T15:30:00Z"
  }
}
```

**Error Response:** `400 Bad Request` (Already a member)

```json
{
  "error": "You are already a member of this group."
}
```

**Error Response:** `400 Bad Request` (Pending request exists)

```json
{
  "error": "You already have a pending request for this group."
}
```

**Error Response:** `400 Bad Request` (Group full)

```json
{
  "error": "This group is not accepting new members."
}
```

---

### 8. Leave Group

Leave a group you are a member of. Leaders cannot leave.

**Endpoint:** `POST /api/v1/groups/{id}/leave/`

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Group ID |

**Request Example:**
```http
POST /api/v1/groups/123e4567-e89b-12d3-a456-426614174000/leave/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**No request body required.**

**Response:** `200 OK`

```json
{
  "message": "Successfully left group."
}
```

**Error Response:** `400 Bad Request` (Not a member)

```json
{
  "error": "You are not a member of this group."
}
```

**Error Response:** `400 Bad Request` (User is leader)

```json
{
  "error": "Group leader cannot leave. Please transfer leadership first or delete the group."
}
```

---

### 9. Upload Group Photo

Upload a photo for the group. Only leaders and co-leaders can upload.

**Endpoint:** `POST /api/v1/groups/{id}/upload_photo/`

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Group ID |

**Request:**

Content-Type: `multipart/form-data`

**Form Data:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `photo` | file | ✅ Yes | Image file (JPEG, PNG, etc.), Max 2MB |

**Request Example:**
```http
POST /api/v1/groups/123e4567-e89b-12d3-a456-426614174000/upload_photo/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="photo"; filename="group-photo.jpg"
Content-Type: image/jpeg

[binary image data]
------WebKitFormBoundary--
```

**Response:** `200 OK`

Returns the updated group object with new `photo` and `photo_url` fields (same structure as Get Group Details).

**Error Response:** `400 Bad Request` (No file)

```json
{
  "error": "No photo file provided."
}
```

**Error Response:** `403 Forbidden` (Not leader/co-leader)

```json
{
  "error": "Only group leaders can upload photos."
}
```

---

### 10. View Pending Join Requests

View all pending membership requests for a group. Only accessible by group leaders and co-leaders.

**Endpoint:** `GET /api/v1/groups/{id}/pending_requests/`

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Group ID |

**Request Example:**
```http
GET /api/v1/groups/123e4567-e89b-12d3-a456-426614174000/pending_requests/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:** `200 OK`

```json
[
  {
    "id": "membership-uuid-1",
    "user_id": "user-uuid-1",
    "email": "john.doe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "JohnDoe",
    "bio": "Passionate about worship and fellowship",
    "photo_url": "http://localhost:8001/media/profile_photos/2024/11/photo.jpg",
    "profile_visibility": "public",
    "role": "member",
    "status": "pending",
    "joined_at": "2024-11-01T15:30:00Z"
  },
  {
    "id": "membership-uuid-2",
    "user_id": "user-uuid-2",
    "email": "jane.smith@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "display_name": "JaneSmith",
    "bio": "Seeking spiritual growth and community",
    "photo_url": null,
    "profile_visibility": "community",
    "role": "member",
    "status": "pending",
    "joined_at": "2024-11-01T16:45:00Z"
  }
]
```

**Error Response:** `403 Forbidden` (Not leader/co-leader)

```json
{
  "error": "Only group leaders can view pending membership requests."
}
```

---

### 11. Approve Join Request

Approve a pending membership request. Only accessible by group leaders and co-leaders.

**Endpoint:** `POST /api/v1/groups/{id}/approve-request/{membership_id}/`

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Group ID |
| `membership_id` | UUID | Membership request ID |

**Request Example:**
```http
POST /api/v1/groups/123e4567-e89b-12d3-a456-426614174000/approve-request/membership-uuid-1/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

**Response:** `200 OK`

```json
{
  "message": "Membership request approved for john.doe@example.com.",
  "membership": {
    "id": "membership-uuid-1",
    "user_id": "user-uuid-1",
    "email": "john.doe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "JohnDoe",
    "bio": "Passionate about worship and fellowship",
    "photo_url": "http://localhost:8001/media/profile_photos/2024/11/photo.jpg",
    "profile_visibility": "public",
    "role": "member",
    "status": "active",
    "joined_at": "2024-11-01T15:30:00Z"
  }
}
```

**Error Response:** `400 Bad Request` (Group is full)

```json
{
  "error": "Cannot approve request. Group is full."
}
```

**Error Response:** `400 Bad Request` (Request not found)

```json
{
  "error": "Pending membership request not found."
}
```

**Error Response:** `403 Forbidden` (Not leader/co-leader)

```json
{
  "error": "Only group leaders can approve membership requests."
}
```

---

### 12. Reject Join Request

Reject a pending membership request. Only accessible by group leaders and co-leaders.

**Endpoint:** `POST /api/v1/groups/{id}/reject-request/{membership_id}/`

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Group ID |
| `membership_id` | UUID | Membership request ID |

**Request Example:**
```http
POST /api/v1/groups/123e4567-e89b-12d3-a456-426614174000/reject-request/membership-uuid-2/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

**Response:** `200 OK`

```json
{
  "message": "Membership request rejected for jane.smith@example.com."
}
```

**Error Response:** `400 Bad Request` (Request not found)

```json
{
  "error": "Pending membership request not found."
}
```

**Error Response:** `403 Forbidden` (Not leader/co-leader)

```json
{
  "error": "Only group leaders can reject membership requests."
}
```

---

## Data Models

### Group Object (Full)

```typescript
{
  id: string (UUID)
  name: string (max 200 chars)
  description: string
  location: string (max 255 chars)
  location_type: "in_person" | "virtual" | "hybrid"
  member_limit: number (2-100)
  current_member_count: number (computed)
  is_full: boolean (computed)
  available_spots: number (computed)
  is_open: boolean
  is_active: boolean
  can_accept_members: boolean (computed)
  leader: string (UUID)
  leader_info: LeaderInfo
  co_leaders: string[] (array of UUIDs)
  co_leaders_info: LeaderInfo[]
  photo: string | null (relative path)
  photo_url: string | null (full URL)
  meeting_day: "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday"
  meeting_time: string (HH:MM:SS format)
  meeting_frequency: "weekly" | "biweekly" | "monthly"
  focus_areas: string[]
  visibility: "public" | "community" | "private"

  // Location-based fields (NEW)
  latitude: string | null (decimal, 9 digits, 6 decimal places)
  longitude: string | null (decimal, 9 digits, 6 decimal places)
  geocoded_address: string (full address from geocoding service)
  distance_km: number | null (distance from user in kilometers, only present when using nearby filter)

  user_membership: UserMembership | null
  group_members: GroupMember[] (all active members including leader)
  created_at: string (ISO 8601 datetime)
  updated_at: string (ISO 8601 datetime)
}
```

### Group Object (List View)

```typescript
{
  id: string (UUID)
  name: string
  description: string
  location: string
  location_type: "in_person" | "virtual" | "hybrid"
  member_limit: number
  current_member_count: number
  available_spots: number
  is_open: boolean
  is_active: boolean
  leader_info: LeaderInfo
  photo_url: string | null
  meeting_day: string
  meeting_time: string
  meeting_frequency: string
  focus_areas: string[]

  // Location-based fields (NEW)
  latitude: string | null
  longitude: string | null
  geocoded_address: string
  distance_km: number | null (only present when using nearby filter, sorted by distance ascending)

  membership_status: "leader" | "co_leader" | "active" | "pending" | null
  request_date: string | null (ISO 8601 datetime)
  created_at: string
}
```

### LeaderInfo Object

```typescript
{
  id: string (UUID)
  email: string
  display_name: string
}
```

### UserMembership Object

```typescript
{
  id: string (UUID)
  role: "leader" | "co_leader" | "member"
  status: "pending" | "active" | "inactive" | "removed"
  joined_at: string (ISO 8601 datetime)
}
```

### GroupMember Object

```typescript
{
  id: string (UUID - membership ID)
  user_id: string (UUID)
  email: string
  first_name: string
  last_name: string
  display_name: string
  bio: string
  photo_url: string | null (full URL to profile photo)
  profile_visibility: "private" | "community" | "public"
  role: "leader" | "co_leader" | "member"
  status: "pending" | "active" | "inactive" | "removed"
  joined_at: string (ISO 8601 datetime)
}
```

**Note:** The `group_members` field in the Group Object (Full) contains an array of GroupMember objects with all active members, including the group leader.

---

## Error Responses

### Standard Error Format

All error responses follow this structure:

```json
{
  "detail": "Error message here"
}
```

or

```json
{
  "error": "Error message here"
}
```

### HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| `200` | OK | Successful GET/POST/PATCH request |
| `201` | Created | Successful resource creation |
| `204` | No Content | Successful DELETE request |
| `400` | Bad Request | Invalid data, validation errors, business logic violations |
| `401` | Unauthorized | Missing or invalid authentication token |
| `403` | Forbidden | Valid auth but insufficient permissions |
| `404` | Not Found | Resource doesn't exist |
| `500` | Internal Server Error | Server-side error |

### Common Error Scenarios

**Authentication Errors:**

```json
// Missing token
{
  "detail": "Authentication credentials were not provided."
}

// Invalid/expired token
{
  "detail": "Given token not valid for any token type"
}
```

**Permission Errors:**

```json
// No leadership permission
{
  "detail": "You do not have permission to create groups. Please complete leadership onboarding first."
}

// Not group leader/co-leader
{
  "detail": "Only group leaders can update group details."
}

// Not group leader
{
  "detail": "Only the group leader can delete this group."
}
```

**Validation Errors:**

```json
// Missing required field
{
  "name": ["This field is required."]
}

// Invalid choice
{
  "location_type": ["\"invalid\" is not a valid choice."]
}

// Invalid member limit
{
  "member_limit": ["Ensure this value is less than or equal to 100."]
}
```

**Business Logic Errors:**

```json
// Already a member
{
  "error": "You are already a member of this group."
}

// Group full
{
  "error": "This group is not accepting new members."
}

// Leader trying to leave
{
  "error": "Group leader cannot leave. Please transfer leadership first or delete the group."
}
```

---

## Field Constraints Reference

### String Fields

| Field | Max Length | Required |
|-------|------------|----------|
| `name` | 200 | Yes (on create) |
| `description` | Unlimited | No |
| `location` | 255 | No |
| `message` (join request) | 500 | No |

### Choice Fields

| Field | Valid Options |
|-------|---------------|
| `location_type` | `in_person`, `virtual`, `hybrid` |
| `meeting_day` | `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday` |
| `meeting_frequency` | `weekly`, `biweekly`, `monthly` |
| `visibility` | `public`, `community`, `private` |
| `role` | `leader`, `co_leader`, `member` |
| `status` | `pending`, `active`, `inactive`, `removed` |

### Numeric Fields

| Field | Min | Max | Default |
|-------|-----|-----|---------|
| `member_limit` | 2 | 100 | 12 |

### Date/Time Fields

| Field | Format |
|-------|--------|
| `meeting_time` | `HH:MM:SS` (24-hour) |
| `created_at` | ISO 8601 (e.g., `2024-11-01T10:00:00Z`) |
| `updated_at` | ISO 8601 |
| `joined_at` | ISO 8601 |

### File Upload

| Field | Type | Max Size | Allowed Types |
|-------|------|----------|---------------|
| `photo` | Image | 2MB | JPEG, PNG, GIF, etc. |

---

## Related Endpoints

### Get Current User Profile

Get the current authenticated user's profile, including their group membership status.

**Endpoint:** `GET /api/v1/profiles/me/`

**Request Example:**
```http
GET /api/v1/profiles/me/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:** `200 OK`

```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "display_name": "John Doe",
  "first_name": "John",
  "last_name": "Doe",
  "bio": "Passionate about worship and fellowship",
  "location": "Downtown Area",
  "post_code": "12345",
  "profile_visibility": "public",
  "photo_url": "http://localhost:8001/media/profile_photos/2024/11/photo.jpg",
  "leadership_info": {
    "can_lead_group": false,
    "group": {
      "id": "group-uuid",
      "name": "Young Adults Fellowship",
      "description": "A group for young adults to connect and grow together",
      "location": "Downtown Campus",
      "location_type": "in_person",
      "meeting_time": "19:00:00",
      "is_open": true,
      "current_member_count": 8,
      "member_limit": 12,
      "available_spots": 4,
      "photo_url": "http://localhost:8001/media/group_photos/2024/11/photo.jpg",
      "my_role": "member",
      "created_by_me": false,
      "last_updated_by": {
        "id": "leader-uuid",
        "email": "leader@example.com",
        "display_name": "Jane Leader"
      },
      "joined_at": "2024-11-01T15:30:00Z",
      "membership_status": "pending",
      "request_submitted_at": "2024-11-01T15:30:00Z"
    }
  },
  "created_at": "2024-10-01T10:00:00Z",
  "updated_at": "2024-11-01T15:30:00Z"
}
```

**Response (No Group):**
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "display_name": "John Doe",
  "first_name": "John",
  "last_name": "Doe",
  "bio": "",
  "location": "",
  "post_code": "",
  "profile_visibility": "private",
  "photo_url": null,
  "leadership_info": {
    "can_lead_group": false,
    "group": null
  },
  "created_at": "2024-10-01T10:00:00Z",
  "updated_at": "2024-10-01T10:00:00Z"
}
```

**Response (Active Group Member):**
```json
{
  "leadership_info": {
    "can_lead_group": false,
    "group": {
      "id": "group-uuid",
      "name": "Young Adults Fellowship",
      "membership_status": "active",
      "my_role": "member",
      "joined_at": "2024-10-15T12:00:00Z"
    }
  }
}
```

**Response (Group Leader):**
```json
{
  "leadership_info": {
    "can_lead_group": true,
    "group": {
      "id": "group-uuid",
      "name": "Young Adults Fellowship",
      "membership_status": "active",
      "my_role": "leader",
      "created_by_me": true,
      "joined_at": "2024-09-01T10:00:00Z"
    }
  }
}
```

### leadership_info.group Field

The `group` field in `leadership_info` shows the user's current group status:

| membership_status | Description | group Value |
|------------------|-------------|-------------|
| `null` | User has no group | `null` |
| `"pending"` | User has requested to join, awaiting approval | Group object with `request_submitted_at` |
| `"active"` | User is an active member | Group object with full details |

**Important Notes:**
- ✅ Users can only have **ONE** group at a time (either active or pending)
- ✅ If `membership_status: "pending"`, the group shows the join request details
- ✅ The `request_submitted_at` field only appears for pending requests
- ✅ Check `membership_status` to determine UI state (show "Pending Approval" vs "Member")

---

## Quick Reference

```
BASE: /api/v1/groups/

LIST:       GET    /                                   → Group[]
CREATE:     POST   /                                   → Group
DETAIL:     GET    /{id}/                              → Group
UPDATE:     PATCH  /{id}/                              → Group
DELETE:     DELETE /{id}/                              → 204
MEMBERS:    GET    /{id}/members/                      → GroupMember[] (active only)
JOIN:       POST   /{id}/join/                         → {message, membership}
LEAVE:      POST   /{id}/leave/                        → {message}
PHOTO:      POST   /{id}/upload_photo/                 → Group
PENDING:    GET    /{id}/pending_requests/             → GroupMember[] (pending only)
APPROVE:    POST   /{id}/approve-request/{m_id}/       → {message, membership}
REJECT:     POST   /{id}/reject-request/{m_id}/        → {message}

Auth: Bearer token required for all endpoints
```

---

## Join Request Workflow

### For Members (Users wanting to join):

1. **Request to Join**
   ```
   POST /api/v1/groups/{id}/join/
   → Returns membership with status: "pending"
   → Message: "Join request submitted successfully. Awaiting leader approval."
   ```

2. **Check Status**
   ```
   GET /api/v1/groups/{id}/
   → Look at user_membership.status field
   → "pending" = waiting for approval
   → "active" = approved and can participate
   ```

3. **After Approval**
   - Status changes to "active"
   - User appears in /members/ endpoint
   - User appears in group_members array of group details

### For Leaders (Approving/Rejecting requests):

1. **View Pending Requests**
   ```
   GET /api/v1/groups/{id}/pending_requests/
   → Returns array of all pending membership requests
   → Each request includes user details and profile photo
   ```

2. **Approve a Request**
   ```
   POST /api/v1/groups/{id}/approve-request/{membership_id}/
   → Changes status from "pending" to "active"
   → User becomes a full member
   → Checks group capacity before approving
   ```

3. **Reject a Request**
   ```
   POST /api/v1/groups/{id}/reject-request/{membership_id}/
   → Deletes the membership request
   → User can request to join another group
   ```

### Important Notes:

- ✅ **All join requests require leader approval** (no auto-approval)
- ✅ Only **active** members appear in the members list
- ✅ Pending requests are only visible to leaders/co-leaders
- ✅ Users cannot join if they already have a pending request
- ✅ Group capacity is checked before approving requests
- ✅ Both leaders and co-leaders can approve/reject requests

### Viewing Your Pending Requests:

Users can check their pending group requests in two ways:

**1. Using the my_groups filter:**
```http
GET /api/v1/groups/?my_groups=true
→ Returns all groups where user is a leader, co-leader, active member, OR has a pending request
```

**2. Using the profiles/me endpoint:**
```http
GET /api/v1/profiles/me/
→ Returns user profile with leadership_info.group showing pending status
→ Check if leadership_info.group.membership_status === "pending"
```

**Recommended Approach:**
- Use `GET /api/v1/groups/?my_groups=true` to show a **list of all user's groups** (including pending)
- Use `GET /api/v1/profiles/me/` to display **current group status** in user profile/dashboard
- Both endpoints include `membership_status` field to differentiate pending vs active

---

## Security Considerations

### Server-Side Validation

All leadership-protected endpoints implement **multi-layer server-side validation** that cannot be bypassed by frontend manipulation:

#### Protected Endpoints:
- `GET /{id}/pending_requests/` - View pending requests
- `POST /{id}/approve-request/{membership_id}/` - Approve requests
- `POST /{id}/reject-request/{membership_id}/` - Reject requests
- `POST /{id}/upload_photo/` - Upload group photo

#### Security Layers:

**1. Primary Leader Verification**
```
Checks if user.id matches group.leader_id directly in the database
```

**2. Co-Leader Verification**
```
Database query: group.co_leaders.filter(id=user.id).exists()
Cannot be spoofed or manipulated from frontend
```

**3. Active Membership Cross-Check**
```
Verifies user has active leadership membership in GroupMembership table
Additional verification layer for data consistency
```

**4. Group Ownership Validation**
```
Double-checks that membership.group.id matches the requested group.id
Prevents cross-group manipulation attacks
```

#### What This Means for Frontend Development:

✅ **Do not rely solely on frontend permission checks**
- The backend will always verify leadership status against the database
- Even if you hide UI elements, the API will reject unauthorized requests

✅ **Handle 403 Forbidden responses gracefully**
- User might lose leadership status while viewing the page
- Token manipulation attempts will be rejected
- Show appropriate error messages to users

✅ **Validation order in approve/reject requests:**
1. Leadership verification (403 if fails)
2. Membership existence check (400 if not found)
3. Group ownership validation (400 if mismatch)
4. Status verification (400 if not pending)
5. Capacity check for approvals (400 if group full)

#### Example Error Responses:

**Unauthorized leadership action:**
```json
{
  "error": "Only group leaders and co-leaders can approve membership requests."
}
```
**Status:** `403 Forbidden`

**Invalid membership request:**
```json
{
  "error": "Pending membership request not found."
}
```
**Status:** `400 Bad Request`

**Cross-group manipulation attempt:**
```json
{
  "error": "Invalid membership request for this group."
}
```
**Status:** `400 Bad Request`

**Group at capacity:**
```json
{
  "error": "Cannot approve request. Group is full."
}
```
**Status:** `400 Bad Request`

### Best Practices:

1. **Always validate responses** - Check for both 4xx and 2xx status codes
2. **Refresh group data** - After approve/reject actions, fetch updated group data
3. **Handle edge cases** - User might approve the last spot while another leader is viewing
4. **Show loading states** - API validates multiple conditions, may take time
5. **Implement optimistic updates carefully** - Revert if backend validation fails

---

## Location-Based Filtering (NEW)

### Overview

The Group API now supports location-based filtering to help users find groups near them. This feature uses PostGIS for efficient geographic queries and integrates with the Nominatim geocoding service.

### How It Works

1. **User Location**: Can come from user's profile or be provided explicitly via query params
2. **Distance Calculation**: Groups are filtered by distance from user's location
3. **Radius Control**: Frontend can specify search radius (default: 5km, max: 10km)
4. **Sorted Results**: Groups are automatically sorted by distance (closest first)
5. **Distance Display**: Each group includes `distance_km` field showing kilometers from user

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `nearby` | boolean | Yes | - | Enable location-based filtering |
| `radius` | float | No | 5.0 | Search radius in kilometers (max: 10km) |
| `lat` | float | Conditional | - | User's latitude (required if no profile location) |
| `lng` | float | Conditional | - | User's longitude (required if no profile location) |

### Usage Examples

#### Example 1: Use Profile Location (Default 5km)

```javascript
// Assuming user has location in their profile
const response = await fetch('/api/v1/groups/?nearby=true', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});

const groups = await response.json();
// Groups sorted by distance, each with distance_km field
```

#### Example 2: Custom Radius

```javascript
// Find groups within 3km using profile location
const response = await fetch('/api/v1/groups/?nearby=true&radius=3', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});
```

#### Example 3: Custom Coordinates

```javascript
// Use specific coordinates (e.g., from browser geolocation API)
navigator.geolocation.getCurrentPosition(async (position) => {
  const { latitude, longitude } = position.coords;

  const response = await fetch(
    `/api/v1/groups/?nearby=true&lat=${latitude}&lng=${longitude}&radius=5`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );

  const groups = await response.json();
});
```

#### Example 4: Combine with Other Filters

```javascript
// Find nearby groups that are open and have space
const params = new URLSearchParams({
  nearby: 'true',
  radius: '5',
  is_open: 'true',
  has_space: 'true'
});

const response = await fetch(`/api/v1/groups/?${params}`, {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});
```

### Response Structure

When using `nearby=true`, each group in the response includes:

```typescript
{
  // ... all standard group fields
  latitude: "38.897700",
  longitude: "-77.036500",
  geocoded_address: "1600 Pennsylvania Avenue NW, Washington, DC 20500, USA",
  distance_km: 2.34  // Distance from user's location in kilometers
}
```

**Response Example:**

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Downtown Fellowship",
    "location": "123 Main St, Downtown",
    "latitude": "38.897700",
    "longitude": "-77.036500",
    "geocoded_address": "123 Main Street, Washington, DC 20001, USA",
    "distance_km": 0.85,
    "is_open": true,
    "current_member_count": 8,
    "available_spots": 4
  },
  {
    "id": "223e4567-e89b-12d3-a456-426614174001",
    "name": "Westside Group",
    "location": "456 West Ave",
    "latitude": "38.912300",
    "longitude": "-77.045600",
    "geocoded_address": "456 West Avenue, Washington, DC 20015, USA",
    "distance_km": 2.34,
    "is_open": true,
    "current_member_count": 10,
    "available_spots": 2
  }
]
```

### Frontend Implementation Guide

#### 1. Get User's Location

```javascript
// Option A: Use browser geolocation
async function getUserLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation not supported'));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        });
      },
      (error) => reject(error),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  });
}

// Option B: Use profile location (already stored in backend)
async function getNearbyGroups() {
  const response = await fetch('/api/v1/groups/?nearby=true&radius=5', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
}
```

#### 2. Display Distance to User

```javascript
// React component example
function GroupCard({ group }) {
  return (
    <div className="group-card">
      <h3>{group.name}</h3>
      <p>{group.description}</p>

      {/* Show distance if available */}
      {group.distance_km !== null && (
        <div className="distance-badge">
          📍 {group.distance_km} km away
        </div>
      )}

      <div className="location">
        {group.geocoded_address || group.location}
      </div>
    </div>
  );
}
```

#### 3. Map Integration

```javascript
// Example with Google Maps or Mapbox
function GroupMap({ groups }) {
  const mapRef = useRef(null);

  useEffect(() => {
    if (!mapRef.current || !groups.length) return;

    // Add markers for each group
    groups.forEach(group => {
      if (group.latitude && group.longitude) {
        new google.maps.Marker({
          position: {
            lat: parseFloat(group.latitude),
            lng: parseFloat(group.longitude)
          },
          map: mapRef.current,
          title: group.name,
          label: {
            text: `${group.distance_km} km`,
            color: 'white'
          }
        });
      }
    });
  }, [groups]);

  return <div ref={mapRef} className="map-container" />;
}
```

#### 4. Radius Slider UI

```javascript
function NearbyGroupsFilter({ onRadiusChange }) {
  const [radius, setRadius] = useState(5);

  const handleRadiusChange = (value) => {
    const clampedValue = Math.min(10, Math.max(1, value));
    setRadius(clampedValue);
    onRadiusChange(clampedValue);
  };

  return (
    <div className="radius-filter">
      <label>Search Radius: {radius} km</label>
      <input
        type="range"
        min="1"
        max="10"
        value={radius}
        onChange={(e) => handleRadiusChange(Number(e.target.value))}
      />
      <small>Maximum: 10km</small>
    </div>
  );
}
```

### Important Notes

1. **Radius Limits**:
   - Default: 5km
   - Maximum: 10km (enforced by backend)
   - Frontend should validate and clamp values

2. **Fallback Behavior**:
   - If user has no profile location and doesn't provide lat/lng, location filtering is skipped
   - Groups without coordinates are excluded from location-based results

3. **Distance Field**:
   - `distance_km` is only present when using `nearby=true`
   - Value is rounded to 2 decimal places
   - Results are automatically sorted by distance (ascending)

4. **Geocoding**:
   - Groups are geocoded when created/updated (if location provided)
   - Uses Nominatim (OpenStreetMap) geocoding service
   - Respects rate limits (1 request/second)
   - Results cached for 30 days

5. **Performance**:
   - PostGIS provides efficient spatial queries
   - Coordinates stored as geography type for accurate distance calculations
   - Indexes on coordinate fields for fast lookups

### Error Handling

```javascript
async function fetchNearbyGroups(lat, lng, radius = 5) {
  try {
    // Validate radius
    if (radius > 10) {
      console.warn('Radius exceeds maximum (10km), using maximum');
      radius = 10;
    }

    const params = new URLSearchParams({
      nearby: 'true',
      radius: radius.toString()
    });

    // Add coordinates if provided
    if (lat && lng) {
      params.append('lat', lat.toString());
      params.append('lng', lng.toString());
    }

    const response = await fetch(`/api/v1/groups/?${params}`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const groups = await response.json();

    // Filter out groups without coordinates if needed
    return groups.filter(g => g.latitude && g.longitude);

  } catch (error) {
    console.error('Failed to fetch nearby groups:', error);

    // Fallback to regular group list without location filtering
    const response = await fetch('/api/v1/groups/', {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });

    return response.json();
  }
}
```

### TypeScript Interfaces

```typescript
// Extended group interface with location fields
interface Group {
  id: string;
  name: string;
  description: string;
  location: string;
  location_type: 'in_person' | 'online' | 'hybrid';

  // Location fields (NEW)
  latitude: string | null;
  longitude: string | null;
  geocoded_address: string;
  distance_km: number | null; // Only present when using nearby filter

  // ... other fields
  member_limit: number;
  current_member_count: number;
  is_open: boolean;
  is_active: boolean;
  // ...
}

// Query parameters for location filtering
interface GroupQueryParams {
  nearby?: boolean;
  radius?: number; // 1-10 km
  lat?: number;
  lng?: number;
  is_open?: boolean;
  has_space?: boolean;
  my_groups?: boolean;
}

// Helper function types
type GetNearbyGroupsParams = {
  latitude?: number;
  longitude?: number;
  radius?: number;
  filters?: {
    is_open?: boolean;
    has_space?: boolean;
  };
};
```

---
