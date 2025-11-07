"""
Group models for Vineyard Group Fellowship.

This module contains models for fellowship groups, group membership,
and group-related functionality.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models as gis_models
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

    # Geographic coordinates for location-based features
    latitude = models.DecimalField(
        _('latitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_('Latitude coordinate for location-based search')
    )

    longitude = models.DecimalField(
        _('longitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_('Longitude coordinate for location-based search')
    )

    # PostGIS point field for efficient geographic queries
    coordinates = gis_models.PointField(
        _('coordinates'),
        null=True,
        blank=True,
        geography=True,
        srid=4326,  # WGS84 coordinate system
        help_text=_(
            'Geographic point for spatial queries (auto-populated from lat/lng)')
    )

    # Geocoding metadata
    geocoded_address = models.CharField(
        _('geocoded address'),
        max_length=500,
        blank=True,
        help_text=_('Full address returned from geocoding service')
    )

    geocoded_at = models.DateTimeField(
        _('geocoded at'),
        null=True,
        blank=True,
        help_text=_('When the address was last geocoded')
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

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='created_groups',
        verbose_name=_('created by'),
        null=True,
        blank=True,
        help_text=_('User who originally created this group')
    )

    last_updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='updated_groups',
        verbose_name=_('last updated by'),
        null=True,
        blank=True,
        help_text=_('User who last updated this group')
    )

    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='archived_groups',
        verbose_name=_('archived by'),
        null=True,
        blank=True,
        help_text=_('User who archived this group')
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
    archived_at = models.DateTimeField(
        _('archived at'),
        null=True,
        blank=True,
        help_text=_('When the group was archived (soft delete)')
    )

    class Meta:
        verbose_name = _('Group')
        verbose_name_plural = _('Groups')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_open']),
            models.Index(fields=['leader']),
            models.Index(fields=['created_at']),
            models.Index(fields=['created_by']),
            models.Index(fields=['archived_at']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Override save to auto-populate coordinates from lat/lng."""
        from django.contrib.gis.geos import Point

        # Auto-populate coordinates field from latitude/longitude
        if self.latitude is not None and self.longitude is not None:
            self.coordinates = Point(
                float(self.longitude),
                float(self.latitude),
                srid=4326
            )
        elif self.coordinates is None:
            # If coordinates exist but lat/lng don't, extract them
            pass

        super().save(*args, **kwargs)

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

    @property
    def is_archived(self):
        """Check if group is archived."""
        return self.archived_at is not None

    def archive(self, user=None):
        """
        Archive the group (soft delete).

        Args:
            user: The user who is archiving the group (optional)
        """
        self.archived_at = timezone.now()
        self.archived_by = user
        self.is_active = False
        self.is_open = False
        self.save(update_fields=[
                  'archived_at', 'archived_by', 'is_active', 'is_open', 'updated_at'])

    def unarchive(self):
        """Unarchive the group and clear archive metadata."""
        self.archived_at = None
        self.archived_by = None
        self.is_active = True
        self.save(update_fields=['archived_at',
                  'archived_by', 'is_active', 'updated_at'])


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
