"""
Profiles app models - Basic implementation with optimized photo storage.

This provides essential profile functionality with efficient photo processing
and thumbnail generation, replacing base64 storage.
"""

import os
from io import BytesIO
from PIL import Image, ExifTags
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

User = get_user_model()


class UserProfileBasic(models.Model):
    """
    Temporary basic profile model until full migration from authentication app.

    This provides essential profile functionality while we split the monolithic
    UserProfile model from the authentication app.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='basic_profile'
    )

    # Core profile fields
    display_name = models.CharField(
        _('display name'),
        max_length=50,
        blank=True,
        help_text=_('Optional public name shown to other users')
    )

    bio = models.TextField(
        _('bio'),
        max_length=1500,
        blank=True,
        help_text=_('Optional short description about yourself')
    )

    # Basic settings
    timezone = models.CharField(
        _('timezone'),
        max_length=50,
        default='UTC',
        help_text=_('User timezone for date/time display')
    )

    # Profile visibility
    profile_visibility = models.CharField(
        _('profile visibility'),
        max_length=20,
        choices=[
            ('private', _('Private')),
            ('community', _('Community Only')),
            ('public', _('Public')),
        ],
        default='private'
    )

    # Leadership information
    leadership_info = models.JSONField(
        _('leadership information'),
        default=dict,
        blank=True,
        help_text=_('Leadership-related information and permissions')
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'profiles_user_profile_basic'
        verbose_name = _('User Profile (Basic)')
        verbose_name_plural = _('User Profiles (Basic)')
        ordering = ['-created_at']

    def __str__(self):
        return f"Basic Profile for {self.user.email}"

    @property
    def display_name_or_email(self):
        """Return display name or fall back to email."""
        return self.display_name or self.user.email.split('@')[0]

    @property
    def can_lead_group(self):
        """Check if user can lead groups."""
        return self.leadership_info.get('can_lead_group', False)

    @can_lead_group.setter
    def can_lead_group(self, value):
        """Set whether user can lead groups."""
        self.leadership_info['can_lead_group'] = bool(value)

    def set_leadership_permission(self, permission_key, value):
        """
        Set a leadership permission.

        Args:
            permission_key: The permission key (e.g., 'can_lead_group')
            value: The permission value
        """
        self.leadership_info[permission_key] = value
        self.save(update_fields=['leadership_info', 'updated_at'])

    def get_leadership_permission(self, permission_key, default=None):
        """
        Get a leadership permission.

        Args:
            permission_key: The permission key
            default: Default value if key not found

        Returns:
            The permission value or default
        """
        return self.leadership_info.get(permission_key, default)


class ProfilePhoto(models.Model):
    """
    Profile photo storage - separate from main profile for performance.

    This replaces the inefficient base64 storage in the authentication app.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile_photo'
    )

    # File storage (replaces base64)
    photo = models.ImageField(
        upload_to='profile_photos/%Y/%m/',
        null=True,
        blank=True,
        help_text=_('Profile photo (max 2MB)')
    )

    thumbnail = models.ImageField(
        upload_to='profile_thumbnails/%Y/%m/',
        null=True,
        blank=True,
        help_text=_('Auto-generated thumbnail (150x150)')
    )

    # Photo metadata
    photo_filename = models.CharField(
        _('original filename'),
        max_length=255,
        blank=True
    )

    photo_content_type = models.CharField(
        _('content type'),
        max_length=50,
        blank=True
    )

    photo_size_bytes = models.PositiveIntegerField(
        _('file size in bytes'),
        null=True,
        blank=True
    )

    # Privacy settings
    photo_visibility = models.CharField(
        _('photo visibility'),
        max_length=20,
        choices=[
            ('private', _('Private - Only me')),
            ('supporters', _('Supporters only')),
            ('community', _('Community members')),
            ('public', _('Public')),
        ],
        default='community'
    )

    # Moderation
    photo_moderation_status = models.CharField(
        _('moderation status'),
        max_length=20,
        choices=[
            ('pending', _('Pending Review')),
            ('approved', _('Approved')),
            ('rejected', _('Rejected')),
            ('flagged', _('Flagged for Review')),
        ],
        default='approved'  # Auto-approve photos (no moderation required)
    )

    # Timestamps
    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'profiles_profile_photo'
        verbose_name = _('Profile Photo')
        verbose_name_plural = _('Profile Photos')

    def __str__(self):
        return f"Photo for {self.user.email}"

    @property
    def has_photo(self) -> bool:
        """Check if user has uploaded a photo."""
        return bool(self.photo)

    @property
    def is_approved(self) -> bool:
        """Check if photo is approved for display."""
        return self.photo_moderation_status == 'approved'

    def delete_photo(self):
        """Delete photo files and reset metadata."""
        if self.photo:
            self.photo.delete(save=False)
        if self.thumbnail:
            self.thumbnail.delete(save=False)

        self.photo_filename = ''
        self.photo_content_type = ''
        self.photo_size_bytes = None
        # Reset to approved (will be overwritten when new photo is uploaded)
        self.photo_moderation_status = 'approved'
        self.save()

    def save(self, *args, **kwargs):
        """Auto-generate thumbnail on save."""
        super().save(*args, **kwargs)
        if self.photo and not self.thumbnail:
            self.generate_thumbnail()

    def generate_thumbnail(self):
        """Generate optimized thumbnail (150x150) from uploaded photo."""
        if not self.photo:
            return

        try:
            # Open the uploaded image
            image = Image.open(self.photo.path)

            # Handle EXIF orientation
            image = self._fix_orientation(image)

            # Convert to RGB if necessary (handles RGBA, P mode images)
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')

            # Create thumbnail with smart cropping
            thumbnail = self._create_smart_thumbnail(image, (150, 150))

            # Save thumbnail to memory
            thumbnail_io = BytesIO()
            thumbnail.save(thumbnail_io, format='JPEG',
                           quality=90, optimize=True)

            # Generate thumbnail filename
            base_name = os.path.splitext(os.path.basename(self.photo.name))[0]
            thumbnail_name = f"{base_name}_thumb.jpg"

            # Save thumbnail to storage
            self.thumbnail.save(
                thumbnail_name,
                ContentFile(thumbnail_io.getvalue()),
                save=False
            )

            # Update model without triggering save recursion
            ProfilePhoto.objects.filter(pk=self.pk).update(
                thumbnail=self.thumbnail.name
            )

        except Exception as e:
            # Log error but don't break the save process
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to generate thumbnail for user {self.user.id}: {e}")

    def _fix_orientation(self, image):
        """Fix image orientation based on EXIF data."""
        try:
            exif = image._getexif()
            if exif is not None:
                for tag, value in exif.items():
                    if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                        if value == 3:
                            image = image.rotate(180, expand=True)
                        elif value == 6:
                            image = image.rotate(270, expand=True)
                        elif value == 8:
                            image = image.rotate(90, expand=True)
                        break
        except (AttributeError, KeyError, TypeError):
            # No EXIF data or unsupported format, return as is
            pass
        return image

    def _create_smart_thumbnail(self, image, size):
        """Create thumbnail with smart center cropping."""
        # Calculate aspect ratios
        target_ratio = size[0] / size[1]
        image_ratio = image.width / image.height

        if image_ratio > target_ratio:
            # Image is wider than target - crop width
            new_width = int(image.height * target_ratio)
            left = (image.width - new_width) // 2
            crop_box = (left, 0, left + new_width, image.height)
        else:
            # Image is taller than target - crop height
            new_height = int(image.width / target_ratio)
            top = (image.height - new_height) // 2
            crop_box = (0, top, image.width, top + new_height)

        # Crop and resize
        cropped = image.crop(crop_box)
        return cropped.resize(size, Image.Resampling.LANCZOS)

    def generate_optimized_sizes(self):
        """Generate multiple optimized sizes for different use cases."""
        if not self.photo:
            return

        try:
            image = Image.open(self.photo.path)
            image = self._fix_orientation(image)

            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')

            # Generate medium size (400x400) for profile pages
            medium = self._create_smart_thumbnail(image, (400, 400))
            medium_io = BytesIO()
            medium.save(medium_io, format='JPEG', quality=85, optimize=True)

            # Could save medium size to a separate field if needed
            # For now, we'll focus on the essential thumbnail

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to generate optimized sizes for user {self.user.id}: {e}")


class ProfileCompletenessTracker(models.Model):
    """
    Track profile completion status and provide recommendations.

    This model tracks completion across multiple profile models and provides
    insights into what users can do to improve their profile completeness.
    """

    COMPLETION_LEVELS = [
        ('minimal', 'Minimal - Basic account setup'),
        ('basic', 'Basic - Essential information provided'),
        ('standard', 'Standard - Good profile coverage'),
        ('comprehensive', 'Comprehensive - Detailed profile'),
        ('complete', 'Complete - All optional fields filled'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile_completeness'
    )

    # Overall completion metrics
    overall_completion_percentage = models.PositiveIntegerField(
        default=0,
        help_text='Overall profile completion percentage (0-100)'
    )

    completion_level = models.CharField(
        max_length=20,
        choices=COMPLETION_LEVELS,
        default='minimal',
        help_text='Current completion level based on percentage'
    )

    # Section-specific completion scores
    basic_info_score = models.PositiveIntegerField(
        default=0)  # Name, bio, location
    contact_info_score = models.PositiveIntegerField(
        default=0)  # Email verified, phone number
    recovery_info_score = models.PositiveIntegerField(default=0)
    # Privacy, notifications, etc.
    preferences_score = models.PositiveIntegerField(default=0)
    # Profile photos, etc.
    profile_media_score = models.PositiveIntegerField(default=0)

    # Completion badges/achievements
    has_basic_profile_badge = models.BooleanField(default=False)
    has_verified_email_badge = models.BooleanField(default=False)
    has_recovery_goals_badge = models.BooleanField(default=False)
    has_comprehensive_profile_badge = models.BooleanField(default=False)

    # Tracking metadata
    last_calculated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'profiles_completeness_tracker'
        verbose_name = _('Profile Completeness Tracker')
        verbose_name_plural = _('Profile Completeness Trackers')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['completion_level']),
            models.Index(fields=['overall_completion_percentage']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.overall_completion_percentage}% ({self.completion_level})"
