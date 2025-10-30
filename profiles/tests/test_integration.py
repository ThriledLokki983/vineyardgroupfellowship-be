"""
Integration tests for profiles app.

Tests end-to-end workflows and cross-service interactions including:
- Complete user profile creation workflows
- Photo upload and moderation workflows
- Privacy setting changes and access control
- Profile completeness tracking and recommendations
- GDPR compliance workflows
- API integration scenarios
"""

import pytest
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, Mock
from PIL import Image
from io import BytesIO

from profiles.models import (
    UserProfileBasic,
    ProfilePhoto,
    ProfileCompletenessTracker
)
from profiles.services import (
    ProfileService,
    PhotoService,
    ProfileCompletenessService,
    PrivacyService
)
from .factories import (
    UserFactory,
    UserProfileBasicFactory,
    ProfilePhotoFactory,
    CompleteUserProfileFactory
)

User = get_user_model()


class ProfileCreationWorkflowTest(APITestCase):
    """Test complete profile creation workflow."""

    def setUp(self):
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_complete_profile_creation_workflow(self):
        """Test end-to-end profile creation workflow."""
        # Step 1: Get initial profile (should be created automatically)
        response = self.client.get(reverse('profiles:profile-detail'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile_data = response.data

        # Should have minimal data initially
        self.assertEqual(profile_data['display_name'], '')
        self.assertEqual(profile_data['bio'], '')
        self.assertIsNone(profile_data['photo'])

        # Step 2: Update basic profile information
        update_data = {
            'display_name': 'Integration Test User',
            'bio': 'This is my test bio for integration testing.',
            'timezone': 'America/New_York'
        }

        response = self.client.patch(
            reverse('profiles:profile-detail'),
            data=update_data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['display_name'], 'Integration Test User')

        # Step 3: Upload profile photo
        image = Image.new('RGB', (300, 300), color='blue')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)

        photo_file = SimpleUploadedFile(
            name='integration_test.jpg',
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )

        with patch('profiles.services.PhotoService._process_photo') as mock_process:
            mock_process.return_value = (photo_file, photo_file)

            response = self.client.post(
                reverse('profiles:photo-upload'),
                data={'photo': photo_file},
                format='multipart'
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Step 4: Check completeness has updated
        response = self.client.get(reverse('profiles:profile-completeness'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        completeness = response.data

        # Should have higher completeness now
        self.assertGreater(completeness['overall_percentage'], 50)
        self.assertTrue(completeness['has_display_name'])
        self.assertTrue(completeness['has_bio'])
        self.assertTrue(completeness['has_photo'])

        # Step 5: Verify profile is accessible
        response = self.client.get(reverse('profiles:profile-detail'))

        final_profile = response.data
        self.assertEqual(
            final_profile['display_name'], 'Integration Test User')
        self.assertIsNotNone(final_profile['photo'])

    def test_profile_privacy_workflow(self):
        """Test privacy settings workflow."""
        # Create profile
        profile = UserProfileBasicFactory(
            user=self.user,
            profile_visibility='public'
        )

        # Step 1: Verify profile is publicly visible
        other_user = UserFactory()
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)

        response = other_client.get(
            reverse('profiles:public-profile',
                    kwargs={'user_id': self.user.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Step 2: Change to private
        response = self.client.patch(
            reverse('profiles:privacy-settings'),
            data={'profile_visibility': 'private'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Step 3: Verify other user can no longer access
        response = other_client.get(
            reverse('profiles:public-profile',
                    kwargs={'user_id': self.user.id})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Step 4: User can still access own profile
        response = self.client.get(reverse('profiles:profile-detail'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PhotoModerationWorkflowTest(TransactionTestCase):
    """Test photo moderation workflow."""

    def setUp(self):
        self.user = UserFactory()
        self.moderator = UserFactory(is_staff=True)
        self.client = APIClient()

    def test_photo_moderation_workflow(self):
        """Test complete photo moderation workflow."""
        # Step 1: User uploads photo
        self.client.force_authenticate(user=self.user)

        image = Image.new('RGB', (300, 300), color='green')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)

        photo_file = SimpleUploadedFile(
            name='moderation_test.jpg',
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )

        with patch('profiles.services.PhotoService._process_photo') as mock_process:
            mock_process.return_value = (photo_file, photo_file)

            response = self.client.post(
                reverse('profiles:photo-upload'),
                data={'photo': photo_file},
                format='multipart'
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Photo should be pending moderation
        photo = ProfilePhoto.objects.get(user=self.user)
        self.assertEqual(photo.moderation_status, 'pending')
        self.assertFalse(photo.is_moderated)

        # Step 2: Moderator approves photo
        self.client.force_authenticate(user=self.moderator)

        response = self.client.patch(
            reverse('profiles:photo-moderate', kwargs={'photo_id': photo.id}),
            data={
                'moderation_status': 'approved',
                'moderation_notes': 'Photo looks good'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify photo is approved
        photo.refresh_from_db()
        self.assertEqual(photo.moderation_status, 'approved')
        self.assertTrue(photo.is_moderated)

        # Step 3: Photo is now visible in public profile
        other_user = UserFactory()
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)

        response = other_client.get(
            reverse('profiles:public-profile',
                    kwargs={'user_id': self.user.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data.get('photo'))

    def test_photo_rejection_workflow(self):
        """Test photo rejection workflow."""
        # Upload photo
        photo = ProfilePhotoFactory(
            user=self.user,
            moderation_status='pending'
        )

        self.client.force_authenticate(user=self.moderator)

        # Reject photo
        response = self.client.patch(
            reverse('profiles:photo-moderate', kwargs={'photo_id': photo.id}),
            data={
                'moderation_status': 'rejected',
                'moderation_notes': 'Inappropriate content'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify photo is rejected
        photo.refresh_from_db()
        self.assertEqual(photo.moderation_status, 'rejected')

        # User should be notified (would trigger notification in real app)
        # Photo should not appear in public profile


class ProfileCompletenessTrackingWorkflowTest(TestCase):
    """Test profile completeness tracking workflow."""

    def setUp(self):
        self.user = UserFactory()

    def test_completeness_tracking_workflow(self):
        """Test complete profile completeness tracking."""
        # Step 1: Start with empty profile
        profile = UserProfileBasicFactory(
            user=self.user,
            display_name='',
            bio=''
        )

        # Initial completeness should be low
        completeness = ProfileCompletenessService.calculate_completeness(
            self.user)
        initial_percentage = completeness['overall_percentage']

        self.assertLess(initial_percentage, 30)
        self.assertEqual(completeness['completion_level'], 'beginner')

        # Step 2: Add display name
        ProfileService.update_profile(self.user, {'display_name': 'Test User'})

        completeness = ProfileCompletenessService.calculate_completeness(
            self.user)
        after_name_percentage = completeness['overall_percentage']

        self.assertGreater(after_name_percentage, initial_percentage)
        self.assertTrue(completeness['has_display_name'])

        # Step 3: Add bio
        ProfileService.update_profile(self.user, {'bio': 'This is my bio'})

        completeness = ProfileCompletenessService.calculate_completeness(
            self.user)
        after_bio_percentage = completeness['overall_percentage']

        self.assertGreater(after_bio_percentage, after_name_percentage)
        self.assertTrue(completeness['has_bio'])

        # Step 4: Add photo
        photo = ProfilePhotoFactory(
            user=self.user, moderation_status='approved')

        completeness = ProfileCompletenessService.calculate_completeness(
            self.user)
        final_percentage = completeness['overall_percentage']

        self.assertGreater(final_percentage, after_bio_percentage)
        self.assertTrue(completeness['has_photo'])
        self.assertIn(completeness['completion_level'], [
                      'intermediate', 'advanced'])

        # Step 5: Verify tracker was updated
        tracker = ProfileCompletenessTracker.objects.get(user=self.user)
        self.assertEqual(tracker.current_percentage, final_percentage)
        self.assertIsNotNone(tracker.last_calculated)

    def test_completion_recommendations_workflow(self):
        """Test completion recommendations workflow."""
        # Profile with only display name
        profile = UserProfileBasicFactory(
            user=self.user,
            display_name='Test User',
            bio=''
        )

        recommendations = ProfileCompletenessService.get_completion_recommendations(
            self.user)

        # Should recommend adding bio and photo
        self.assertIn('Add a bio', recommendations)
        self.assertIn('Upload a profile photo', recommendations)
        self.assertNotIn('Add a display name', recommendations)

        # Add bio
        ProfileService.update_profile(self.user, {'bio': 'My bio'})

        recommendations = ProfileCompletenessService.get_completion_recommendations(
            self.user)

        # Should no longer recommend bio
        self.assertNotIn('Add a bio', recommendations)
        self.assertIn('Upload a profile photo', recommendations)


class GDPRComplianceWorkflowTest(TestCase):
    """Test GDPR compliance workflows."""

    def setUp(self):
        self.user = UserFactory()

    def test_data_export_workflow(self):
        """Test complete data export workflow."""
        # Create complete profile with data
        profile = UserProfileBasicFactory(
            user=self.user,
            display_name='GDPR Test User',
            bio='Test bio for GDPR export'
        )
        photo = ProfilePhotoFactory(user=self.user)
        tracker = ProfileCompletenessTracker.objects.create(
            user=self.user,
            current_percentage=75
        )

        # Export user data
        export_data = ProfileService.export_user_profile_data(self.user)

        # Verify all data is included
        self.assertIn('user', export_data)
        self.assertIn('profile', export_data)
        self.assertIn('photos', export_data)
        self.assertIn('completeness_history', export_data)

        # Verify data integrity
        self.assertEqual(export_data['profile']
                         ['display_name'], 'GDPR Test User')
        self.assertEqual(len(export_data['photos']), 1)
        self.assertIsNotNone(export_data['completeness_history'])

        # Verify sensitive data handling
        user_data = export_data['user']
        self.assertIn('email', user_data)  # User should get their own email
        self.assertNotIn('password', user_data)  # Never export passwords

    def test_data_deletion_workflow(self):
        """Test complete data deletion workflow."""
        # Create profile with all data types
        profile = UserProfileBasicFactory(user=self.user)
        photo = ProfilePhotoFactory(user=self.user)
        tracker = ProfileCompletenessTracker.objects.create(user=self.user)

        # Record IDs before deletion
        profile_id = profile.id
        photo_id = photo.id
        tracker_id = tracker.id

        # Delete all profile data
        ProfileService.delete_user_profile_data(self.user)

        # Verify all data is deleted
        self.assertFalse(UserProfileBasic.objects.filter(
            id=profile_id).exists())
        self.assertFalse(ProfilePhoto.objects.filter(id=photo_id).exists())
        self.assertFalse(ProfileCompletenessTracker.objects.filter(
            id=tracker_id).exists())

        # User account should still exist (separate deletion process)
        self.assertTrue(User.objects.filter(id=self.user.id).exists())


class CrossServiceIntegrationTest(TestCase):
    """Test integration between different profile services."""

    def setUp(self):
        self.user = UserFactory()

    def test_profile_update_triggers_completeness_recalculation(self):
        """Test that profile updates trigger completeness recalculation."""
        profile = UserProfileBasicFactory(
            user=self.user,
            display_name='',
            bio=''
        )

        # Initial completeness
        initial_completeness = ProfileCompletenessService.calculate_completeness(
            self.user)
        initial_percentage = initial_completeness['overall_percentage']

        # Update profile
        with patch('profiles.services.ProfileCompletenessService.update_completeness_tracker') as mock_update:
            ProfileService.update_profile(self.user, {
                'display_name': 'New Name',
                'bio': 'New bio'
            })

            # Should trigger completeness update
            mock_update.assert_called_once_with(self.user)

        # Verify completeness actually changed
        new_completeness = ProfileCompletenessService.calculate_completeness(
            self.user)
        self.assertGreater(
            new_completeness['overall_percentage'], initial_percentage)

    def test_photo_upload_updates_completeness(self):
        """Test that photo upload updates completeness."""
        profile = UserProfileBasicFactory(user=self.user)

        # Initial completeness (no photo)
        initial_completeness = ProfileCompletenessService.calculate_completeness(
            self.user)
        self.assertFalse(initial_completeness['has_photo'])

        # Upload photo
        image = Image.new('RGB', (300, 300), color='red')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)

        photo_file = SimpleUploadedFile(
            name='test.jpg',
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )

        with patch('profiles.services.PhotoService._process_photo') as mock_process:
            mock_process.return_value = (photo_file, photo_file)
            PhotoService.upload_photo(self.user, photo_file)

        # Completeness should now include photo
        new_completeness = ProfileCompletenessService.calculate_completeness(
            self.user)
        self.assertTrue(new_completeness['has_photo'])
        self.assertGreater(new_completeness['overall_percentage'],
                           initial_completeness['overall_percentage'])

    def test_privacy_changes_affect_public_access(self):
        """Test that privacy changes immediately affect public access."""
        profile = UserProfileBasicFactory(
            user=self.user,
            profile_visibility='public'
        )
        other_user = UserFactory()

        # Initially accessible
        self.assertTrue(PrivacyService.can_view_profile(self.user, other_user))

        # Change to private
        PrivacyService.update_privacy_settings(self.user, {
            'profile_visibility': 'private'
        })

        # Should immediately be inaccessible
        self.assertFalse(
            PrivacyService.can_view_profile(self.user, other_user))

        # But still accessible to user themselves
        self.assertTrue(PrivacyService.can_view_profile(self.user, self.user))


@pytest.mark.django_db
class ProfileIntegrationTestsWithPytest:
    """Pytest-style integration tests."""

    def test_end_to_end_profile_creation(self):
        """Test complete profile creation with pytest."""
        user = UserFactory()

        # Create profile
        profile = ProfileService.get_or_create_profile(user)
        assert profile.user == user

        # Update profile
        updated_profile = ProfileService.update_profile(user, {
            'display_name': 'Pytest User',
            'bio': 'Created with pytest'
        })
        assert updated_profile.display_name == 'Pytest User'

        # Check completeness
        completeness = ProfileCompletenessService.calculate_completeness(user)
        assert completeness['has_display_name'] is True
        assert completeness['has_bio'] is True
        assert completeness['overall_percentage'] > 30

    def test_photo_and_privacy_integration(self):
        """Test photo upload with privacy settings."""
        user = UserFactory()
        other_user = UserFactory()

        # Create private profile
        profile = UserProfileBasicFactory(
            user=user,
            profile_visibility='private'
        )

        # Upload photo
        photo = ProfilePhotoFactory(user=user, moderation_status='approved')

        # Other user should not be able to access profile even with photo
        can_view = PrivacyService.can_view_profile(user, other_user)
        assert can_view is False

        # Change to public
        PrivacyService.update_privacy_settings(user, {
            'profile_visibility': 'public'
        })

        # Now other user should be able to access
        can_view = PrivacyService.can_view_profile(user, other_user)
        assert can_view is True
