"""
Permissions for the privacy app.
GDPR compliance and data privacy access control.
"""

from rest_framework import permissions
from django.utils.translation import gettext_lazy as _


class GDPRDataAccessPermission(permissions.BasePermission):
    """
    Permission for GDPR data access operations.

    Users can only access their own data unless they are staff/admins.
    """

    message = _("You can only access your own personal data.")

    def has_permission(self, request, view):
        """Check if user has permission to access GDPR endpoints."""
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Staff/admins can access all data for compliance purposes
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Regular users can only access their own data
        return True

    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific object."""
        # Staff/admins can access any object
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Users can only access their own objects
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class GDPRDataExportPermission(permissions.BasePermission):
    """
    Permission for GDPR data export operations.

    Article 20 - Right to Data Portability
    """

    message = _("You can only export your own personal data.")

    def has_permission(self, request, view):
        """Check if user can export data."""
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user account is active
        if not request.user.is_active:
            self.message = _("Account must be active to export data.")
            return False

        return True


class GDPRDataErasurePermission(permissions.BasePermission):
    """
    Permission for GDPR data erasure operations.

    Article 17 - Right to Erasure (Right to be Forgotten)
    """

    message = _("You can only delete your own account.")

    def has_permission(self, request, view):
        """Check if user can delete their account."""
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user account is active
        if not request.user.is_active:
            self.message = _("Account must be active to request deletion.")
            return False

        # Prevent staff/admin accounts from self-deletion via API
        if request.user.is_staff or request.user.is_superuser:
            self.message = _("Staff accounts cannot be deleted via API for security reasons.")
            return False

        return True


class GDPRConsentManagementPermission(permissions.BasePermission):
    """
    Permission for GDPR consent management operations.

    Article 7 - Consent
    """

    message = _("You can only manage your own consent preferences.")

    def has_permission(self, request, view):
        """Check if user can manage consent."""
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user account is active
        if not request.user.is_active:
            self.message = _("Account must be active to manage consent.")
            return False

        return True


class GDPRAdminPermission(permissions.BasePermission):
    """
    Permission for GDPR administrative operations.

    Only staff and superusers can perform administrative GDPR operations.
    """

    message = _("Administrative privileges required for this operation.")

    def has_permission(self, request, view):
        """Check if user has admin privileges."""
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_staff or request.user.is_superuser


class GDPRDataRetentionPermission(permissions.BasePermission):
    """
    Permission for GDPR data retention policy operations.

    Users can view retention policies, staff can modify them.
    """

    def has_permission(self, request, view):
        """Check retention policy permissions."""
        if not request.user or not request.user.is_authenticated:
            return False

        # Everyone can view retention policies
        if request.method in permissions.SAFE_METHODS:
            return True

        # Only staff can modify retention policies
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return request.user.is_staff or request.user.is_superuser

        return True


class GDPRDataCleanupPermission(permissions.BasePermission):
    """
    Permission for GDPR data cleanup operations.

    Users can cleanup their own data, staff can perform administrative cleanup.
    """

    def has_permission(self, request, view):
        """Check cleanup permissions."""
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user account is active
        if not request.user.is_active:
            self.message = _("Account must be active to request data cleanup.")
            return False

        return True


class IsDataSubject(permissions.BasePermission):
    """
    Permission to check if user is the data subject.

    Used for ensuring users can only access their own personal data.
    """

    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user owns the object."""
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user


class IsDataController(permissions.BasePermission):
    """
    Permission for data controllers (staff/admins).

    Used for GDPR compliance administration.
    """

    def has_permission(self, request, view):
        """Check if user is a data controller."""
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_staff or request.user.is_superuser


class GDPRRightOfAccessPermission(permissions.BasePermission):
    """
    GDPR Article 15 - Right of Access permission.

    Users can access information about their personal data processing.
    """

    def has_permission(self, request, view):
        """Check right of access permission."""
        return request.user and request.user.is_authenticated


class GDPRRightToRectificationPermission(permissions.BasePermission):
    """
    GDPR Article 16 - Right to Rectification permission.

    Users can correct inaccurate personal data.
    """

    def has_permission(self, request, view):
        """Check right to rectification permission."""
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_active


class GDPRRightToRestrictProcessingPermission(permissions.BasePermission):
    """
    GDPR Article 18 - Right to Restriction of Processing permission.

    Users can restrict processing of their personal data.
    """

    def has_permission(self, request, view):
        """Check right to restrict processing permission."""
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_active