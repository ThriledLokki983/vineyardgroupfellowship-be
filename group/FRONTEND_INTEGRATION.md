# Frontend Integration Guide - Group App API

This guide documents all Group API endpoints, request payloads, and response structures for frontend integration.

## Table of Contents
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Endpoints Overview](#endpoints-overview)
- [Endpoint Details](#endpoint-details)
- [Data Models](#data-models)
- [Error Responses](#error-responses)

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
| GET | `/{id}/members/` | Get group members | ✅ | Anyone who can view the group |
| POST | `/{id}/join/` | Join group | ✅ | Any authenticated user |
| POST | `/{id}/leave/` | Leave group | ✅ | Current member (not leader) |
| POST | `/{id}/upload_photo/` | Upload group photo | ✅ | Leader or co-leader |

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
| `my_groups` | boolean | No | Show only groups where user is a member, co-leader, or leader | `?my_groups=true` |

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
    "created_at": "2024-10-15T14:30:00Z"
  }
]
```

**Empty Response:** `200 OK`
```json
[]
```

---

### 2. Create Group

Create a new fellowship group. Requires leadership permission.

**Endpoint:** `POST /api/v1/groups/`

**Prerequisites:**
- User must have `leadership_info.can_lead_group: true` in their profile
- Check via: `GET /api/v1/profiles/me/`

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

Request to join a group. Automatically approved for open groups, pending for closed groups.

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

**Response (Open Group):** `200 OK`

```json
{
  "message": "Successfully joined group!",
  "membership": {
    "id": "new-membership-uuid",
    "user_id": "current-user-uuid",
    "email": "you@example.com",
    "display_name": "Your Name",
    "role": "member",
    "status": "active",
    "joined_at": "2024-11-01T15:30:00Z"
  }
}
```

**Response (Closed Group):** `200 OK`

```json
{
  "message": "Membership request submitted. Awaiting leader approval.",
  "membership": {
    "id": "new-membership-uuid",
    "user_id": "current-user-uuid",
    "email": "you@example.com",
    "display_name": "Your Name",
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
  user_membership: UserMembership | null
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
  display_name: string
  role: "leader" | "co_leader" | "member"
  status: "pending" | "active" | "inactive" | "removed"
  joined_at: string (ISO 8601 datetime)
}
```

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

## Quick Reference

```
BASE: /api/v1/groups/

LIST:       GET    /                    → Group[]
CREATE:     POST   /                    → Group
DETAIL:     GET    /{id}/               → Group
UPDATE:     PATCH  /{id}/               → Group
DELETE:     DELETE /{id}/               → 204
MEMBERS:    GET    /{id}/members/       → GroupMember[]
JOIN:       POST   /{id}/join/          → {message, membership}
LEAVE:      POST   /{id}/leave/         → {message}
PHOTO:      POST   /{id}/upload_photo/  → Group

Auth: Bearer token required for all endpoints
```