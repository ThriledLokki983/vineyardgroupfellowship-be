# Adding Group Information to profiles/me Endpoint

## Introduction

⚠️ **CRITICAL BUSINESS RULE**: Users can only be in **ONE active group** at a time.

This document analyzes different approaches to include group information in the `/api/v1/profiles/me/` endpoint response. Based on the business rules:

1. ✅ Users can only be in ONE active group at a time
2. ✅ A user can be a **leader** (created the group), **co-leader** (assigned by leader), or **member** (joined the group)
3. ✅ The profile should show different information based on their role
4. ✅ The existing `leadership_info` JSONField is a natural place to add group data

### User-Group Relationship Model

```
User → ONE Active Group (or none)
  ↓
  Role in that group:
    - Leader (created the group) → created_by_me: true
    - Co-leader (assigned by leader) → created_by_me: false
    - Member (joined the group) → created_by_me: false
```

---

## Current Endpoint Structure

```json
GET /api/v1/profiles/me/

{
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "JohnD",
  "bio": "...",
  "location": "London",
  "post_code": "SW1A 1AA",
  "timezone": "Europe/London",
  "profile_visibility": "community",
  "leadership_info": {
    "can_lead_group": true
  },
  "display_name_or_email": "JohnD",
  "email": "john@example.com",
  "date_joined": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-10-28T14:20:00Z",
  "onboarding": { ... },
  "photo_url": "https://...",
  "photo_thumbnail_url": "https://...",
  "photo_visibility": "community",
  "can_upload_photo": true
}
```

---

## Option 1: Nested in `leadership_info` (RECOMMENDED) ✅

Extend the existing `leadership_info` JSONField with group data. This is the most natural approach since:
- Leadership info already exists for permissions (`can_lead_group`)
- Being a group leader/co-leader/member is leadership-related
- No new top-level fields needed
- Supports the `created_by_me` flag you requested

### Response Example - Leader

```json
{
  "first_name": "John",
  "email": "john@example.com",

  "leadership_info": {
    "can_lead_group": true,
    "group": {
      "id": 123,
      "name": "West London Fellowship",
      "description": "A community group...",
      "location": "West London",
      "post_code": "W1",
      "meeting_time": "Sundays at 10am",
      "is_open": true,
      "current_size": 15,
      "max_size": 25,
      "has_space": true,
      "photo_url": "https://...",
      "my_role": "leader",
      "created_by_me": true,
      "joined_at": "2024-01-20T10:00:00Z",
      "membership_status": "active"
    }
  }
}
```

### Response Example - Member

```json
{
  "first_name": "Jane",
  "email": "jane@example.com",

  "leadership_info": {
    "can_lead_group": false,
    "group": {
      "id": 123,
      "name": "West London Fellowship",
      "description": "A community group...",
      "location": "West London",
      "post_code": "W1",
      "meeting_time": "Sundays at 10am",
      "is_open": true,
      "current_size": 15,
      "max_size": 25,
      "has_space": true,
      "photo_url": "https://...",
      "my_role": "member",
      "created_by_me": false,
      "joined_at": "2024-02-15T14:30:00Z",
      "membership_status": "active"
    }
  }
}
```

### Response Example - No Group

```json
{
  "first_name": "Bob",
  "email": "bob@example.com",

  "leadership_info": {
    "can_lead_group": true,
    "group": null
  }
}
```

### Implementation

```python
# profiles/serializers.py

from drf_spectacular.utils import extend_schema_field

class UserProfileBasicSerializer(serializers.ModelSerializer):
    # ... existing fields ...

    # Override leadership_info to make it computed
    leadership_info = serializers.SerializerMethodField()

    class Meta:
        model = UserProfileBasic
        fields = [
            # ... existing fields ...
            'leadership_info',  # Now computed, not a model field
        ]

    @extend_schema_field({
        'type': 'object',
        'properties': {
            'can_lead_group': {'type': 'boolean'},
            'group': {
                'type': 'object',
                'nullable': True,
                'properties': {
                    'id': {'type': 'integer'},
                    'name': {'type': 'string'},
                    'description': {'type': 'string'},
                    'location': {'type': 'string'},
                    'post_code': {'type': 'string'},
                    'meeting_time': {'type': 'string'},
                    'is_open': {'type': 'boolean'},
                    'current_size': {'type': 'integer'},
                    'max_size': {'type': 'integer'},
                    'has_space': {'type': 'boolean'},
                    'photo_url': {'type': 'string', 'nullable': True},
                    'my_role': {
                        'type': 'string',
                        'enum': ['leader', 'co_leader', 'member']
                    },
                    'created_by_me': {'type': 'boolean'},
                    'joined_at': {'type': 'string', 'format': 'date-time'},
                    'membership_status': {'type': 'string'},
                }
            }
        }
    })
    def get_leadership_info(self, obj):
        """
        Enhanced leadership_info with current group data.

        Returns leadership permissions + current group info (if any).
        """
        # Start with existing leadership permissions from the model
        base_info = dict(obj.leadership_info) if obj.leadership_info else {}

        # Ensure can_lead_group is present
        if 'can_lead_group' not in base_info:
            base_info['can_lead_group'] = False

        # Add current group info
        user = obj.user
        from group.models import Group, GroupMembership

        # Check if user is a group leader
        leader_group = Group.objects.filter(leader=user, is_active=True).first()
        if leader_group:
            base_info['group'] = {
                'id': leader_group.id,
                'name': leader_group.name,
                'description': leader_group.description,
                'location': leader_group.location,
                'post_code': leader_group.post_code,
                'meeting_time': leader_group.meeting_time,
                'is_open': leader_group.is_open,
                'current_size': leader_group.current_size,
                'max_size': leader_group.max_size,
                'has_space': leader_group.has_space,
                'photo_url': leader_group.photo.url if leader_group.photo else None,
                'my_role': 'leader',
                'created_by_me': True,  # Leader always created the group
                'joined_at': leader_group.created_at.isoformat(),
                'membership_status': 'active'
            }
            return base_info

        # Check if user is a co-leader
        co_leader_group = Group.objects.filter(
            co_leaders=user,
            is_active=True
        ).first()
        if co_leader_group:
            # Get the membership record for joined_at
            membership = GroupMembership.objects.filter(
                user=user,
                group=co_leader_group,
                status='active'
            ).first()

            base_info['group'] = {
                'id': co_leader_group.id,
                'name': co_leader_group.name,
                'description': co_leader_group.description,
                'location': co_leader_group.location,
                'post_code': co_leader_group.post_code,
                'meeting_time': co_leader_group.meeting_time,
                'is_open': co_leader_group.is_open,
                'current_size': co_leader_group.current_size,
                'max_size': co_leader_group.max_size,
                'has_space': co_leader_group.has_space,
                'photo_url': co_leader_group.photo.url if co_leader_group.photo else None,
                'my_role': 'co_leader',
                'created_by_me': False,  # Co-leader did not create
                'joined_at': (
                    membership.created_at.isoformat()
                    if membership
                    else co_leader_group.created_at.isoformat()
                ),
                'membership_status': 'active'
            }
            return base_info

        # Check if user is a regular member
        membership = GroupMembership.objects.filter(
            user=user,
            status='active'
        ).select_related('group').first()

        if membership:
            group = membership.group
            base_info['group'] = {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'location': group.location,
                'post_code': group.post_code,
                'meeting_time': group.meeting_time,
                'is_open': group.is_open,
                'current_size': group.current_size,
                'max_size': group.max_size,
                'has_space': group.has_space,
                'photo_url': group.photo.url if group.photo else None,
                'my_role': 'member',
                'created_by_me': False,  # Member did not create
                'joined_at': membership.created_at.isoformat(),
                'membership_status': membership.status
            }
            return base_info

        # User has no active group
        base_info['group'] = None
        return base_info
```

### Frontend Usage (React/TypeScript)

```typescript
// types/profile.ts
export type GroupRole = 'leader' | 'co_leader' | 'member';

export interface CurrentGroup {
  id: number;
  name: string;
  description: string;
  location: string;
  post_code: string;
  meeting_time: string;
  is_open: boolean;
  current_size: number;
  max_size: number;
  has_space: boolean;
  photo_url: string | null;
  my_role: GroupRole;
  created_by_me: boolean;
  joined_at: string;
  membership_status: string;
}

export interface LeadershipInfo {
  can_lead_group: boolean;
  group: CurrentGroup | null;
}

export interface UserProfile {
  first_name: string;
  last_name: string;
  email: string;
  leadership_info: LeadershipInfo;
  // ... other fields ...
}

// components/ProfilePage.tsx
function ProfilePage() {
  const { data: profile } = useProfile();
  const group = profile.leadership_info.group;

  if (!group) {
    return <JoinGroupPrompt canLead={profile.leadership_info.can_lead_group} />;
  }

  return (
    <div>
      <h2>Your Group: {group.name}</h2>
      <p>Role: {group.my_role}</p>
      <p>Members: {group.current_size} / {group.max_size}</p>

      {group.created_by_me && (
        <div className="badge">You created this group</div>
      )}

      {(group.my_role === 'leader' || group.my_role === 'co_leader') && (
        <LeaderControls groupId={group.id} />
      )}

      {group.my_role === 'member' && (
        <MemberView groupId={group.id} />
      )}
    </div>
  );
}
```

### Pros
- ✅ **Leverages existing field**: No new top-level fields
- ✅ **Semantic grouping**: Leadership permissions + group membership together
- ✅ **Includes `created_by_me`**: Easy to check if user created the group
- ✅ **Complete information**: All group details in one place
- ✅ **Role awareness**: Frontend knows user's role immediately
- ✅ **Clean structure**: Nested under relevant parent

### Cons
- ❌ **Nested access**: `profile.leadership_info.group` instead of `profile.current_group`
- ❌ **Breaking change**: Makes `leadership_info` computed instead of raw model field
- ❌ **Larger payload**: Includes full group details (~300 bytes)

---

## Option 2: Top-level `current_group` Field

Add a top-level `current_group` field for more prominent, direct access.

### Response Example

```json
{
  "first_name": "John",
  "email": "john@example.com",
  "leadership_info": {
    "can_lead_group": true
  },

  "current_group": {
    "id": 123,
    "name": "West London Fellowship",
    "description": "A community group...",
    "location": "West London",
    "my_role": "leader",
    "created_by_me": true,
    "joined_at": "2024-01-20T10:00:00Z"
    // ... full group details ...
  }
}
```

### Implementation

```python
class UserProfileBasicSerializer(serializers.ModelSerializer):
    # ... existing fields ...
    current_group = serializers.SerializerMethodField()

    def get_current_group(self, obj):
        # Same logic as Option 1, but as a separate field
        # ... (implementation identical to Option 1's group logic)
```

### Pros
- ✅ **Direct access**: `profile.current_group` is more intuitive
- ✅ **Separation of concerns**: Leadership permissions separate from group data
- ✅ **Complete information**: All group details included

### Cons
- ❌ **New top-level field**: Adds clutter to profile root
- ❌ **Doesn't use existing `leadership_info`**: Misses opportunity to group related data
- ❌ **No clear semantic connection**: Why is group at profile root?

---

## Option 3: Minimal - Just ID and Role

Add minimal group info, requiring frontend to fetch full details.

### Response Example

```json
{
  "first_name": "John",
  "email": "john@example.com",
  "leadership_info": {
    "can_lead_group": true,
    "current_group_id": 123,
    "current_group_role": "leader",
    "created_group": true
  }
}
```

### Pros
- ✅ **Tiny payload**: Only ~30 bytes
- ✅ **Fast**: Simple queries

### Cons
- ❌ **Incomplete**: Frontend must fetch group details separately
- ❌ **Extra request**: Always requires second API call
- ❌ **Worse UX**: Two round-trips to display group info

---

## Option 4: Boolean Flags Only

Add simple flags without any group details.

### Response Example

```json
{
  "first_name": "John",
  "email": "john@example.com",
  "leadership_info": {
    "can_lead_group": true,
    "has_active_group": true,
    "is_group_leader": true
  }
}
```

### Pros
- ✅ **Minimal**: Tiny payload

### Cons
- ❌ **Very incomplete**: No group info at all
- ❌ **Always needs extra request**: Frontend must always fetch group
- ❌ **Poor UX**: Not user-friendly

---

## Comparison Matrix

| Feature | Option 1: Nested in `leadership_info` | Option 2: Top-level | Option 3: Minimal | Option 4: Flags |
|---------|---------------------------------------|---------------------|-------------------|-----------------|
| **Uses existing `leadership_info`** | ✅ Yes | ❌ No | ⚠️ Yes | ⚠️ Yes |
| **Includes `created_by_me`** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Complete group data** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Payload size** | Medium (300 bytes) | Medium (300 bytes) | Tiny (30 bytes) | Tiny (20 bytes) |
| **Query count** | 1 | 1 | 1 + 1 extra | 1-3 |
| **Frontend complexity** | ✅ Simple | ✅ Simple | ❌ Complex | ❌ Complex |
| **Semantic grouping** | ✅ Excellent | ⚠️ Moderate | ⚠️ Moderate | ⚠️ Moderate |
| **Type safety** | ✅ Excellent | ✅ Excellent | ✅ Good | ✅ Good |
| **Breaking change** | ⚠️ Yes* | ❌ No | ⚠️ Yes* | ⚠️ Yes* |
| **Recommended?** | ✅ **BEST** | ✅ **GOOD** | ❌ Incomplete | ❌ Too minimal |

\* Breaking change: Makes `leadership_info` a computed field instead of raw model field

---

## Recommendation

### ✅ **Option 1: Nested in `leadership_info`** - RECOMMENDED

This is the best approach because:

1. ✅ **Uses your existing field**: `leadership_info` already exists
2. ✅ **Semantic grouping**: Leadership permissions + group membership belong together
3. ✅ **Includes `created_by_me`**: Exactly what you requested
4. ✅ **Complete data**: Frontend gets everything in one request
5. ✅ **Clean structure**: No new top-level fields
6. ✅ **Flexible**: Easy to add more leadership-related data later

The leader will see:
```json
"leadership_info": {
  "can_lead_group": true,
  "group": {
    "my_role": "leader",
    "created_by_me": true,
    // ... full group details ...
  }
}
```

The member will see:
```json
"leadership_info": {
  "can_lead_group": false,
  "group": {
    "my_role": "member",
    "created_by_me": false,
    // ... full group details ...
  }
}
```

---

## Implementation Checklist

- [ ] Update `UserProfileBasicSerializer` to override `leadership_info` as SerializerMethodField
- [ ] Implement `get_leadership_info()` method with group logic
- [ ] Add OpenAPI schema documentation with `@extend_schema_field`
- [ ] Test with users in different roles:
  - [ ] Leader (created group)
  - [ ] Co-leader (assigned)
  - [ ] Member (joined)
  - [ ] No group
- [ ] Update FRONTEND_INTEGRATION.md with new response structure
- [ ] Update frontend TypeScript types
- [ ] Add unit tests for the serializer method
- [ ] Consider database constraint to enforce one-group-per-user (optional)

---

## Database Constraint (Optional but Recommended)

To enforce the one-group-per-user rule at the database level:

```python
# group/models.py

class GroupMembership(models.Model):
    # ... existing fields ...

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(status='active'),
                name='one_active_group_per_user'
            )
        ]
```

This prevents a user from having multiple active memberships at the database level.

---

## Validation in Views (Recommended)

Add validation when users try to join or create groups:

```python
# group/views.py

class GroupViewSet(viewsets.ModelViewSet):

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        # Check if user already has an active group
        existing_membership = GroupMembership.objects.filter(
            user=request.user,
            status='active'
        ).exists()

        if existing_membership:
            return Response(
                {'error': 'You already belong to an active group. Please leave your current group first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Also check if user is a leader or co-leader
        from group.models import Group
        if Group.objects.filter(leader=request.user, is_active=True).exists():
            return Response(
                {'error': 'You are currently leading a group. Please transfer leadership or delete the group first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Group.objects.filter(co_leaders=request.user, is_active=True).exists():
            return Response(
                {'error': 'You are currently a co-leader of a group. Please leave that role first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Proceed with join logic...
```

---

## Next Steps

1. ✅ **Implement Option 1**: Update serializer with nested group in `leadership_info`
2. ✅ **Test thoroughly**: Verify all user roles work correctly
3. ✅ **Update documentation**: FRONTEND_INTEGRATION.md and TypeScript types
4. ⚠️ **Consider constraint**: Add database-level enforcement
5. ⚠️ **Add validation**: Prevent users from joining multiple groups

Would you like me to implement Option 1 now?
