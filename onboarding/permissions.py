"""
Onboarding permissions for Vineyard Group Fellowship.

This module contains custom permissions for onboarding-related views.
"""

from rest_framework.permissions import BasePermission
from django.utils.translation import gettext_lazy as _


class IsGroupLeader(BasePermission):
    """
    Permission that allows access only to users with leadership permissions.
    """

    message = _('Only group leaders can access this resource.')

    def has_permission(self, request, view):
        """Check if user is authenticated and has leadership permissions."""
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            profile = request.user.basic_profile
            return profile.leadership_info.get('can_lead_group', False)
        except:
            return False


class OnboardingInProgress(BasePermission):
    """
    Permission that allows access only to users who haven't completed onboarding.
    """

    message = _('This resource is only available during onboarding.')

    def has_permission(self, request, view):
        """Check if user is in onboarding process."""
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            progress = request.user.onboarding_progress
            return progress.completion_percentage < 100
        except:
            return True  # Allow access if progress doesn't exist yet


class OnboardingCompleted(BasePermission):
    """
    Permission that allows access only to users who have completed onboarding.
    """

    message = _('Please complete onboarding to access this resource.')

    def has_permission(self, request, view):
        """Check if user has completed onboarding."""
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            progress = request.user.onboarding_progress
            return progress.completion_percentage >= 100
        except:
            return False
