"""
Utility functions for messaging app.
"""

from django.contrib.auth import get_user_model
from group.models import GroupMembership
from .models import Conversation

User = get_user_model()


def check_shared_group_membership(user1, user2):
    """
    Check if two users share at least one active group membership.

    Args:
        user1: First user
        user2: Second user

    Returns:
        tuple: (bool, list) - (has_shared_group, list_of_shared_groups)
    """
    # Get all active group IDs for user1
    user1_groups = set(
        GroupMembership.objects.filter(
            user=user1,
            status='active'
        ).values_list('group_id', flat=True)
    )

    # Get all active group IDs for user2
    user2_groups = set(
        GroupMembership.objects.filter(
            user=user2,
            status='active'
        ).values_list('group_id', flat=True)
    )

    # Find intersection
    shared_groups = user1_groups & user2_groups

    return len(shared_groups) > 0, list(shared_groups)


def get_or_create_direct_conversation(user1, user2, group=None):
    """
    Get existing direct message conversation between two users or create a new one.

    Ensures only one conversation exists between any two users.

    Args:
        user1: First user (typically the requester)
        user2: Second user (typically the recipient)
        group: Optional group context for the conversation

    Returns:
        tuple: (Conversation, bool) - (conversation_object, created)
    """
    # Try to find existing direct message conversation between these users
    # Need to check both orderings since participants is a ManyToMany field
    existing = Conversation.objects.filter(
        context_type='direct_message',
        participants=user1
    ).filter(
        participants=user2
    ).first()

    if existing:
        return existing, False

    # Create new conversation
    conversation = Conversation.objects.create(
        context_type='direct_message',
        group=group
    )
    conversation.participants.add(user1, user2)

    return conversation, True


def validate_can_message_user(sender, recipient):
    """
    Validate if sender can message recipient.

    Business rules:
    - Users must share at least one active group membership
    - Cannot message yourself
    - Both users must have active membership status

    Args:
        sender: User initiating the conversation
        recipient: User receiving the message

    Returns:
        tuple: (bool, str) - (is_valid, error_message)

    Raises:
        None - returns validation result as tuple
    """
    # Check if trying to message self
    if sender == recipient:
        return False, "cannot_message_self"

    # Check if they share at least one active group
    has_shared_group, _ = check_shared_group_membership(sender, recipient)

    if not has_shared_group:
        return False, "no_shared_group"

    # Validation passed
    return True, None
