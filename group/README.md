# Group App

The Group app manages fellowship groups within the Vineyard Group Fellowship platform. It provides complete CRUD operations for creating, managing, and joining groups.

## Overview

This Django app is built with Django REST Framework and provides a complete API for fellowship group management. Groups can be public, community-based, or private, with configurable member limits, meeting schedules, and leadership structures.

## Table of Contents
- [Features](#features)
- [Models](#models)
- [API Endpoints](#api-endpoints)
- [Permissions](#permissions)
- [Integration Points](#integration-points)
- [Admin Interface](#admin-interface)
- [Example Workflows](#example-workflows)

## Features

### Core Functionality
- ✅ **Group CRUD**: Create, read, update, and delete fellowship groups
- ✅ **Membership Management**: Join, leave, and manage group memberships
- ✅ **Leadership Roles**: Support for group leaders and co-leaders
- ✅ **Photo Uploads**: Group photo management with media handling
- ✅ **Visibility Controls**: Public, community, and private groups
- ✅ **Member Limits**: Configurable group size (2-100) with automatic capacity tracking
- ✅ **Meeting Schedules**: Track meeting days, times, and frequencies
- ✅ **Focus Areas**: Flexible JSON field for group interests and activities
- ✅ **Smart Filtering**: Filter by location, availability, and status

### Member Roles
- **Leader**: Group creator with full management permissions (create, update, delete, manage members)
- **Co-Leader**: Additional leaders with update permissions (update, upload photo)
- **Member**: Regular group participants (view, leave)

### Membership Status
- **Pending**: Awaiting approval (for closed groups)
- **Active**: Current member with full participation rights
- **Inactive**: Left the group voluntarily
- **Removed**: Removed by group leaders

## Models

### Group

Main model for fellowship groups.

**Fields:**

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Unique identifier | Primary key, auto-generated |
| `name` | CharField(200) | Group name | Required |
| `description` | TextField | Group description | Optional |
| `location` | CharField(255) | Physical/virtual location | Optional |
| `location_type` | CharField(20) | Type of location | Choices: in_person, virtual, hybrid |
| `member_limit` | PositiveIntegerField | Maximum members | 2-100, default: 12 |
| `is_open` | BooleanField | Accepts new members | Default: True |
| `is_active` | BooleanField | Soft delete flag | Default: True |
| `leader` | ForeignKey(User) | Group leader | Required, on_delete=PROTECT |
| `co_leaders` | ManyToManyField(User) | Additional leaders | Optional |
| `photo` | ImageField | Group photo | Optional, uploads to group_photos/ |
| `meeting_day` | CharField(10) | Day of week | Choices: monday-sunday |
| `meeting_time` | TimeField | Meeting time | Optional |
| `meeting_frequency` | CharField(20) | How often | Choices: weekly, biweekly, monthly |
| `focus_areas` | JSONField | Interests/activities | Default: empty list |
| `visibility` | CharField(20) | Privacy level | Choices: public, community, private |
| `created_at` | DateTimeField | Creation timestamp | Auto-generated |
| `updated_at` | DateTimeField | Last update timestamp | Auto-updated |

**Properties:**

```python
@property
def current_member_count(self) -> int:
    """Returns count of active members"""

@property
def is_full(self) -> bool:
    """Returns True if group is at capacity"""

@property
def available_spots(self) -> int:
    """Returns number of remaining member slots"""

@property
def can_accept_members(self) -> bool:
    """Returns True if group is open and has space"""
```

**Database Indexes:**
- `(is_active, is_open)` - For filtering active/open groups
- `leader` - For leader-based queries
- `created_at` - For sorting by creation date

### GroupMembership

Tracks user membership in groups.

**Fields:**

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Unique identifier | Primary key |
| `group` | ForeignKey(Group) | Associated group | on_delete=CASCADE |
| `user` | ForeignKey(User) | Member user | on_delete=CASCADE |
| `role` | CharField(20) | Member role | Choices: leader, co_leader, member |
| `status` | CharField(20) | Membership status | Choices: pending, active, inactive, removed |
| `joined_at` | DateTimeField | Join timestamp | Auto-generated |
| `left_at` | DateTimeField | Leave timestamp | Optional |
| `notes` | TextField | Additional notes | Optional (e.g., join message) |

**Constraints:**
- `unique_together = ('group', 'user')` - One membership per user per group

**Database Indexes:**
- `(group, status)` - For querying group members by status
- `(user, status)` - For querying user's memberships by status

## API Endpoints

Base URL: `/api/v1/groups/`

All endpoints require authentication (JWT token in Authorization header).

### List Groups

```http
GET /api/v1/groups/
```

Lists all active groups visible to the authenticated user based on visibility settings.

**Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `location` | string | Filter by location (case-insensitive contains) | `?location=downtown` |
| `is_open` | boolean | Filter by open/closed status | `?is_open=true` |
| `has_space` | boolean | Show only groups with available spots | `?has_space=true` |

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
      "id": "user-uuid",
      "email": "leader@example.com",
      "display_name": "John Doe"
    },
    "photo_url": "http://localhost:8001/media/group_photos/2024/11/photo.jpg",
    "meeting_day": "wednesday",
    "meeting_time": "19:00:00",
    "meeting_frequency": "weekly",
    "focus_areas": ["worship", "bible_study", "fellowship"],
    "created_at": "2024-11-01T10:00:00Z"
  }
]
```

### Create Group

```http
POST /api/v1/groups/
```

Create a new fellowship group. User must have `can_lead_group` permission in their profile.

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

**Response:** `201 Created`

Returns the created group with full details. A leader membership is automatically created for the creator.

**Error Responses:**
- `400 Bad Request` - If user doesn't have leadership permissions
- `401 Unauthorized` - If not authenticated

### Get Group Details

```http
GET /api/v1/groups/{id}/
```

Get detailed information about a specific group.

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
  "leader": "user-uuid",
  "leader_info": {
    "id": "user-uuid",
    "email": "leader@example.com",
    "display_name": "John Doe"
  },
  "co_leaders": ["co-leader-uuid"],
  "co_leaders_info": [
    {
      "id": "co-leader-uuid",
      "email": "coleader@example.com",
      "display_name": "Jane Smith"
    }
  ],
  "photo": "/media/group_photos/2024/11/photo.jpg",
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
    "joined_at": "2024-11-01T12:00:00Z"
  },
  "created_at": "2024-11-01T10:00:00Z",
  "updated_at": "2024-11-01T10:00:00Z"
}
```

**Note:** `user_membership` field shows the authenticated user's membership status if they are a member.

### Update Group

```http
PUT /api/v1/groups/{id}/
PATCH /api/v1/groups/{id}/
```

Update group details. Only the group leader and co-leaders can update.

**Request Body:** Same as create, all fields optional for PATCH

**Response:** `200 OK`

Returns updated group details.

**Error Responses:**
- `403 Forbidden` - If user is not leader or co-leader

### Delete Group

```http
DELETE /api/v1/groups/{id}/
```

Soft delete a group (sets `is_active=False`). Only the group leader can delete.

**Response:** `204 No Content`

**Error Responses:**
- `403 Forbidden` - If user is not the group leader

### Get Group Members

```http
GET /api/v1/groups/{id}/members/
```

Get list of all active members in the group.

**Response:** `200 OK`

```json
[
  {
    "id": "membership-uuid",
    "user_id": "user-uuid",
    "email": "member@example.com",
    "display_name": "John Doe",
    "role": "leader",
    "status": "active",
    "joined_at": "2024-11-01T10:00:00Z"
  },
  {
    "id": "membership-uuid-2",
    "user_id": "user-uuid-2",
    "email": "member2@example.com",
    "display_name": "Jane Smith",
    "role": "member",
    "status": "active",
    "joined_at": "2024-11-01T12:00:00Z"
  }
]
```

### Join Group

```http
POST /api/v1/groups/{id}/join/
```

Request to join a group.

**Request Body (optional):**

```json
{
  "message": "I'd love to join your group!"
}
```

**Behavior:**
- **Open groups**: Automatically approved (status=active)
- **Closed groups**: Pending approval (status=pending)

**Response:** `200 OK`

```json
{
  "message": "Successfully joined group!",
  "membership": {
    "id": "membership-uuid",
    "user_id": "user-uuid",
    "email": "user@example.com",
    "display_name": "John Doe",
    "role": "member",
    "status": "active",
    "joined_at": "2024-11-01T15:00:00Z"
  }
}
```

**Error Responses:**
- `400 Bad Request` - If already a member or group is full/closed

### Leave Group

```http
POST /api/v1/groups/{id}/leave/
```

Leave a group you are a member of. Group leaders cannot leave (must transfer leadership first).

**Response:** `200 OK`

```json
{
  "message": "Successfully left group."
}
```

**Error Responses:**
- `400 Bad Request` - If not a member or if you're the leader

### Upload Group Photo

```http
POST /api/v1/groups/{id}/upload_photo/
```

Upload a photo for the group. Only leaders and co-leaders can upload.

**Request:** Multipart form data

```
Content-Type: multipart/form-data

photo: [binary file data]
```

**Response:** `200 OK`

Returns updated group details with new photo URL.

**Error Responses:**
- `403 Forbidden` - If user is not leader or co-leader
- `400 Bad Request` - If no photo file provided

## Permissions

### Leadership Requirements

To create or lead a group, users must have the `can_lead_group` permission in their profile's `leadership_info` JSON field. This is typically granted through leadership onboarding.

**Check in profile:**
```json
{
  "leadership_info": {
    "can_lead_group": true
  }
}
```

### Group Access Permissions

| Action | Permission Required |
|--------|-------------------|
| List groups | Authenticated user |
| View group | Based on visibility settings |
| Create group | Authenticated + `can_lead_group` permission |
| Update group | Group leader or co-leader |
| Delete group | Group leader only |
| Upload photo | Group leader or co-leader |
| Join group | Authenticated user (if group is open/accepting) |
| Leave group | Current member (except leader) |
| View members | Any user who can view the group |

### Visibility Access

| Visibility Level | Who Can View |
|-----------------|-------------|
| **Public** | All authenticated users |
| **Community** | Community members (all authenticated users currently) |
| **Private** | Only group members, co-leaders, and leader |

## Integration Points

### Profiles App

Groups integrate with the profiles app through:

1. **Leadership Permissions**: Checks `basic_profile.leadership_info.can_lead_group`
2. **User Display Names**: Uses `display_name_or_email` for member/leader names
3. **User Location**: Can match group location with user's profile location

**Example check:**
```python
try:
    profile = request.user.basic_profile
    can_lead = profile.leadership_info.get('can_lead_group', False)
except:
    can_lead = False
```

### Onboarding App

Future integration planned for:
- Group selection/creation during onboarding process
- Encouraging users to join or create groups as part of onboarding
- Leadership onboarding to grant `can_lead_group` permission

### Authentication

All group endpoints require authentication via JWT tokens:

```http
Authorization: Bearer <access_token>
```

Use the authentication endpoints to obtain tokens:
- Login: `POST /api/v1/auth/login/`
- Refresh: `POST /api/v1/auth/token/refresh/`

## Admin Interface

The Django admin provides comprehensive group management at `/admin/group/`.

### Group Admin Features

- **List View**:
  - Display: name, leader, location, member count, capacity, status
  - Filters: is_active, is_open, visibility, location_type, meeting frequency
  - Search: name, description, location, leader email

- **Detail View**:
  - Organized fieldsets (Basic Info, Location, Leadership, Membership, etc.)
  - Inline membership management
  - Readonly computed fields (member count, capacity)
  - Autocomplete for leader and co-leaders
  - Horizontal filter for co-leaders

- **Inline Memberships**:
  - View/edit all memberships from group detail page
  - Quick access to member role and status

### GroupMembership Admin Features

- **List View**:
  - Display: user, group, role, status, joined/left dates
  - Filters: role, status, dates
  - Search: user email, group name, notes

- **Optimizations**:
  - Select_related queries for performance
  - Prefetch_related for many-to-many relationships

## Example Workflows

### 1. Creating a Group

**Scenario**: A user wants to create a new fellowship group

**Steps**:
1. User completes leadership onboarding (gets `can_lead_group` permission)
2. Frontend sends POST to `/api/v1/groups/` with group details
3. Backend validates leadership permission
4. Group is created with user as leader
5. Leader membership automatically created with status=active
6. Frontend redirects to group detail page

**API Flow**:
```javascript
// 1. Check if user can lead
const profile = await fetch('/api/v1/profiles/me/');
const canLead = profile.leadership_info?.can_lead_group;

// 2. Create group
const response = await fetch('/api/v1/groups/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: "Young Adults Fellowship",
    description: "Connect and grow together",
    location: "Downtown Campus",
    location_type: "in_person",
    member_limit: 12,
    is_open: true,
    meeting_day: "wednesday",
    meeting_time: "19:00:00",
    meeting_frequency: "weekly",
    focus_areas: ["worship", "bible_study"],
    visibility: "public"
  })
});
```

### 2. Browsing and Joining Groups

**Scenario**: A user wants to find and join a group

**Steps**:
1. User browses groups via GET `/api/v1/groups/?has_space=true`
2. Frontend displays list with filters (location, open status)
3. User selects a group and views details
4. User clicks "Join Group"
5. Frontend sends POST to `/api/v1/groups/{id}/join/`
6. If open: User immediately becomes active member
7. If closed: Request goes to leader for approval (status=pending)

**API Flow**:
```javascript
// 1. Browse groups with filters
const groups = await fetch('/api/v1/groups/?location=downtown&has_space=true');

// 2. View group details
const group = await fetch(`/api/v1/groups/${groupId}/`);

// 3. Join group
const joinResponse = await fetch(`/api/v1/groups/${groupId}/join/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: "I'd love to join!"
  })
});
```

### 3. Managing Group Members

**Scenario**: A group leader wants to view and manage members

**Steps**:
1. Leader views members via GET `/api/v1/groups/{id}/members/`
2. Frontend displays list of active members with roles
3. For pending members: Leader can approve/reject (future feature)
4. For active members: Leader can promote to co-leader or remove (via admin currently)

**API Flow**:
```javascript
// Get all members
const members = await fetch(`/api/v1/groups/${groupId}/members/`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

// Display members grouped by role
const leaders = members.filter(m => m.role === 'leader');
const coLeaders = members.filter(m => m.role === 'co_leader');
const regularMembers = members.filter(m => m.role === 'member');
```

### 4. Updating Group Information

**Scenario**: A co-leader wants to update group meeting time

**Steps**:
1. Frontend sends PATCH to `/api/v1/groups/{id}/`
2. Backend verifies user is leader or co-leader
3. Group is updated
4. Frontend shows success message and updated details

**API Flow**:
```javascript
const response = await fetch(`/api/v1/groups/${groupId}/`, {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    meeting_time: "20:00:00",
    meeting_frequency: "biweekly"
  })
});
```

### 5. Uploading Group Photo

**Scenario**: A leader wants to add a photo to their group

**Steps**:
1. User selects photo file
2. Frontend sends POST to `/api/v1/groups/{id}/upload_photo/`
3. Backend validates user is leader/co-leader
4. Photo is saved to media storage
5. Group photo URL is updated
6. Frontend displays new photo

**API Flow**:
```javascript
const formData = new FormData();
formData.append('photo', photoFile);

const response = await fetch(`/api/v1/groups/${groupId}/upload_photo/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

## Database Schema

```
┌─────────────────────────────────────────┐
│              Group                       │
├─────────────────────────────────────────┤
│ id (UUID, PK)                           │
│ name (VARCHAR 200)                      │
│ description (TEXT)                      │
│ location (VARCHAR 255)                  │
│ location_type (VARCHAR 20)              │
│ member_limit (INT, 2-100)               │
│ is_open (BOOLEAN)                       │
│ is_active (BOOLEAN)                     │
│ leader_id (FK → User)                   │
│ photo (VARCHAR 100)                     │
│ meeting_day (VARCHAR 10)                │
│ meeting_time (TIME)                     │
│ meeting_frequency (VARCHAR 20)          │
│ focus_areas (JSON)                      │
│ visibility (VARCHAR 20)                 │
│ created_at (TIMESTAMP)                  │
│ updated_at (TIMESTAMP)                  │
└─────────────────────────────────────────┘
         │                        │
         │                        │ (Many-to-Many)
         │                        │
         ▼                        ▼
┌──────────────────────┐   ┌─────────────────────────┐
│  GroupMembership     │   │    co_leaders           │
├──────────────────────┤   │  (Through table)        │
│ id (UUID, PK)        │   └─────────────────────────┘
│ group_id (FK)        │
│ user_id (FK)         │
│ role (VARCHAR 20)    │
│ status (VARCHAR 20)  │
│ joined_at (TIMESTAMP)│
│ left_at (TIMESTAMP)  │
│ notes (TEXT)         │
└──────────────────────┘
```

## Future Enhancements

Potential features for future development:

### Phase 1 (Priority)
- [ ] Member invitation system (invite via email/link)
- [ ] Approval/rejection workflow for pending memberships
- [ ] Transfer leadership endpoint
- [ ] Promote/demote member roles via API

### Phase 2 (Medium Priority)
- [ ] Group activity feed
- [ ] Meeting attendance tracking
- [ ] Group messaging/announcements
- [ ] Event scheduling within groups

### Phase 3 (Nice to Have)
- [ ] Integration with calendar systems (Google Calendar, iCal)
- [ ] Group tags/categories beyond focus_areas
- [ ] Advanced search with full-text search
- [ ] Group recommendations based on user interests
- [ ] Analytics (member growth, attendance trends)
- [ ] Automated reminders for meetings
- [ ] Waitlist for full groups

## Testing

Run tests with:
```bash
python manage.py test group
```

Coverage:
```bash
coverage run --source='group' manage.py test group
coverage report
```

## License

This app is part of the Vineyard Group Fellowship project.

## Models

### Group
Main model for fellowship groups.

**Key Fields:**
- `name`: Group name
- `description`: Group description
- `location`: Physical or virtual location
- `location_type`: in_person, virtual, hybrid
- `member_limit`: Max members (2-100, default 12)
- `leader`: Group leader (ForeignKey to User)
- `co_leaders`: Additional leaders (ManyToMany to User)
- `photo`: Group photo
- `meeting_day`, `meeting_time`, `meeting_frequency`: Schedule info
- `focus_areas`: JSON field for interests/activities
- `visibility`: public, community, private
- `is_open`: Whether group accepts new members
- `is_active`: Soft delete flag

**Properties:**
- `current_member_count`: Number of active members
- `is_full`: Whether group is at capacity
- `available_spots`: Remaining member slots
- `can_accept_members`: Whether group can accept new members

### GroupMembership
Tracks user membership in groups.

**Key Fields:**
- `group`: ForeignKey to Group
- `user`: ForeignKey to User
- `role`: leader, co_leader, member
- `status`: pending, active, inactive, removed
- `joined_at`: When user joined
- `left_at`: When user left (if applicable)
- `notes`: Additional notes (e.g., join request message)

**Constraints:**
- Unique together on (group, user)

## API Endpoints

All endpoints are prefixed with `/api/v1/groups/`

### List Groups
```
GET /api/v1/groups/
```
Lists all active groups visible to the user.

**Query Parameters:**
- `location`: Filter by location (case-insensitive contains)
- `is_open`: Filter by open/closed status (true/false)
- `has_space`: Show only groups with available spots (true/false)

**Response:** Array of groups with basic info

### Create Group
```
POST /api/v1/groups/
```
Create a new fellowship group. User must have leadership permissions.

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

**Response:** Created group details with auto-created leader membership

### Get Group Details
```
GET /api/v1/groups/{id}/
```
Get detailed information about a specific group.

**Response:** Full group details including leader info, member count, and user's membership status (if applicable)

### Update Group
```
PUT /api/v1/groups/{id}/
PATCH /api/v1/groups/{id}/
```
Update group details. Only leader and co-leaders can update.

**Request Body:** Same as create, all fields optional for PATCH

### Delete Group
```
DELETE /api/v1/groups/{id}/
```
Soft delete a group (sets is_active=False). Only leader can delete.

### Get Group Members
```
GET /api/v1/groups/{id}/members/
```
Get list of all active members in the group.

**Response:** Array of member objects with user info, role, and join date

### Join Group
```
POST /api/v1/groups/{id}/join/
```
Request to join a group.

**Request Body (optional):**
```json
{
  "message": "I'd love to join your group!"
}
```

**Behavior:**
- Open groups: Automatically approved (status=active)
- Closed groups: Pending approval (status=pending)

**Response:**
```json
{
  "message": "Successfully joined group!",
  "membership": {
    "id": "...",
    "role": "member",
    "status": "active",
    "joined_at": "2024-01-15T19:00:00Z"
  }
}
```

### Leave Group
```
POST /api/v1/groups/{id}/leave/
```
Leave a group you are a member of. Leaders cannot leave (must transfer leadership first).

**Response:**
```json
{
  "message": "Successfully left group."
}
```

### Upload Group Photo
```
POST /api/v1/groups/{id}/upload_photo/
```
Upload a photo for the group. Only leaders and co-leaders can upload.

**Request:** Multipart form data with `photo` field

**Response:** Updated group details with new photo URL

## Permissions

### Leadership Requirements
To create or lead a group, users must have `can_lead_group` permission in their profile's `leadership_info` field. This is typically granted through leadership onboarding.

### Group Management
- **Create**: Users with leadership permissions
- **Update**: Group leader and co-leaders
- **Delete**: Group leader only
- **Upload Photo**: Group leader and co-leaders
- **View**: Based on visibility settings
  - Public: All authenticated users
  - Community: All authenticated users
  - Private: Only members and leaders

## Integration Points

### Profiles App
Groups integrate with the profiles app through:
- Leadership permissions check via `basic_profile.leadership_info`
- User display names from `display_name_or_email`

### Onboarding App
Future integration planned for:
- Group selection/creation during onboarding
- Encouraging users to join or create groups

### Authentication
All group endpoints require authentication via JWT tokens.

## Admin Interface

The Django admin provides comprehensive group management:
- Group list with filters and search
- Inline membership management
- Readonly computed fields (member count, capacity, etc.)
- Autocomplete for users and leaders
- Custom fieldsets for organized editing

## Visibility Levels

### Public
- Visible to all authenticated users
- Anyone can see and join (if open)

### Community
- Visible to community members
- Requires some level of engagement

### Private
- Only visible to members and leaders
- Invite-only or by request

## Example Workflows

### Creating a Group
1. User completes leadership onboarding (gets `can_lead_group` permission)
2. POST to `/api/v1/groups/` with group details
3. Group is created with user as leader
4. Leader membership automatically created with status=active

### Joining a Group
1. User browses groups via GET `/api/v1/groups/?has_space=true`
2. Selects a group and views details
3. POST to `/api/v1/groups/{id}/join/`
4. If open: Immediately becomes active member
5. If closed: Request goes to leader for approval

### Managing Members
1. Leader views members via GET `/api/v1/groups/{id}/members/`
2. Can approve pending requests (future feature)
3. Can promote members to co-leaders via admin or future API
4. Can remove members via admin or future API

## Future Enhancements

Potential features for future development:
- Member invitation system
- Approval/rejection workflow for pending memberships
- Transfer leadership endpoint
- Promote/demote member roles
- Group activity feed
- Meeting attendance tracking
- Group messaging/announcements
- Integration with calendar systems
- Group tags/categories beyond focus_areas
- Advanced search and filtering
- Group recommendations based on user interests
