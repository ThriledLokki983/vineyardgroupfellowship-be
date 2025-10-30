"""
Custom permissions for Vineyard Group Fellowship platform.

This module contains DRF permission classes for:
- Object-level ownership checks
- Privacy-based access controls
- Recovery-specific permissions
"""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only to the owner of the object
        return obj.user == request.user


class IsProfileOwner(permissions.BasePermission):
    """
    Permission to check if user owns the profile.
    """

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsSessionOwner(permissions.BasePermission):
    """
    Permission to check if user owns the session.
    """

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class CanManageOwnData(permissions.BasePermission):
    """
    Permission for GDPR data management operations.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Users can only manage their own data
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsRecoverySeeker(permissions.BasePermission):
    """
    Permission to check if user has user_purpose = 'seeking_recovery'.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            profile = request.user.basic_profile
            return profile.user_purpose == 'seeking_recovery'
        except:
            return False


class IsRecoverySupporter(permissions.BasePermission):
    """
    Permission to check if user has user_purpose = 'providing_support'.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            profile = request.user.basic_profile
            return profile.user_purpose == 'providing_support'
        except:
            return False


class IsRecoverySeekerOrSupporter(permissions.BasePermission):
    """
    Permission to check if user has any valid user_purpose.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            profile = request.user.basic_profile
            return profile.user_purpose in ['seeking_recovery', 'providing_support']
        except:
            return False


class CanProvideSupport(permissions.BasePermission):
    """
    Permission to check if user can provide support (has supporter qualifications).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            profile = request.user.basic_profile
            return profile.can_provide_support()
        except:
            return False


class IsApprovedSupporter(permissions.BasePermission):
    """
    Permission to check if user is an approved supporter.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            profile = request.user.basic_profile
            if profile.user_purpose != 'providing_support':
                return False

            qualifications = profile.supporter_qualifications
            return qualifications.supporter_status == 'approved'
        except:
            return False


class CanLeadGroups(permissions.BasePermission):
    """
    Permission to check if user can lead support groups.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            profile = request.user.basic_profile
            return profile.can_lead_groups
        except:
            return False


class IsMemberOrPublicReadOnly(permissions.BasePermission):
    """
    Permission to allow group members full access, and public read-only access.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only to group members
        return obj.members.filter(id=request.user.id).exists()
