# Group App

The Group app manages fellowship groups within the Vineyard Group Fellowship platform. It provides complete CRUD operations for creating, managing, and joining groups.

## Overview

This Django app is built with Django REST Framework and provides a complete API for fellowship group management. Groups can be public, community-based, or private, with configurable member limits, meeting schedules, and leadership structures.

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
