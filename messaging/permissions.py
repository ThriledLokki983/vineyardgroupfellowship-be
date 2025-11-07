"""
Permission classes for messaging app.

Implements fine-grained access control for messaging features.
"""

from rest_framework import permissions
from group.models import GroupMembership


class IsGroupMember(permissions.BasePermission):
    """
    Permission to check if user is a member of the group.

    - Discussions: User must be group member to view/create
    - Comments: User must be group member to view/create
    - Reactions: User must be group member to create
    """

    message = "You must be a member of this group to perform this action."

    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user is member of the object's group."""
        # Get the group from different object types
        if hasattr(obj, 'group'):
            group = obj.group
        elif hasattr(obj, 'discussion'):
            group = obj.discussion.group
        elif hasattr(obj, 'comment'):
            group = obj.comment.discussion.group
        else:
            return False

        # Check membership
        return GroupMembership.objects.filter(
            group=group,
            user=request.user,
            status='active'
        ).exists()


class IsAuthorOrGroupLeaderOrReadOnly(permissions.BasePermission):
    """
    Permission for editing posts/comments.

    - Read: Any group member can read
    - Create: Any group member can create
    - Update/Delete: Only author or group leader can modify
    """

    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user can modify the object."""
        # Read permissions for any group member
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for author or group leader
        is_author = obj.author == request.user

        # Get the group
        if hasattr(obj, 'group'):
            group = obj.group
        elif hasattr(obj, 'discussion'):
            group = obj.discussion.group
        else:
            return False

        is_group_leader = group.leader == request.user or request.user in group.co_leaders.all()

        return is_author or is_group_leader


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Permission for editing own content only.

    - Read: Any group member can read
    - Create: Any group member can create
    - Update/Delete: Only author can modify
    """

    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user is the author."""
        # Read permissions for any group member
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for author
        return obj.author == request.user or obj.user == request.user


class CanModerateGroup(permissions.BasePermission):
    """
    Permission for group moderation actions.

    Only group leaders can:
    - Pin/unpin discussions
    - Lock/unlock discussions
    - Delete any member's posts (not just their own)
    """

    message = "Only group leaders can perform moderation actions."

    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user is a group leader."""
        # Get the group
        if hasattr(obj, 'group'):
            group = obj.group
        elif hasattr(obj, 'discussion'):
            group = obj.discussion.group
        else:
            return False

        return group.leader == request.user or request.user in group.co_leaders.all()
