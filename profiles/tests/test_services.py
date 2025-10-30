"""
Unit tests for profiles app services.

Tests service layer business logic including:
- Profile management services
- Photo processing services
- Completeness calculation services
- Privacy services
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, Mock, MagicMock
from PIL import Image
from io import BytesIO

from profiles.services import (
    ProfileService,
    PhotoService,
    ProfileCompletenessService,
    PrivacyService
)
from profiles.models import (
    UserProfileBasic,
    ProfilePhoto,
    ProfileCompletenessTracker
)
from .factories import (
    UserFactory,
    UserProfileBasicFactory,
    ProfilePhotoFactory,
    ProfileCompletenessTrackerFactory,
    CompleteUserProfileFactory
)

User = get_user_model()


class ProfileServiceTest(TestCase):
    """Test ProfileService business logic."""

    def setUp(self):
        self.user = UserFactory()

    def test_get_or_create_profile(self):
        """Test getting or creating user profile."""
        # Should create new profile if doesn't exist
        profile = ProfileService.get_or_create_profile(self.user)

        self.assertIsInstance(profile, UserProfileBasic)
        self.assertEqual(profile.user, self.user)

        # Should return existing profile
        existing_profile = ProfileService.get_or_create_profile(self.user)
        self.assertEqual(profile.id, existing_profile.id)

    def test_update_profile(self):
        """Test updating user profile."""
        profile = UserProfileBasicFactory(user=self.user)

        update_data = {
            'display_name': 'Updated Name',
            'bio': 'Updated bio',
            'timezone': 'Europe/London'
        }

        updated_profile = ProfileService.update_profile(self.user, update_data)

        self.assertEqual(updated_profile.display_name, 'Updated Name')
        self.assertEqual(updated_profile.bio, 'Updated bio')
        self.assertEqual(updated_profile.timezone, 'Europe/London')

    @patch('profiles.services.ProfileCompletenessService.calculate_completeness')
    def test_update_profile_triggers_completeness_calculation(self, mock_calculate):
        """Test that updating profile triggers completeness recalculation."""
        profile = UserProfileBasicFactory(user=self.user)

        mock_calculate.return_value = {
            'overall_percentage': 75,
            'completion_level': 'intermediate'
        }

        update_data = {'display_name': 'New Name'}
        ProfileService.update_profile(self.user, update_data)

        # Should trigger completeness calculation
        mock_calculate.assert_called_once_with(self.user)

    def test_get_public_profile_data(self):
        """Test getting public profile data with privacy filtering."""
        profile = UserProfileBasicFactory(
            user=self.user,
            profile_visibility='public',
            show_email=True,
            show_full_name=False
        )

        public_data = ProfileService.get_public_profile_data(self.user)

        self.assertIsNotNone(public_data)
        self.assertEqual(public_data['display_name'], profile.display_name)
        self.assertEqual(public_data['profile_visibility'], 'public')

    def test_get_private_profile_denied(self):
        """Test that private profiles cannot be accessed publicly."""
        profile = UserProfileBasicFactory(
            user=self.user,
            profile_visibility='private'
        )

        public_data = ProfileService.get_public_profile_data(self.user)

        self.assertIsNone(public_data)

    def test_delete_profile_data(self):
        """Test deleting user profile data."""
        profile = UserProfileBasicFactory(user=self.user)
        photo = ProfilePhotoFactory(user=self.user)
        tracker = ProfileCompletenessTrackerFactory(user=self.user)

        ProfileService.delete_user_profile_data(self.user)

        # Verify all profile data is deleted
        self.assertFalse(UserProfileBasic.objects.filter(
            user=self.user).exists())
        self.assertFalse(ProfilePhoto.objects.filter(user=self.user).exists())
        self.assertFalse(ProfileCompletenessTracker.objects.filter(
            user=self.user).exists())

    def test_export_profile_data(self):
        """Test exporting user profile data for GDPR compliance."""
        profile = UserProfileBasicFactory(user=self.user)
        photo = ProfilePhotoFactory(user=self.user)

        export_data = ProfileService.export_user_profile_data(self.user)

        self.assertIn('profile', export_data)
        self.assertIn('photos', export_data)
        self.assertEqual(export_data['profile']
                         ['display_name'], profile.display_name)
        self.assertEqual(len(export_data['photos']), 1)


class PhotoServiceTest(TestCase):
    """Test PhotoService business logic."""

    def setUp(self):
        self.user = UserFactory()

    def create_test_image(self, size=(300, 300), format='JPEG'):
        """Helper to create test image."""
        image = Image.new('RGB', size, color='red')
        image_io = BytesIO()
        image.save(image_io, format=format)
        image_io.seek(0)

        return SimpleUploadedFile(
            name='test_photo.jpg',
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )

    @patch('profiles.services.PhotoService._process_photo')
    def test_upload_photo_new(self, mock_process):
        """Test uploading new photo."""
        test_image = self.create_test_image()

        mock_process.return_value = (
            test_image, test_image)  # (photo, thumbnail)

        photo = PhotoService.upload_photo(self.user, test_image)

        self.assertIsInstance(photo, ProfilePhoto)
        self.assertEqual(photo.user, self.user)
        self.assertEqual(photo.moderation_status, 'pending')
        mock_process.assert_called_once()

    @patch('profiles.services.PhotoService._process_photo')
    def test_upload_photo_replace_existing(self, mock_process):
        """Test replacing existing photo."""
        # Create existing photo
        existing_photo = ProfilePhotoFactory(user=self.user)
        existing_id = existing_photo.id

        test_image = self.create_test_image()
        mock_process.return_value = (test_image, test_image)

        new_photo = PhotoService.upload_photo(self.user, test_image)

        # Should replace existing photo
        self.assertNotEqual(new_photo.id, existing_id)
        self.assertFalse(ProfilePhoto.objects.filter(id=existing_id).exists())

    def test_delete_photo(self):
        """Test deleting user photo."""
        photo = ProfilePhotoFactory(user=self.user)

        result = PhotoService.delete_photo(self.user)

        self.assertTrue(result)
        self.assertFalse(ProfilePhoto.objects.filter(user=self.user).exists())

    def test_delete_photo_no_photo(self):
        """Test deleting photo when no photo exists."""
        result = PhotoService.delete_photo(self.user)

        self.assertFalse(result)

    def test_get_photo_info(self):
        """Test getting photo information."""
        photo = ProfilePhotoFactory(user=self.user)

        photo_info = PhotoService.get_photo_info(self.user)

        self.assertIsNotNone(photo_info)
        self.assertEqual(photo_info.id, photo.id)

    def test_get_photo_info_no_photo(self):
        """Test getting photo info when no photo exists."""
        photo_info = PhotoService.get_photo_info(self.user)

        self.assertIsNone(photo_info)

    @patch('profiles.services.default_storage.delete')
    def test_cleanup_orphaned_photos(self, mock_delete):
        """Test cleaning up orphaned photo files."""
        # This would test a method that cleans up photo files
        # that exist in storage but have no database record

        orphaned_files = ['photos/orphan1.jpg', 'photos/orphan2.jpg']

        # Mock the cleanup method
        with patch.object(PhotoService, 'get_orphaned_photo_files',
                          return_value=orphaned_files):
            cleaned_count = PhotoService.cleanup_orphaned_photos()

            self.assertEqual(cleaned_count, 2)
            self.assertEqual(mock_delete.call_count, 2)

    def test_moderate_photo(self):
        """Test photo moderation."""
        photo = ProfilePhotoFactory(
            user=self.user,
            moderation_status='pending',
            is_moderated=False
        )

        PhotoService.moderate_photo(photo.id, 'approved', 'admin_user')

        photo.refresh_from_db()
        self.assertEqual(photo.moderation_status, 'approved')
        self.assertTrue(photo.is_moderated)

    def test_process_photo_orientation(self):
        """Test photo processing handles EXIF orientation."""
        # Create image with EXIF orientation data
        test_image = self.create_test_image()

        # Mock EXIF processing
        with patch('PIL.Image.open') as mock_open:
            mock_img = Mock()
            mock_img.size = (300, 300)
            mock_img.format = 'JPEG'
            mock_open.return_value = mock_img

            processed_photo, thumbnail = PhotoService._process_photo(
                test_image)

            self.assertIsNotNone(processed_photo)
            self.assertIsNotNone(thumbnail)


class ProfileCompletenessServiceTest(TestCase):
    """Test ProfileCompletenessService business logic."""

    def setUp(self):
        self.user = UserFactory()

    def test_calculate_completeness_empty_profile(self):
        """Test completeness calculation for empty profile."""
        # Create minimal profile
        profile = UserProfileBasicFactory(
            user=self.user,
            display_name='',
            bio=''
        )

        completeness = ProfileCompletenessService.calculate_completeness(
            self.user)

        self.assertLess(completeness['overall_percentage'], 50)
        self.assertEqual(completeness['completion_level'], 'beginner')
        self.assertFalse(completeness['has_display_name'])
        self.assertFalse(completeness['has_bio'])
        self.assertFalse(completeness['has_photo'])

    def test_calculate_completeness_complete_profile(self):
        """Test completeness calculation for complete profile."""
        # Create complete profile
        profile = UserProfileBasicFactory(
            user=self.user,
            display_name='Complete User',
            bio='This is a complete bio'
        )
        photo = ProfilePhotoFactory(
            user=self.user, moderation_status='approved')

        completeness = ProfileCompletenessService.calculate_completeness(
            self.user)

        self.assertGreater(completeness['overall_percentage'], 80)
        self.assertIn(completeness['completion_level'], ['advanced', 'expert'])
        self.assertTrue(completeness['has_display_name'])
        self.assertTrue(completeness['has_bio'])
        self.assertTrue(completeness['has_photo'])

    def test_update_completeness_tracker(self):
        """Test updating completeness tracker."""
        profile = UserProfileBasicFactory(user=self.user)

        ProfileCompletenessService.update_completeness_tracker(self.user)

        # Should create tracker if doesn't exist
        self.assertTrue(ProfileCompletenessTracker.objects.filter(
            user=self.user).exists())

        tracker = ProfileCompletenessTracker.objects.get(user=self.user)
        self.assertIsNotNone(tracker.last_calculated)

    def test_get_completion_recommendations(self):
        """Test getting completion recommendations."""
        profile = UserProfileBasicFactory(
            user=self.user,
            display_name='',  # Missing
            bio='Has bio'     # Has
        )

        recommendations = ProfileCompletenessService.get_completion_recommendations(
            self.user)

        self.assertIn('Add a display name', recommendations)
        self.assertIn('Upload a profile photo', recommendations)
        self.assertNotIn('Add a bio', recommendations)  # Already has bio

    def test_award_completion_badges(self):
        """Test awarding completion badges."""
        profile = CompleteUserProfileFactory(user=self.user)

        badges = ProfileCompletenessService.award_completion_badges(self.user)

        expected_badges = ['first_photo', 'profile_complete', 'bio_writer']
        for badge in expected_badges:
            self.assertIn(badge, badges)

    def test_calculate_individual_scores(self):
        """Test calculating individual completion scores."""
        profile = UserProfileBasicFactory(
            user=self.user,
            display_name='Test User',
            bio=''  # Missing bio
        )

        scores = ProfileCompletenessService._calculate_individual_scores(
            self.user)

        # Should have partial basic info score
        self.assertGreater(scores['basic_info_score'], 0)
        self.assertLess(scores['basic_info_score'], 100)

        # Should have zero photo score
        self.assertEqual(scores['photo_score'], 0)


class PrivacyServiceTest(TestCase):
    """Test PrivacyService business logic."""

    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()

    def test_can_view_profile_public(self):
        """Test viewing public profile."""
        profile = UserProfileBasicFactory(
            user=self.user,
            profile_visibility='public'
        )

        # Anyone can view public profile
        self.assertTrue(PrivacyService.can_view_profile(
            self.user, self.other_user))
        self.assertTrue(PrivacyService.can_view_profile(
            self.user, None))  # Anonymous

    def test_can_view_profile_private(self):
        """Test viewing private profile."""
        profile = UserProfileBasicFactory(
            user=self.user,
            profile_visibility='private'
        )

        # Only user can view private profile
        self.assertTrue(PrivacyService.can_view_profile(self.user, self.user))
        self.assertFalse(PrivacyService.can_view_profile(
            self.user, self.other_user))
        self.assertFalse(PrivacyService.can_view_profile(self.user, None))

    def test_can_view_profile_community(self):
        """Test viewing community profile."""
        profile = UserProfileBasicFactory(
            user=self.user,
            profile_visibility='community'
        )

        # Authenticated users can view community profile
        self.assertTrue(PrivacyService.can_view_profile(
            self.user, self.other_user))
        self.assertFalse(PrivacyService.can_view_profile(
            self.user, None))  # Anonymous

    def test_filter_profile_data_by_privacy(self):
        """Test filtering profile data based on privacy settings."""
        profile = UserProfileBasicFactory(
            user=self.user,
            show_email=False,
            show_full_name=True
        )

        filtered_data = PrivacyService.filter_profile_data_by_privacy(
            profile, self.other_user
        )

        # Should not include email
        self.assertNotIn('email', filtered_data.get('user', {}))

        # Should include full name
        if 'user' in filtered_data:
            self.assertIn('first_name', filtered_data['user'])

    def test_get_privacy_settings(self):
        """Test getting privacy settings."""
        profile = UserProfileBasicFactory(
            user=self.user,
            profile_visibility='community',
            show_email=True,
            show_full_name=False
        )

        privacy_settings = PrivacyService.get_privacy_settings(self.user)

        self.assertEqual(privacy_settings['profile_visibility'], 'community')
        self.assertTrue(privacy_settings['show_email'])
        self.assertFalse(privacy_settings['show_full_name'])

    def test_update_privacy_settings(self):
        """Test updating privacy settings."""
        profile = UserProfileBasicFactory(user=self.user)

        new_settings = {
            'profile_visibility': 'public',
            'show_email': True,
            'show_full_name': True
        }

        updated_profile = PrivacyService.update_privacy_settings(
            self.user, new_settings)

        self.assertEqual(updated_profile.profile_visibility, 'public')
        self.assertTrue(updated_profile.show_email)
        self.assertTrue(updated_profile.show_full_name)

    def test_validate_privacy_settings(self):
        """Test privacy settings validation."""
        # Valid settings
        valid_settings = {
            'profile_visibility': 'community',
            'show_email': False,
            'show_full_name': True
        }

        is_valid, errors = PrivacyService.validate_privacy_settings(
            valid_settings)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Invalid settings
        invalid_settings = {
            'profile_visibility': 'invalid_choice'
        }

        is_valid, errors = PrivacyService.validate_privacy_settings(
            invalid_settings)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


@pytest.mark.django_db
class ProfileServicesTestsWithPytest:
    """Pytest-style tests for profile services."""

    def test_profile_service_creates_profile(self):
        """Test ProfileService creates profile correctly."""
        user = UserFactory()

        profile = ProfileService.get_or_create_profile(user)

        assert profile.user == user
        assert isinstance(profile, UserProfileBasic)

    def test_photo_service_handles_upload(self):
        """Test PhotoService handles photo upload."""
        user = UserFactory()

        # Create test image
        image = Image.new('RGB', (300, 300), color='red')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)

        test_image = SimpleUploadedFile(
            name='test.jpg',
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )

        with patch('profiles.services.PhotoService._process_photo') as mock_process:
            mock_process.return_value = (test_image, test_image)

            photo = PhotoService.upload_photo(user, test_image)

            assert photo.user == user
            assert photo.moderation_status == 'pending'

    def test_completeness_service_calculates_correctly(self):
        """Test ProfileCompletenessService calculations."""
        user = UserFactory()
        profile = UserProfileBasicFactory(
            user=user,
            display_name='Test User',
            bio='Test bio'
        )

        completeness = ProfileCompletenessService.calculate_completeness(user)

        assert 'overall_percentage' in completeness
        assert 'completion_level' in completeness
        assert completeness['has_display_name'] is True
        assert completeness['has_bio'] is True

    def test_privacy_service_enforces_rules(self):
        """Test PrivacyService enforces privacy rules."""
        user = UserFactory()
        other_user = UserFactory()

        # Private profile
        profile = UserProfileBasicFactory(
            user=user,
            profile_visibility='private'
        )

        # Other user cannot view private profile
        can_view = PrivacyService.can_view_profile(user, other_user)
        assert can_view is False

        # User can view own private profile
        can_view_own = PrivacyService.can_view_profile(user, user)
        assert can_view_own is True
