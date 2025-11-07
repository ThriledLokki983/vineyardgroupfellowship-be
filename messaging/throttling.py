"""
Throttling classes for messaging app.

Implements rate limiting to prevent spam and abuse.
"""

from rest_framework.throttling import UserRateThrottle


class DiscussionCreateThrottle(UserRateThrottle):
    """
    Throttle for creating discussions.

    Limit: 10 discussions per hour per user
    Prevents discussion spam
    """
    scope = 'discussion_create'
    rate = '10/hour'


class CommentCreateThrottle(UserRateThrottle):
    """
    Throttle for creating comments.

    Limit: 50 comments per hour per user
    Prevents comment spam while allowing active discussion
    """
    scope = 'comment_create'
    rate = '50/hour'


class ReactionCreateThrottle(UserRateThrottle):
    """
    Throttle for creating reactions.

    Limit: 100 reactions per hour per user
    Allows generous reaction usage
    """
    scope = 'reaction_create'
    rate = '100/hour'


class BurstProtectionThrottle(UserRateThrottle):
    """
    Short burst protection.

    Limit: 20 requests per minute per user
    Prevents rapid-fire spam attacks
    """
    scope = 'burst'
    rate = '20/min'
