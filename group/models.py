"""
Group models for Vineyard Group Fellowship.

This module contains models for fellowship groups, group membership,
and group-related functionality.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

User = get_user_model()


class Group(models.Model):
    """
    Fellowship group model.

    Represents a fellowship group where members meet together for
    spiritual growth, support, and community.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Basic Information
    name = models.CharField(
        _('group name'),
        max_length=200,
        help_text=_('Name of the fellowship group')
    )

    description = models.TextField(
        _('description'),
        help_text=_('Description of the group\'s purpose and activities')
    )

    # Location
    location = models.CharField(
        _('location'),
        max_length=300,
        help_text=_(
            'Meeting location or area (e.g., "Downtown Chapel, Main Street")')
    )

    location_type = models.CharField(
        _('location type'),
        max_length=20,
        choices=[
            ('in_person', _('In Person')),
            ('online', _('Online')),
            ('hybrid', _('Hybrid')),
        ],
        default='in_person'
    )

    # Group Settings
    member_limit = models.PositiveIntegerField(
        _('member limit'),
        validators=[MinValueValidator(2), MaxValueValidator(100)],
        default=12,
        help_text=_('Maximum number of members allowed in the group')
    )

    is_open = models.BooleanField(
        _('accepting new members'),
        default=True,
        help_text=_('Whether the group is currently accepting new members')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether the group is currently active')
    )

    # Leadership
    leader = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='led_groups',
        verbose_name=_('group leader'),
        help_text=_('Primary leader of the group')
    )

    co_leaders = models.ManyToManyField(
        User,
        related_name='co_led_groups',
        blank=True,
        verbose_name=_('co-leaders'),
        help_text=_('Additional leaders/facilitators of the group')
    )

    # Group Photo
    photo = models.ImageField(
        _('group photo'),
        upload_to='group_photos/',
        blank=True,
        null=True,
        help_text=_('Group photo or banner image')
    )

    # Meeting Schedule
    meeting_day = models.CharField(
        _('meeting day'),
        max_length=20,
        choices=[
            ('monday', _('Monday')),
            ('tuesday', _('Tuesday')),
            ('wednesday', _('Wednesday')),
            ('thursday', _('Thursday')),
            ('friday', _('Friday')),
            ('saturday', _('Saturday')),
            ('sunday', _('Sunday')),
        ],
        blank=True,
        null=True,
        help_text=_('Primary day of weekly meetings')
    )

    meeting_time = models.TimeField(
        _('meeting time'),
        blank=True,
        null=True,
        help_text=_('Time when group typically meets')
    )

    meeting_frequency = models.CharField(
        _('meeting frequency'),
        max_length=20,
        choices=[
            ('weekly', _('Weekly')),
            ('biweekly', _('Bi-weekly')),
            ('monthly', _('Monthly')),
        ],
        default='weekly'
    )

    # Categories/Tags
    focus_areas = models.JSONField(
        _('focus areas'),
        default=list,
        blank=True,
        help_text=_('Areas of focus (e.g., prayer, bible study, youth, etc.)')
    )

    # Privacy
    visibility = models.CharField(
        _('visibility'),
        max_length=20,
        choices=[
            ('public', _('Public - Anyone can see')),
            ('community', _('Community - Authenticated users only')),
            ('private', _('Private - Invite only')),
        ],
        default='public'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Group')
        verbose_name_plural = _('Groups')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_open']),
            models.Index(fields=['leader']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name

    @property
    def current_member_count(self):
        """Get current number of active members."""
        return self.memberships.filter(status='active').count()

    @property
    def is_full(self):
        """Check if group has reached member limit."""
        return self.current_member_count >= self.member_limit

    @property
    def available_spots(self):
        """Get number of available spots."""
        return max(0, self.member_limit - self.current_member_count)

    @property
    def can_accept_members(self):
        """Check if group can accept new members."""
        return self.is_active and self.is_open and not self.is_full


class GroupMembership(models.Model):
    """
    Group membership model.

    Tracks user membership in fellowship groups with roles and status.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name=_('group')
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='group_memberships',
        verbose_name=_('member')
    )

    role = models.CharField(
        _('role'),
        max_length=20,
        choices=[
            ('leader', _('Leader')),
            ('co_leader', _('Co-Leader')),
            ('member', _('Member')),
        ],
        default='member'
    )

    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('pending', _('Pending Approval')),
            ('active', _('Active')),
            ('inactive', _('Inactive')),
            ('removed', _('Removed')),
        ],
        default='pending'
    )

    joined_at = models.DateTimeField(
        _('joined at'),
        default=timezone.now
    )

    left_at = models.DateTimeField(
        _('left at'),
        blank=True,
        null=True
    )

    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Internal notes about this membership')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Group Membership')
        verbose_name_plural = _('Group Memberships')
        unique_together = ['group', 'user']
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.email} in {self.group.name}"
