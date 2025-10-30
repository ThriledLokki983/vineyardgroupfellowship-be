"""
Unit tests for profiles app models.

Tests all model functionality including:
- Model creation and validation
- Model methods and properties
- Model relationships
- Photo processing
- Completeness calculations
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from io import BytesIO
import tempfile
import os

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


class UserProfileBasicModelTest(TestCase):
    """Test UserProfileBasic model."""

    def setUp(self):
        self.user = UserFactory()

    def test_profile_creation(self):
        """Test basic profile creation."""
        profile = UserProfileBasicFactory(user=self.user)

        self.assertIsInstance(profile, UserProfileBasic)
        self.assertEqual(profile.user, self.user)
        self.assertIsNotNone(profile.display_name)
        self.assertIsNotNone(profile.bio)

    def test_profile_str_representation(self):
        """Test profile string representation."""
        profile = UserProfileBasicFactory(
            user=self.user, display_name="Test User")

        expected = f"{self.user.username} - Test User"
        self.assertEqual(str(profile), expected)

    def test_display_name_or_username(self):
        """Test display_name_or_username property."""
        # With display name
        profile = UserProfileBasicFactory(
            user=self.user,
            display_name="Test Display"
        )
        self.assertEqual(profile.display_name_or_username, "Test Display")

        # Without display name
        profile.display_name = ""
        profile.save()
        self.assertEqual(profile.display_name_or_username, self.user.username)

    def test_has_basic_info(self):
        """Test has_basic_info property."""
        # Complete basic info
        profile = UserProfileBasicFactory(
            user=self.user,
            display_name="Test User",
            bio="Test bio"
        )
        self.assertTrue(profile.has_basic_info)

        # Incomplete basic info
        profile.display_name = ""
        profile.bio = ""
        profile.save()
        self.assertFalse(profile.has_basic_info)

    def test_profile_visibility_choices(self):
        """Test profile visibility choices."""
        profile = UserProfileBasicFactory(user=self.user)

        valid_choices = ['private', 'community', 'public']
        for choice in valid_choices:
            profile.profile_visibility = choice
            profile.save()
            self.assertEqual(profile.profile_visibility, choice)

    def test_timezone_field(self):
        """Test timezone field."""
        profile = UserProfileBasicFactory(
            user=self.user,
            timezone='America/New_York'
        )
        self.assertEqual(profile.timezone, 'America/New_York')

    def test_one_to_one_relationship(self):
        """Test one-to-one relationship with User."""
        profile = UserProfileBasicFactory(user=self.user)

        # Check forward relationship
        self.assertEqual(profile.user, self.user)

        # Check reverse relationship
        self.assertEqual(self.user.basic_profile, profile)

    def test_privacy_settings(self):
        """Test privacy settings."""
        profile = UserProfileBasicFactory(
            user=self.user,
            show_email=True,
            show_full_name=False
        )

        self.assertTrue(profile.show_email)
        self.assertFalse(profile.show_full_name)


class ProfilePhotoModelTest(TestCase):
    """Test ProfilePhoto model."""

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

    def test_photo_creation(self):
        """Test photo creation."""
        photo = ProfilePhotoFactory(user=self.user)

        self.assertIsInstance(photo, ProfilePhoto)
        self.assertEqual(photo.user, self.user)
        self.assertIsNotNone(photo.uploaded_at)

    def test_photo_str_representation(self):
        """Test photo string representation."""
        photo = ProfilePhotoFactory(user=self.user)

        expected = f"{self.user.username} - Profile Photo"
        self.assertEqual(str(photo), expected)

    def test_moderation_status_choices(self):
        """Test moderation status choices."""
        photo = ProfilePhotoFactory(user=self.user)

        valid_statuses = ['pending', 'approved', 'rejected']
        for status in valid_statuses:
            photo.moderation_status = status
            photo.save()
            self.assertEqual(photo.moderation_status, status)

    def test_is_approved_property(self):
        """Test is_approved property."""
        # Approved photo
        photo = ProfilePhotoFactory(
            user=self.user,
            moderation_status='approved'
        )
        self.assertTrue(photo.is_approved)

        # Pending photo
        photo.moderation_status = 'pending'
        photo.save()
        self.assertFalse(photo.is_approved)

        # Rejected photo
        photo.moderation_status = 'rejected'
        photo.save()
        self.assertFalse(photo.is_approved)

    def test_can_display_property(self):
        """Test can_display property."""
        # Approved and moderated
        photo = ProfilePhotoFactory(
            user=self.user,
            is_moderated=True,
            moderation_status='approved'
        )
        self.assertTrue(photo.can_display)

        # Not moderated
        photo.is_moderated = False
        photo.save()
        self.assertFalse(photo.can_display)

        # Rejected
        photo.is_moderated = True
        photo.moderation_status = 'rejected'
        photo.save()
        self.assertFalse(photo.can_display)

    def test_one_to_one_relationship(self):
        """Test one-to-one relationship with User."""
        photo = ProfilePhotoFactory(user=self.user)

        # Check forward relationship
        self.assertEqual(photo.user, self.user)

        # Check reverse relationship (if it exists)
        self.assertTrue(hasattr(self.user, 'profile_photo'))


class ProfileCompletenessTrackerModelTest(TestCase):
    """Test ProfileCompletenessTracker model."""

    def setUp(self):
        self.user = UserFactory()

    def test_tracker_creation(self):
        """Test completeness tracker creation."""
        tracker = ProfileCompletenessTrackerFactory(user=self.user)

        self.assertIsInstance(tracker, ProfileCompletenessTracker)
        self.assertEqual(tracker.user, self.user)
        self.assertIsNotNone(tracker.last_calculated)

    def test_tracker_str_representation(self):
        """Test tracker string representation."""
        tracker = ProfileCompletenessTrackerFactory(
            user=self.user,
            overall_percentage=75
        )

        expected = f"{self.user.username} - 75% complete"
        self.assertEqual(str(tracker), expected)

    def test_completion_level_choices(self):
        """Test completion level choices."""
        tracker = ProfileCompletenessTrackerFactory(user=self.user)

        valid_levels = ['beginner', 'intermediate', 'advanced', 'expert']
        for level in valid_levels:
            tracker.completion_level = level
            tracker.save()
            self.assertEqual(tracker.completion_level, level)

    def test_is_complete_property(self):
        """Test is_complete property."""
        # Complete profile
        tracker = ProfileCompletenessTrackerFactory(
            user=self.user,
            overall_percentage=100
        )
        self.assertTrue(tracker.is_complete)

        # Incomplete profile
        tracker.overall_percentage = 75
        tracker.save()
        self.assertFalse(tracker.is_complete)

    def test_badges_earned_field(self):
        """Test badges_earned JSON field."""
        badges = ['first_photo', 'profile_complete', 'community_member']
        tracker = ProfileCompletenessTrackerFactory(
            user=self.user,
            badges_earned=badges
        )

        self.assertEqual(tracker.badges_earned, badges)
        self.assertIn('first_photo', tracker.badges_earned)

    def test_score_fields_range(self):
        """Test score fields are within valid range."""
        tracker = ProfileCompletenessTrackerFactory(
            user=self.user,
            overall_percentage=85,
            basic_info_score=90,
            photo_score=80,
            privacy_score=85
        )

        # Check all scores are within 0-100 range
        self.assertGreaterEqual(tracker.overall_percentage, 0)
        self.assertLessEqual(tracker.overall_percentage, 100)
        self.assertGreaterEqual(tracker.basic_info_score, 0)
        self.assertLessEqual(tracker.basic_info_score, 100)
        self.assertGreaterEqual(tracker.photo_score, 0)
        self.assertLessEqual(tracker.photo_score, 100)
        self.assertGreaterEqual(tracker.privacy_score, 0)
        self.assertLessEqual(tracker.privacy_score, 100)

    def test_boolean_flags(self):
        """Test boolean completion flags."""
        tracker = ProfileCompletenessTrackerFactory(
            user=self.user,
            has_display_name=True,
            has_bio=True,
            has_photo=False,
            has_privacy_settings=True
        )

        self.assertTrue(tracker.has_display_name)
        self.assertTrue(tracker.has_bio)
        self.assertFalse(tracker.has_photo)
        self.assertTrue(tracker.has_privacy_settings)

    def test_one_to_one_relationship(self):
        """Test one-to-one relationship with User."""
        tracker = ProfileCompletenessTrackerFactory(user=self.user)

        # Check forward relationship
        self.assertEqual(tracker.user, self.user)


class ModelIntegrationTest(TestCase):
    """Test model integrations and relationships."""

    def setUp(self):
        self.user = UserFactory()

    def test_complete_profile_integration(self):
        """Test complete profile with all related models."""
        # Create profile
        profile = UserProfileBasicFactory(
            user=self.user,
            display_name="Test User",
            bio="Test bio",
            is_profile_complete=True
        )

        # Create photo
        photo = ProfilePhotoFactory(
            user=self.user,
            moderation_status='approved'
        )

        # Create completeness tracker
        tracker = ProfileCompletenessTrackerFactory(
            user=self.user,
            overall_percentage=100,
            has_display_name=True,
            has_bio=True,
            has_photo=True
        )

        # Test relationships
        self.assertEqual(self.user.basic_profile, profile)
        self.assertEqual(profile.user, self.user)
        self.assertTrue(photo.can_display)
        self.assertTrue(tracker.is_complete)

    def test_user_deletion_cascade(self):
        """Test that related models are deleted when user is deleted."""
        # Create related models
        profile = UserProfileBasicFactory(user=self.user)
        photo = ProfilePhotoFactory(user=self.user)
        tracker = ProfileCompletenessTrackerFactory(user=self.user)

        # Get IDs
        profile_id = profile.id
        photo_id = photo.id
        tracker_id = tracker.id

        # Delete user
        self.user.delete()

        # Verify related models are deleted
        self.assertFalse(UserProfileBasic.objects.filter(
            id=profile_id).exists())
        self.assertFalse(ProfilePhoto.objects.filter(id=photo_id).exists())
        self.assertFalse(ProfileCompletenessTracker.objects.filter(
            id=tracker_id).exists())


@pytest.mark.django_db
class ProfileModelTestsWithPytest:
    """Pytest-style tests for profiles models."""

    def test_profile_factory_creates_valid_profile(self):
        """Test that factory creates valid profile."""
        profile = UserProfileBasicFactory()

        assert profile.user is not None
        assert profile.user.email is not None
        assert profile.timezone in [
            'UTC', 'America/New_York', 'Europe/London', 'Asia/Tokyo']

    def test_photo_factory_creates_valid_photo(self):
        """Test that factory creates valid photo."""
        photo = ProfilePhotoFactory()

        assert photo.user is not None
        assert photo.photo is not None
        assert photo.moderation_status in ['pending', 'approved', 'rejected']

    def test_completeness_factory_creates_valid_tracker(self):
        """Test that factory creates valid tracker."""
        tracker = ProfileCompletenessTrackerFactory()

        assert tracker.user is not None
        assert 0 <= tracker.overall_percentage <= 100
        assert tracker.completion_level in [
            'beginner', 'intermediate', 'advanced', 'expert']
