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
    display_name_or_email = serializers.ReadOnlyField()

    # User information (read-only)
    email = serializers.EmailField(source='user.email', read_only=True)
    date_joined = serializers.DateTimeField(
        source='user.date_joined', read_only=True)

    class Meta:
        model = UserProfileBasic
        fields = [
            'display_name',
            'bio',
            'timezone',
            'profile_visibility',
            'display_name_or_email',
            'email',
            'date_joined',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'display_name_or_email',
            'email',
            'date_joined',
            'created_at',
            'updated_at',
        ]

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
            instance.photo_moderation_status = 'pending'

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

    display_name_or_email = serializers.ReadOnlyField()
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
