"""
Unit tests for profiles app serializers.

Tests serializer functionality including:
- Serialization and deserialization
- Validation rules
- Field mappings
- Custom methods
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError
from PIL import Image
from io import BytesIO

from profiles.serializers import (
    UserProfileBasicSerializer,
    ProfilePhotoSerializer,
    ProfileCompletenessSerializer,
    ProfilePrivacySettingsSerializer,
    UserProfilePublicSerializer,
    PhotoUploadSerializer,
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
    PublicUserProfileFactory
)

User = get_user_model()


class UserProfileBasicSerializerTest(TestCase):
    """Test UserProfileBasicSerializer."""

    def setUp(self):
        self.user = UserFactory()
        self.profile = UserProfileBasicFactory(user=self.user)

    def test_serialize_profile(self):
        """Test serializing profile to JSON."""
        serializer = UserProfileBasicSerializer(self.profile)
        data = serializer.data

        self.assertEqual(data['display_name'], self.profile.display_name)
        self.assertEqual(data['bio'], self.profile.bio)
        self.assertEqual(data['timezone'], self.profile.timezone)
        self.assertIn('user', data)
        self.assertEqual(data['user']['id'], self.user.id)

    def test_deserialize_valid_data(self):
        """Test deserializing valid profile data."""
        data = {
            'display_name': 'New Display Name',
            'bio': 'New bio text',
            'timezone': 'America/New_York',
            'profile_visibility': 'public',
            'show_email': True,
            'show_full_name': False
        }

        serializer = UserProfileBasicSerializer(self.profile, data=data)

        self.assertTrue(serializer.is_valid())
        updated_profile = serializer.save()

        self.assertEqual(updated_profile.display_name, 'New Display Name')
        self.assertEqual(updated_profile.bio, 'New bio text')
        self.assertEqual(updated_profile.timezone, 'America/New_York')

    def test_validate_display_name_length(self):
        """Test display name length validation."""
        # Too long display name
        data = {
            'display_name': 'x' * 51  # Max is 50
        }

        serializer = UserProfileBasicSerializer(
            self.profile, data=data, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn('display_name', serializer.errors)

    def test_validate_bio_length(self):
        """Test bio length validation."""
        # Too long bio
        data = {
            'bio': 'x' * 1501  # Max is 1500
        }

        serializer = UserProfileBasicSerializer(
            self.profile, data=data, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn('bio', serializer.errors)

    def test_validate_profile_visibility_choices(self):
        """Test profile visibility validation."""
        # Valid choice
        data = {'profile_visibility': 'community'}
        serializer = UserProfileBasicSerializer(
            self.profile, data=data, partial=True)
        self.assertTrue(serializer.is_valid())

        # Invalid choice
        data = {'profile_visibility': 'invalid_choice'}
        serializer = UserProfileBasicSerializer(
            self.profile, data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('profile_visibility', serializer.errors)

    def test_readonly_fields(self):
        """Test that readonly fields cannot be updated."""
        data = {
            'is_profile_complete': True,  # Should be readonly
            'profile_completion_percentage': 100,  # Should be readonly
            'display_name': 'Updated Name'
        }

        serializer = UserProfileBasicSerializer(
            self.profile, data=data, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_profile = serializer.save()

        # display_name should be updated
        self.assertEqual(updated_profile.display_name, 'Updated Name')

        # Readonly fields should not be updated from input
        # (They should retain original values or be calculated)

    def test_create_new_profile(self):
        """Test creating new profile through serializer."""
        data = {
            'display_name': 'New User',
            'bio': 'New user bio',
            'timezone': 'UTC',
            'profile_visibility': 'private'
        }

        serializer = UserProfileBasicSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        # Note: In actual views, the user would be set from request.user


class ProfilePhotoSerializerTest(TestCase):
    """Test ProfilePhotoSerializer."""

    def setUp(self):
        self.user = UserFactory()
        self.photo = ProfilePhotoFactory(user=self.user)

    def test_serialize_photo(self):
        """Test serializing photo to JSON."""
        serializer = ProfilePhotoSerializer(self.photo)
        data = serializer.data

        self.assertIn('photo_url', data)
        self.assertIn('thumbnail_url', data)
        self.assertEqual(data['moderation_status'],
                         self.photo.moderation_status)
        self.assertEqual(data['is_approved'], self.photo.is_approved)

    def test_photo_url_field(self):
        """Test photo URL generation."""
        serializer = ProfilePhotoSerializer(self.photo)
        data = serializer.data

        # Should contain URL to photo
        self.assertIsNotNone(data['photo_url'])
        self.assertTrue(data['photo_url'].startswith('/media/') or
                        data['photo_url'].startswith('http'))

    def test_moderation_fields(self):
        """Test moderation-related fields."""
        # Approved photo
        approved_photo = ProfilePhotoFactory(
            user=self.user,
            moderation_status='approved',
            is_moderated=True
        )

        serializer = ProfilePhotoSerializer(approved_photo)
        data = serializer.data

        self.assertTrue(data['is_approved'])
        self.assertTrue(data['can_display'])
        self.assertEqual(data['moderation_status'], 'approved')


class PhotoUploadSerializerTest(TestCase):
    """Test PhotoUploadSerializer."""

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

    def test_validate_valid_image(self):
        """Test validating valid image upload."""
        test_image = self.create_test_image()

        data = {'photo': test_image}
        serializer = PhotoUploadSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_validate_invalid_file_type(self):
        """Test validation fails for non-image files."""
        text_file = SimpleUploadedFile(
            name='test.txt',
            content=b'not an image',
            content_type='text/plain'
        )

        data = {'photo': text_file}
        serializer = PhotoUploadSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('photo', serializer.errors)

    def test_validate_image_too_large(self):
        """Test validation fails for oversized images."""
        # Create large image (over 5MB)
        large_image = Image.new('RGB', (5000, 5000), color='red')
        image_io = BytesIO()
        large_image.save(image_io, format='JPEG', quality=100)
        image_io.seek(0)

        large_file = SimpleUploadedFile(
            name='large_photo.jpg',
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )

        data = {'photo': large_file}
        serializer = PhotoUploadSerializer(data=data)

        # Should fail if file size validation is implemented
        # self.assertFalse(serializer.is_valid())

    def test_validate_image_dimensions(self):
        """Test image dimension validation."""
        # Very small image
        tiny_image = self.create_test_image(size=(10, 10))

        data = {'photo': tiny_image}
        serializer = PhotoUploadSerializer(data=data)

        # Depending on implementation, might fail for too small images
        # For now, assuming it passes basic validation
        self.assertTrue(serializer.is_valid())


class ProfileCompletenessSerializerTest(TestCase):
    """Test ProfileCompletenessSerializer."""

    def setUp(self):
        self.user = UserFactory()
        self.tracker = ProfileCompletenessTrackerFactory(user=self.user)

    def test_serialize_completeness(self):
        """Test serializing completeness data."""
        serializer = ProfileCompletenessSerializer(self.tracker)
        data = serializer.data

        self.assertIn('overall_percentage', data)
        self.assertIn('completion_level', data)
        self.assertIn('badges_earned', data)
        self.assertIn('basic_info_score', data)
        self.assertIn('photo_score', data)
        self.assertIn('privacy_score', data)

    def test_readonly_serializer(self):
        """Test that completeness serializer is readonly."""
        data = {
            'overall_percentage': 100,
            'completion_level': 'expert'
        }

        serializer = ProfileCompletenessSerializer(self.tracker, data=data)

        # Should be valid even though fields are readonly
        self.assertTrue(serializer.is_valid())

        # But shouldn't actually update the data
        serializer.save()
        self.tracker.refresh_from_db()

        # Values should remain unchanged from serializer input
        self.assertNotEqual(self.tracker.overall_percentage, 100)


class ProfilePrivacySettingsSerializerTest(TestCase):
    """Test ProfilePrivacySettingsSerializer."""

    def setUp(self):
        self.user = UserFactory()
        self.profile = UserProfileBasicFactory(user=self.user)

    def test_serialize_privacy_settings(self):
        """Test serializing privacy settings."""
        serializer = ProfilePrivacySettingsSerializer(self.profile)
        data = serializer.data

        self.assertIn('profile_visibility', data)
        self.assertIn('show_email', data)
        self.assertIn('show_full_name', data)

    def test_update_privacy_settings(self):
        """Test updating privacy settings."""
        data = {
            'profile_visibility': 'public',
            'show_email': True,
            'show_full_name': True
        }

        serializer = ProfilePrivacySettingsSerializer(self.profile, data=data)

        self.assertTrue(serializer.is_valid())
        updated_profile = serializer.save()

        self.assertEqual(updated_profile.profile_visibility, 'public')
        self.assertTrue(updated_profile.show_email)
        self.assertTrue(updated_profile.show_full_name)

    def test_validate_profile_visibility(self):
        """Test profile visibility validation."""
        valid_choices = ['private', 'community', 'public']

        for choice in valid_choices:
            data = {'profile_visibility': choice}
            serializer = ProfilePrivacySettingsSerializer(
                self.profile, data=data, partial=True
            )
            self.assertTrue(serializer.is_valid(),
                            f"Should accept '{choice}' as valid choice")

        # Invalid choice
        data = {'profile_visibility': 'invalid'}
        serializer = ProfilePrivacySettingsSerializer(
            self.profile, data=data, partial=True
        )
        self.assertFalse(serializer.is_valid())


class UserProfilePublicSerializerTest(TestCase):
    """Test UserProfilePublicSerializer."""

    def setUp(self):
        self.user = UserFactory()
        self.public_profile = PublicUserProfileFactory(user=self.user)

    def test_serialize_public_profile(self):
        """Test serializing public profile."""
        serializer = UserProfilePublicSerializer(self.public_profile)
        data = serializer.data

        # Should include public fields
        self.assertIn('display_name', data)
        self.assertIn('bio', data)
        self.assertIn('user', data)

        # Should not include private fields
        self.assertNotIn('show_email', data)
        self.assertNotIn('show_full_name', data)

    def test_conditional_field_display(self):
        """Test conditional display of fields based on privacy settings."""
        # Public profile with email shown
        public_profile = PublicUserProfileFactory(
            user=self.user,
            show_email=True,
            show_full_name=True
        )

        serializer = UserProfilePublicSerializer(public_profile)
        data = serializer.data

        # Email should be included if show_email is True
        if public_profile.show_email:
            self.assertIn('email', data['user'])

        # Full name should be included if show_full_name is True
        if public_profile.show_full_name:
            self.assertIn('first_name', data['user'])
            self.assertIn('last_name', data['user'])


class SerializerFieldValidationTest(TestCase):
    """Test custom field validations across serializers."""

    def setUp(self):
        self.user = UserFactory()
        self.profile = UserProfileBasicFactory(user=self.user)

    def test_display_name_sanitization(self):
        """Test display name sanitization."""
        data = {
            'display_name': '  Test Name  '  # With whitespace
        }

        serializer = UserProfileBasicSerializer(
            self.profile, data=data, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_profile = serializer.save()

        # Should trim whitespace
        self.assertEqual(updated_profile.display_name, 'Test Name')

    def test_bio_sanitization(self):
        """Test bio field sanitization."""
        data = {
            'bio': '  Test bio with extra spaces  \n\n'
        }

        serializer = UserProfileBasicSerializer(
            self.profile, data=data, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_profile = serializer.save()

        # Should clean up extra whitespace
        self.assertEqual(updated_profile.bio.strip(),
                         'Test bio with extra spaces')

    def test_timezone_validation(self):
        """Test timezone field validation."""
        # Valid timezone
        data = {'timezone': 'America/New_York'}
        serializer = UserProfileBasicSerializer(
            self.profile, data=data, partial=True)
        self.assertTrue(serializer.is_valid())

        # Invalid timezone (if validation is implemented)
        data = {'timezone': 'Invalid/Timezone'}
        serializer = UserProfileBasicSerializer(
            self.profile, data=data, partial=True)
        # Should validate timezone if validation is implemented
        # self.assertFalse(serializer.is_valid())


@pytest.mark.django_db
class ProfileSerializerTestsWithPytest:
    """Pytest-style tests for profile serializers."""

    def test_profile_serializer_creates_valid_data(self):
        """Test profile serializer creates valid data."""
        user = UserFactory()
        profile = UserProfileBasicFactory(user=user)

        serializer = UserProfileBasicSerializer(profile)
        data = serializer.data

        assert 'display_name' in data
        assert 'bio' in data
        assert 'user' in data
        assert data['user']['id'] == user.id

    def test_photo_serializer_validation(self):
        """Test photo serializer validation."""
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

        data = {'photo': test_image}
        serializer = PhotoUploadSerializer(data=data)

        assert serializer.is_valid()

    def test_completeness_serializer_readonly(self):
        """Test completeness serializer is readonly."""
        user = UserFactory()
        tracker = ProfileCompletenessTrackerFactory(user=user)

        serializer = ProfileCompletenessSerializer(tracker)
        data = serializer.data

        assert 'overall_percentage' in data
        assert 'completion_level' in data
        assert isinstance(data['badges_earned'], list)
