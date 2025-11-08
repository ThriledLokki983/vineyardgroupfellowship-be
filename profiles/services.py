"""
Profiles app business logic services.
"""

from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
import structlog

from .models import UserProfileBasic, ProfilePhoto, ProfileCompletenessTracker

logger = structlog.get_logger(__name__)
User = get_user_model()


class ProfileService:
    """
    Service for managing user profiles and related functionality.
    """

    @staticmethod
    def get_or_create_profile(user):
        """
        Get or create a basic profile for the user.
        """
        try:
            profile = UserProfileBasic.objects.get(user=user)
        except UserProfileBasic.DoesNotExist:
            profile = UserProfileBasic.objects.create(user=user)
            logger.info(
                "Created basic profile for user",
                user_id=str(user.id),
                email=user.email
            )

        return profile

    @staticmethod
    def get_or_create_photo_profile(user):
        """
        Get or create a photo profile for the user.
        """
        try:
            photo_profile = ProfilePhoto.objects.get(user=user)
        except ProfilePhoto.DoesNotExist:
            photo_profile = ProfilePhoto.objects.create(user=user)
            logger.info(
                "Created photo profile for user",
                user_id=str(user.id),
                email=user.email
            )

        return photo_profile

    @staticmethod
    def get_or_create_completeness_tracker(user):
        """
        Get or create a completeness tracker for the user.
        """
        try:
            tracker = ProfileCompletenessTracker.objects.get(user=user)
        except ProfileCompletenessTracker.DoesNotExist:
            tracker = ProfileCompletenessTracker.objects.create(user=user)
            logger.info(
                "Created completeness tracker for user",
                user_id=str(user.id),
                email=user.email
            )

        return tracker

    @staticmethod
    @transaction.atomic
    def update_profile(user, profile_data):
        """
        Update user profile with validation and logging.
        """
        profile = ProfileService.get_or_create_profile(user)

        old_values = {
            'display_name': profile.display_name,
            'bio': profile.bio,
            'timezone': profile.timezone,
            'profile_visibility': profile.profile_visibility,
        }

        # Update profile fields
        for field, value in profile_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)

        profile.save()

        # Log the update
        changes = {}
        for field, old_value in old_values.items():
            new_value = getattr(profile, field)
            if old_value != new_value:
                changes[field] = {'old': old_value, 'new': new_value}

        if changes:
            logger.info(
                "Profile updated",
                user_id=str(user.id),
                email=user.email,
                changes=changes
            )

        # Trigger completeness recalculation
        ProfileCompletenessService.calculate_completeness(user)

        return profile

    @staticmethod
    def get_public_profile(user, requesting_user=None):
        """
        Get public profile data respecting privacy settings.
        """
        try:
            profile = UserProfileBasic.objects.get(user=user)
        except UserProfileBasic.DoesNotExist:
            return None

        # Check privacy settings
        if profile.profile_visibility == 'private':
            # Only owner can see private profiles
            if requesting_user != user:
                return None
        elif profile.profile_visibility == 'community':
            # Only authenticated community members can see
            if not requesting_user or not requesting_user.is_authenticated:
                return None

        return profile


class PhotoService:
    """
    Service for managing profile photos.
    """

    @staticmethod
    @transaction.atomic
    def upload_photo(user, photo_file):
        """
        Upload and process a new profile photo (converts to Base64).
        """
        import base64
        from PIL import Image
        from io import BytesIO
        
        logger.info(
            "PhotoService.upload_photo called",
            user_id=str(user.id),
            photo_file_name=photo_file.name,
            photo_file_size=photo_file.size,
            photo_file_content_type=photo_file.content_type
        )

        photo_profile = ProfileService.get_or_create_photo_profile(user)

        logger.info(
            "Got photo profile",
            photo_profile_id=photo_profile.id,
            has_existing_photo=photo_profile.has_photo
        )

        # Delete existing photo if present
        if photo_profile.has_photo:
            old_filename = photo_profile.photo_filename
            photo_profile.delete_photo()
            logger.info(
                "Deleted old profile photo",
                user_id=str(user.id),
                old_filename=old_filename
            )

        # Convert uploaded file to Base64
        logger.info("Converting photo to Base64")
        
        # Read file data
        photo_file.seek(0)
        file_data = photo_file.read()
        
        # Encode to Base64
        base64_data = base64.b64encode(file_data).decode('utf-8')
        
        # Determine image format from content type
        content_type_map = {
            'image/jpeg': 'jpeg',
            'image/jpg': 'jpeg',
            'image/png': 'png',
            'image/webp': 'webp'
        }
        image_format = content_type_map.get(photo_file.content_type, 'jpeg')
        
        # Create data URL
        photo_data_url = f'data:{photo_file.content_type};base64,{base64_data}'
        
        # Generate thumbnail
        try:
            image = Image.open(BytesIO(file_data))
            image.thumbnail((150, 150), Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # Save thumbnail as Base64
            thumbnail_io = BytesIO()
            image.save(thumbnail_io, format='JPEG', quality=85)
            thumbnail_data = base64.b64encode(thumbnail_io.getvalue()).decode('utf-8')
            thumbnail_url = f'data:image/jpeg;base64,{thumbnail_data}'
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}")
            thumbnail_url = None
        
        # Save new photo as Base64
        logger.info("Saving Base64 photo to photo_profile")
        photo_profile.photo = photo_data_url
        photo_profile.thumbnail = thumbnail_url
        photo_profile.photo_filename = photo_file.name
        photo_profile.photo_content_type = photo_file.content_type
        photo_profile.photo_size_bytes = len(base64_data)
        # Auto-approve uploaded photos (no moderation required)
        photo_profile.photo_moderation_status = 'approved'

        logger.info(
            "About to save photo_profile",
            photo_data_length=len(photo_data_url),
            has_thumbnail=bool(thumbnail_url)
        )

        photo_profile.save()

        # Refresh from DB to verify save
        photo_profile.refresh_from_db()

        logger.info(
            "Photo profile saved and refreshed",
            has_photo_after_save=photo_profile.has_photo,
            photo_data_length=len(photo_profile.photo) if photo_profile.photo else 0
        )

        logger.info(
            "Uploaded new profile photo",
            user_id=str(user.id),
            filename=photo_file.name,
            size_bytes=photo_file.size,
            content_type=photo_file.content_type
        )

        # Trigger completeness recalculation
        ProfileCompletenessService.calculate_completeness(user)

        return photo_profile

    @staticmethod
    @transaction.atomic
    def delete_photo(user):
        """
        Delete user's profile photo.
        """
        try:
            photo_profile = ProfilePhoto.objects.get(user=user)
            if photo_profile.has_photo:
                filename = photo_profile.photo_filename
                photo_profile.delete_photo()

                logger.info(
                    "Deleted profile photo",
                    user_id=str(user.id),
                    filename=filename
                )

                # Trigger completeness recalculation
                ProfileCompletenessService.calculate_completeness(user)

                return True
        except ProfilePhoto.DoesNotExist:
            pass

        return False

    @staticmethod
    def moderate_photo(photo_profile, status, moderator_user=None):
        """
        Update photo moderation status.
        """
        old_status = photo_profile.photo_moderation_status
        photo_profile.photo_moderation_status = status
        photo_profile.save(update_fields=['photo_moderation_status'])

        logger.info(
            "Photo moderation status updated",
            user_id=str(photo_profile.user.id),
            old_status=old_status,
            new_status=status,
            moderator=str(moderator_user.id) if moderator_user else None
        )

        return photo_profile


class ProfileCompletenessService:
    """
    Service for calculating and managing profile completeness.
    """

    @staticmethod
    def calculate_completeness(user):
        """
        Calculate overall profile completeness and update tracker.
        """
        tracker = ProfileService.get_or_create_completeness_tracker(user)

        # Calculate section scores
        basic_info_score = ProfileCompletenessService._calculate_basic_info_score(
            user)
        contact_info_score = ProfileCompletenessService._calculate_contact_info_score(
            user)
        recovery_info_score = ProfileCompletenessService._calculate_recovery_info_score(
            user)
        preferences_score = ProfileCompletenessService._calculate_preferences_score(
            user)
        profile_media_score = ProfileCompletenessService._calculate_profile_media_score(
            user)

        # Update section scores
        tracker.basic_info_score = basic_info_score
        tracker.contact_info_score = contact_info_score
        tracker.recovery_info_score = recovery_info_score
        tracker.preferences_score = preferences_score
        tracker.profile_media_score = profile_media_score

        # Calculate overall completion (weighted average)
        weights = {
            'basic_info': 0.3,
            'contact_info': 0.2,
            'recovery_info': 0.2,
            'preferences': 0.15,
            'profile_media': 0.15,
        }

        overall_score = (
            basic_info_score * weights['basic_info'] +
            contact_info_score * weights['contact_info'] +
            recovery_info_score * weights['recovery_info'] +
            preferences_score * weights['preferences'] +
            profile_media_score * weights['profile_media']
        )

        tracker.overall_completion_percentage = int(overall_score)

        # Determine completion level
        if overall_score >= 90:
            tracker.completion_level = 'complete'
        elif overall_score >= 70:
            tracker.completion_level = 'comprehensive'
        elif overall_score >= 50:
            tracker.completion_level = 'standard'
        elif overall_score >= 25:
            tracker.completion_level = 'basic'
        else:
            tracker.completion_level = 'minimal'

        # Update badges
        tracker.has_basic_profile_badge = basic_info_score >= 75
        tracker.has_verified_email_badge = user.email_verified
        tracker.has_recovery_goals_badge = recovery_info_score >= 50
        tracker.has_comprehensive_profile_badge = overall_score >= 80

        tracker.save()

        logger.info(
            "Profile completeness calculated",
            user_id=str(user.id),
            overall_score=tracker.overall_completion_percentage,
            completion_level=tracker.completion_level,
            section_scores={
                'basic_info': basic_info_score,
                'contact_info': contact_info_score,
                'recovery_info': recovery_info_score,
                'preferences': preferences_score,
                'profile_media': profile_media_score,
            }
        )

        return tracker

    @staticmethod
    def _calculate_basic_info_score(user):
        """Calculate basic info completeness score (0-100)."""
        score = 0

        try:
            profile = UserProfileBasic.objects.get(user=user)

            # Display name (30 points)
            if profile.display_name and profile.display_name.strip():
                score += 30

            # Bio (40 points)
            if profile.bio and len(profile.bio.strip()) >= 50:
                score += 40
            elif profile.bio and profile.bio.strip():
                score += 20  # Partial points for short bio

            # Timezone (15 points)
            if profile.timezone and profile.timezone != 'UTC':
                score += 15

            # Profile visibility set (15 points)
            if profile.profile_visibility != 'private':
                score += 15

        except UserProfileBasic.DoesNotExist:
            pass

        return min(score, 100)

    @staticmethod
    def _calculate_contact_info_score(user):
        """Calculate contact info completeness score (0-100)."""
        score = 0

        # Email verification (70 points)
        if user.email_verified:
            score += 70

        # Email present (30 points)
        if user.email:
            score += 30

        return min(score, 100)

    @staticmethod
    def _calculate_recovery_info_score(user):
        """Calculate recovery info completeness score (0-100)."""
        # This would connect to recovery-related models when available
        # For now, return partial score based on profile completion
        score = 0

        try:
            profile = UserProfileBasic.objects.get(user=user)
            # Basic profile exists
            score += 25

            # Has bio that might indicate recovery journey
            if profile.bio and len(profile.bio.strip()) >= 100:
                score += 25

        except UserProfileBasic.DoesNotExist:
            pass

        return min(score, 100)

    @staticmethod
    def _calculate_preferences_score(user):
        """Calculate preferences completeness score (0-100)."""
        score = 0

        try:
            profile = UserProfileBasic.objects.get(user=user)

            # Privacy settings configured (40 points)
            if profile.profile_visibility:
                score += 40

            # Timezone set (30 points)
            if profile.timezone and profile.timezone != 'UTC':
                score += 30

            # Account age indicates engagement (30 points)
            if profile.created_at:
                score += 30

        except UserProfileBasic.DoesNotExist:
            pass

        return min(score, 100)

    @staticmethod
    def _calculate_profile_media_score(user):
        """Calculate profile media completeness score (0-100)."""
        score = 0

        try:
            photo = ProfilePhoto.objects.get(user=user)

            # Has uploaded photo (60 points)
            if photo.has_photo:
                score += 60

                # Photo is approved (40 points)
                if photo.is_approved:
                    score += 40

        except ProfilePhoto.DoesNotExist:
            pass

        return min(score, 100)


class PrivacyService:
    """
    Service for managing privacy settings.
    """

    @staticmethod
    def update_privacy_settings(user, privacy_data):
        """
        Update user privacy settings across profile models.
        """
        updates = {}

        # Update profile visibility
        if 'profile_visibility' in privacy_data:
            profile = ProfileService.get_or_create_profile(user)
            profile.profile_visibility = privacy_data['profile_visibility']
            profile.save(update_fields=['profile_visibility'])
            updates['profile_visibility'] = privacy_data['profile_visibility']

        # Update photo visibility
        if 'photo_visibility' in privacy_data:
            photo_profile = ProfileService.get_or_create_photo_profile(user)
            photo_profile.photo_visibility = privacy_data['photo_visibility']
            photo_profile.save(update_fields=['photo_visibility'])
            updates['photo_visibility'] = privacy_data['photo_visibility']

        if updates:
            logger.info(
                "Privacy settings updated",
                user_id=str(user.id),
                updates=updates
            )

        return updates

    @staticmethod
    def get_privacy_settings(user):
        """
        Get current privacy settings for user.
        """
        settings = {
            'profile_visibility': 'private',
            'photo_visibility': 'community',
            'show_email_to_community': False,
            'allow_direct_messages': True,
            'show_online_status': True,
        }

        try:
            profile = UserProfileBasic.objects.get(user=user)
            settings['profile_visibility'] = profile.profile_visibility
        except UserProfileBasic.DoesNotExist:
            pass

        try:
            photo = ProfilePhoto.objects.get(user=user)
            settings['photo_visibility'] = photo.photo_visibility
        except ProfilePhoto.DoesNotExist:
            pass

        return settings
