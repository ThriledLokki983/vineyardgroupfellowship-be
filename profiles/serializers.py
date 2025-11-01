"""
Profiles app serializers for DRF API endpoints.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
from io import BytesIO
from drf_spectacular.utils import extend_schema_field

from .models import UserProfileBasic, ProfilePhoto, ProfileCompletenessTracker

User = get_user_model()


class UserProfileBasicSerializer(serializers.ModelSerializer):
    """
    Serializer for basic user profile information.
    """

    # Read-only computed fields
    display_name_or_email = serializers.CharField(read_only=True)

    # User information (read-only)
    email = serializers.EmailField(source='user.email', read_only=True)
    date_joined = serializers.DateTimeField(
        source='user.date_joined', read_only=True)

    # Onboarding state (read-only) - nested under 'onboarding'
    onboarding = serializers.SerializerMethodField()

    # Leadership info with group data (read-only, computed)
    leadership_info = serializers.SerializerMethodField()

    # Profile photo fields (read-only)
    photo_url = serializers.SerializerMethodField()
    photo_thumbnail_url = serializers.SerializerMethodField()
    photo_visibility = serializers.SerializerMethodField()
    can_upload_photo = serializers.SerializerMethodField()

    class Meta:
        model = UserProfileBasic
        fields = [
            'first_name',
            'last_name',
            'display_name',
            'bio',
            'location',
            'post_code',
            'timezone',
            'profile_visibility',
            'leadership_info',
            'display_name_or_email',
            'email',
            'date_joined',
            'created_at',
            'updated_at',
            'onboarding',
            'photo_url',
            'photo_thumbnail_url',
            'photo_visibility',
            'can_upload_photo',
        ]
        read_only_fields = [
            'display_name_or_email',
            'email',
            'date_joined',
            'created_at',
            'updated_at',
            'leadership_info',
            'onboarding',
            'photo_url',
            'photo_thumbnail_url',
            'photo_visibility',
            'can_upload_photo',
        ]

    def get_onboarding(self, obj):
        """Get all onboarding state as a nested object."""
        progress = self._get_onboarding_progress(obj)

        # Default values for users without onboarding progress
        if not progress:
            return {
                'completed': False,
                'current_step': None,
                'progress_percentage': 0
            }

        # Get current step - the most recent uncompleted or in-progress step
        current_step = None
        if progress.steps_completed:
            completed_steps = list(progress.steps_completed.keys())
            if completed_steps:
                # Filter out "completed" as it's not a real step
                real_steps = [
                    step for step in completed_steps if step != 'completed']
                current_step = real_steps[-1] if real_steps else None

        # Calculate completion
        progress_percentage = float(progress.completion_percentage)
        is_completed = progress_percentage >= 100.0

        return {
            'completed': is_completed,
            'current_step': current_step,
            'progress_percentage': int(progress_percentage)
        }

    def _get_onboarding_progress(self, obj):
        """Helper method to get onboarding progress with caching."""
        # Cache the progress object in the serializer context to avoid multiple queries
        if not hasattr(self, '_onboarding_progress_cache'):
            try:
                from onboarding.models import OnboardingProgress
                self._onboarding_progress_cache = OnboardingProgress.objects.filter(
                    user=obj.user
                ).first()
            except Exception:
                self._onboarding_progress_cache = None
        return self._onboarding_progress_cache

    def _get_profile_photo(self, obj):
        """Helper method to get profile photo with caching."""
        if not hasattr(self, '_profile_photo_cache'):
            try:
                self._profile_photo_cache = ProfilePhoto.objects.filter(
                    user=obj.user
                ).first()
            except Exception:
                self._profile_photo_cache = None
        return self._profile_photo_cache

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_photo_url(self, obj):
        """Get the full URL for the profile photo."""
        photo = self._get_profile_photo(obj)
        if photo and photo.has_photo:
            # Show photo to the owner regardless of moderation status
            # For public/community viewing, would need approval check
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(photo.photo.url)
        return None

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_photo_thumbnail_url(self, obj):
        """Get the full URL for the profile photo thumbnail."""
        photo = self._get_profile_photo(obj)
        if photo and photo.has_photo and photo.thumbnail:
            # Show thumbnail to the owner regardless of moderation status
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(photo.thumbnail.url)
        return None

    @extend_schema_field(serializers.ChoiceField(choices=['public', 'private', 'community']))
    def get_photo_visibility(self, obj):
        """Get the photo visibility setting."""
        photo = self._get_profile_photo(obj)
        if photo:
            return photo.photo_visibility
        return 'private'  # Default to private if no photo profile exists

    @extend_schema_field(serializers.BooleanField())
    def get_can_upload_photo(self, obj):
        """Check if user can upload a photo (always true for authenticated users)."""
        return True

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
                    'location_type': {'type': 'string'},
                    'meeting_time': {'type': 'string', 'nullable': True},
                    'is_open': {'type': 'boolean'},
                    'current_member_count': {'type': 'integer'},
                    'member_limit': {'type': 'integer'},
                    'available_spots': {'type': 'integer'},
                    'photo_url': {'type': 'string', 'nullable': True},
                    'my_role': {
                        'type': 'string',
                        'enum': ['leader', 'co_leader', 'member']
                    },
                    'created_by_me': {'type': 'boolean'},
                    'last_updated_by': {
                        'type': 'object',
                        'nullable': True,
                        'properties': {
                            'id': {'type': 'integer'},
                            'email': {'type': 'string'},
                            'display_name': {'type': 'string', 'nullable': True},
                        }
                    },
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
        Users can only be in ONE active group at a time.
        """
        # Start with existing leadership permissions from the model
        base_info = dict(obj.leadership_info) if obj.leadership_info else {}

        # Ensure can_lead_group is present
        if 'can_lead_group' not in base_info:
            base_info['can_lead_group'] = False

        # Add current group info
        user = obj.user
        from group.models import Group, GroupMembership

        # Check if user is a group leader (exclude archived groups)
        leader_group = Group.objects.filter(
            leader=user,
            is_active=True,
            archived_at__isnull=True
        ).first()
        if leader_group:
            # Get last updated by info
            last_updated_by_info = None
            if leader_group.last_updated_by:
                last_updated_by_info = {
                    'id': leader_group.last_updated_by.id,
                    'email': leader_group.last_updated_by.email,
                    'display_name': getattr(leader_group.last_updated_by.profile, 'display_name', None) if hasattr(leader_group.last_updated_by, 'profile') else None,
                }

            base_info['group'] = {
                'id': leader_group.id,
                'name': leader_group.name,
                'description': leader_group.description,
                'location': leader_group.location,
                'location_type': leader_group.location_type,
                'meeting_time': leader_group.meeting_time,
                'is_open': leader_group.is_open,
                'current_member_count': leader_group.current_member_count,
                'member_limit': leader_group.member_limit,
                'available_spots': leader_group.available_spots,
                'photo_url': self.context['request'].build_absolute_uri(leader_group.photo.url) if leader_group.photo else None,
                'my_role': 'leader',
                'created_by_me': leader_group.created_by_id == user.id if leader_group.created_by else False,
                'last_updated_by': last_updated_by_info,
                'joined_at': leader_group.created_at.isoformat(),
                'membership_status': 'active'
            }
            return base_info

        # Check if user is a co-leader (exclude archived groups)
        co_leader_group = Group.objects.filter(
            co_leaders=user,
            is_active=True,
            archived_at__isnull=True
        ).first()
        if co_leader_group:
            # Get the membership record for joined_at
            membership = GroupMembership.objects.filter(
                user=user,
                group=co_leader_group,
                status='active'
            ).first()

            # Get last updated by info
            last_updated_by_info = None
            if co_leader_group.last_updated_by:
                last_updated_by_info = {
                    'id': co_leader_group.last_updated_by.id,
                    'email': co_leader_group.last_updated_by.email,
                    'display_name': getattr(co_leader_group.last_updated_by.profile, 'display_name', None) if hasattr(co_leader_group.last_updated_by, 'profile') else None,
                }

            base_info['group'] = {
                'id': co_leader_group.id,
                'name': co_leader_group.name,
                'description': co_leader_group.description,
                'location': co_leader_group.location,
                'location_type': co_leader_group.location_type,
                'meeting_time': co_leader_group.meeting_time,
                'is_open': co_leader_group.is_open,
                'current_member_count': co_leader_group.current_member_count,
                'member_limit': co_leader_group.member_limit,
                'available_spots': co_leader_group.available_spots,
                'photo_url': self.context['request'].build_absolute_uri(co_leader_group.photo.url) if co_leader_group.photo else None,
                'my_role': 'co_leader',
                'created_by_me': co_leader_group.created_by_id == user.id if co_leader_group.created_by else False,
                'last_updated_by': last_updated_by_info,
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

            # Get last updated by info
            last_updated_by_info = None
            if group.last_updated_by:
                last_updated_by_info = {
                    'id': group.last_updated_by.id,
                    'email': group.last_updated_by.email,
                    'display_name': getattr(group.last_updated_by.profile, 'display_name', None) if hasattr(group.last_updated_by, 'profile') else None,
                }

            base_info['group'] = {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'location': group.location,
                'location_type': group.location_type,
                'meeting_time': group.meeting_time,
                'is_open': group.is_open,
                'current_member_count': group.current_member_count,
                'member_limit': group.member_limit,
                'available_spots': group.available_spots,
                'photo_url': self.context['request'].build_absolute_uri(group.photo.url) if group.photo else None,
                'my_role': 'member',
                'created_by_me': group.created_by_id == user.id if group.created_by else False,
                'last_updated_by': last_updated_by_info,
                'joined_at': membership.created_at.isoformat(),
                'membership_status': membership.status
            }
            return base_info

        # User has no active group
        base_info['group'] = None
        return base_info

    def validate_display_name(self, value):
        """Validate display name for appropriateness."""
        if value:
            # Basic validation - can be extended with profanity filters
            if len(value.strip()) < 2:
                raise serializers.ValidationError(
                    "Display name must be at least 2 characters long."
                )

            # Check for only whitespace
            if not value.strip():
                raise serializers.ValidationError(
                    "Display name cannot be only whitespace."
                )

        return value.strip() if value else value

    def validate_bio(self, value):
        """Validate bio content."""
        if value and len(value.strip()) > 1500:
            raise serializers.ValidationError(
                "Bio cannot exceed 1500 characters."
            )
        return value


class ProfilePhotoSerializer(serializers.ModelSerializer):
    """
    Serializer for profile photo upload and management.
    """

    # URLs for accessing photos
    photo_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = ProfilePhoto
        fields = [
            'photo',
            'thumbnail',
            'photo_url',
            'thumbnail_url',
            'photo_filename',
            'photo_content_type',
            'photo_size_bytes',
            'photo_visibility',
            'photo_moderation_status',
            'has_photo',
            'is_approved',
            'uploaded_at',
            'updated_at',
        ]
        read_only_fields = [
            'thumbnail',
            'photo_url',
            'thumbnail_url',
            'photo_filename',
            'photo_content_type',
            'photo_size_bytes',
            'photo_moderation_status',
            'has_photo',
            'is_approved',
            'uploaded_at',
            'updated_at',
        ]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_photo_url(self, obj):
        """Get the full URL for the photo."""
        if obj.photo:
            return self.context['request'].build_absolute_uri(obj.photo.url)
        return None

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_thumbnail_url(self, obj):
        """Get the full URL for the thumbnail."""
        if obj.thumbnail:
            return self.context['request'].build_absolute_uri(obj.thumbnail.url)
        return None

    def validate_photo(self, value):
        """Validate uploaded photo."""
        if not value:
            return value

        # Check file size (2MB limit)
        max_size = 2 * 1024 * 1024  # 2MB
        if value.size > max_size:
            raise serializers.ValidationError(
                "Photo file size cannot exceed 2MB."
            )

        # Check file type
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Only JPEG, PNG, and WebP images are allowed."
            )

        # Validate image integrity
        try:
            image = Image.open(value)
            image.verify()
        except Exception:
            raise serializers.ValidationError(
                "Invalid image file."
            )

        # Reset file pointer after verification
        value.seek(0)

        return value

    def update(self, instance, validated_data):
        """Handle photo upload and metadata extraction."""
        photo = validated_data.get('photo')

        if photo:
            # Delete old photo if exists
            if instance.photo:
                instance.delete_photo()

            # Extract metadata
            instance.photo_filename = photo.name
            instance.photo_content_type = photo.content_type
            instance.photo_size_bytes = photo.size
            # Auto-approve uploaded photos (no moderation required)
            instance.photo_moderation_status = 'approved'

        return super().update(instance, validated_data)


class ProfileCompletenessSerializer(serializers.ModelSerializer):
    """
    Serializer for profile completeness tracking.
    """

    # Recommendations for improving completeness
    recommendations = serializers.SerializerMethodField()
    completion_level_display = serializers.CharField(
        source='get_completion_level_display',
        read_only=True
    )

    class Meta:
        model = ProfileCompletenessTracker
        fields = [
            'overall_completion_percentage',
            'completion_level',
            'completion_level_display',
            'basic_info_score',
            'contact_info_score',
            'recovery_info_score',
            'preferences_score',
            'profile_media_score',
            'has_basic_profile_badge',
            'has_verified_email_badge',
            'has_recovery_goals_badge',
            'has_comprehensive_profile_badge',
            'recommendations',
            'last_calculated_at',
        ]
        read_only_fields = [
            'overall_completion_percentage',
            'completion_level',
            'completion_level_display',
            'basic_info_score',
            'contact_info_score',
            'recovery_info_score',
            'preferences_score',
            'profile_media_score',
            'has_basic_profile_badge',
            'has_verified_email_badge',
            'has_recovery_goals_badge',
            'has_comprehensive_profile_badge',
            'recommendations',
            'last_calculated_at',
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_recommendations(self, obj):
        """Generate recommendations for improving profile completeness."""
        recommendations = []

        if obj.basic_info_score < 100:
            recommendations.append({
                'category': 'basic_info',
                'title': 'Complete Basic Information',
                'description': 'Add a display name and bio to help others connect with you.',
                'priority': 'high'
            })

        if obj.profile_media_score < 100:
            recommendations.append({
                'category': 'profile_media',
                'title': 'Add Profile Photo',
                'description': 'Upload a profile photo to personalize your account.',
                'priority': 'medium'
            })

        if not obj.has_verified_email_badge:
            recommendations.append({
                'category': 'contact_info',
                'title': 'Verify Email Address',
                'description': 'Verify your email address to secure your account.',
                'priority': 'high'
            })

        if obj.preferences_score < 100:
            recommendations.append({
                'category': 'preferences',
                'title': 'Configure Privacy Settings',
                'description': 'Set up your privacy preferences and notification settings.',
                'priority': 'medium'
            })

        return recommendations


class ProfilePrivacySettingsSerializer(serializers.Serializer):
    """
    Serializer for privacy settings management.
    """

    profile_visibility = serializers.ChoiceField(
        choices=[
            ('private', 'Private'),
            ('community', 'Community Only'),
            ('public', 'Public'),
        ]
    )

    photo_visibility = serializers.ChoiceField(
        choices=[
            ('private', 'Private - Only me'),
            ('supporters', 'Supporters only'),
            ('community', 'Community members'),
            ('public', 'Public'),
        ]
    )

    # Additional privacy settings can be added here
    show_email_to_community = serializers.BooleanField(default=False)
    allow_direct_messages = serializers.BooleanField(default=True)
    show_online_status = serializers.BooleanField(default=True)


class UserProfilePublicSerializer(serializers.ModelSerializer):
    """
    Serializer for public profile view (respects privacy settings).
    """

    display_name_or_email = serializers.CharField(read_only=True)
    photo_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfileBasic
        fields = [
            'display_name_or_email',
            'bio',
            'photo_url',
            'thumbnail_url',
            'created_at',
        ]
        read_only_fields = [
            'display_name_or_email',
            'bio',
            'photo_url',
            'thumbnail_url',
            'created_at',
        ]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_photo_url(self, obj):
        """Get photo URL if visible to current user."""
        try:
            photo = obj.user.profile_photo
            if photo.has_photo and photo.is_approved:
                # Check privacy settings
                request = self.context.get('request')
                if request and request.user.is_authenticated:
                    # Apply privacy rules here
                    if photo.photo_visibility in ['public', 'community']:
                        return request.build_absolute_uri(photo.photo.url)
                elif photo.photo_visibility == 'public':
                    return request.build_absolute_uri(photo.photo.url)
        except (AttributeError, ProfilePhoto.DoesNotExist):
            pass
        return None

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_thumbnail_url(self, obj):
        """Get thumbnail URL if visible to current user."""
        try:
            photo = obj.user.profile_photo
            if photo.has_photo and photo.is_approved:
                # Check privacy settings
                request = self.context.get('request')
                if request and request.user.is_authenticated:
                    # Apply privacy rules here
                    if photo.photo_visibility in ['public', 'community']:
                        return request.build_absolute_uri(photo.thumbnail.url)
                elif photo.photo_visibility == 'public':
                    return request.build_absolute_uri(photo.thumbnail.url)
        except (AttributeError, ProfilePhoto.DoesNotExist):
            pass
        return None

    def to_representation(self, instance):
        """Filter fields based on privacy settings."""
        data = super().to_representation(instance)

        # If profile is private, only show basic info to non-owners
        request = self.context.get('request')
        if (instance.profile_visibility == 'private' and
                request and request.user != instance.user):
            # Return minimal public info for private profiles
            return {
                'display_name_or_email': data['display_name_or_email'],
                'created_at': data['created_at'],
            }

        return data


class DeviceManagementSerializer(serializers.Serializer):
    """
    Placeholder serializer for device management.
    """
    message = serializers.CharField(
        default="Device management not implemented yet")
