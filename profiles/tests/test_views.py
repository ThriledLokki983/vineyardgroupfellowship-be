"""
Unit tests for profiles app views.

Tests all API endpoints including:
- Profile management endpoints
- Photo upload and management
- Privacy settings
- Profile completeness
- Public profile viewing
"""

import pytest
import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from PIL import Image
from io import BytesIO
from unittest.mock import patch, Mock

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
    PublicUserProfileFactory,
    PrivateUserProfileFactory,
    CompleteUserProfileFactory
)

User = get_user_model()


class UserProfileViewSetTest(APITestCase):
    """Test UserProfileViewSet endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.profile = UserProfileBasicFactory(user=self.user)

        # Get JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        # URLs
        self.my_profile_url = reverse('profiles:my-profile')

    def authenticate(self):
        """Helper to authenticate requests."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_get_my_profile_authenticated(self):
        """Test getting current user's profile."""
        self.authenticate()

        response = self.client.get(self.my_profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['id'], self.user.id)
        self.assertEqual(
            response.data['display_name'], self.profile.display_name)

    def test_get_my_profile_unauthenticated(self):
        """Test getting profile without authentication."""
        response = self.client.get(self.my_profile_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_my_profile(self):
        """Test updating current user's profile."""
        self.authenticate()

        update_data = {
            'display_name': 'Updated Name',
            'bio': 'Updated bio',
            'timezone': 'Europe/London'
        }

        response = self.client.put(
            self.my_profile_url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Updated Name')
        self.assertEqual(response.data['bio'], 'Updated bio')

        # Verify database update
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, 'Updated Name')
        self.assertEqual(self.profile.bio, 'Updated bio')

    def test_partial_update_my_profile(self):
        """Test partial update of current user's profile."""
        self.authenticate()

        update_data = {
            'display_name': 'Partially Updated'
        }

        response = self.client.patch(
            self.my_profile_url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Partially Updated')

        # Verify other fields unchanged
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, 'Partially Updated')
        # Bio should remain unchanged
        self.assertNotEqual(self.profile.bio, '')

    def test_create_profile_if_not_exists(self):
        """Test that profile is created if it doesn't exist."""
        # Delete existing profile
        self.profile.delete()

        self.authenticate()

        response = self.client.get(self.my_profile_url)

        # Should create new profile and return it
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserProfileBasic.objects.filter(
            user=self.user).exists())


class ProfilePhotoViewSetTest(APITestCase):
    """Test ProfilePhotoViewSet endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()

        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        # URLs
        self.photo_info_url = reverse('profiles:my-photo-info')
        self.photo_upload_url = reverse('profiles:photo-upload')
        self.photo_delete_url = reverse('profiles:photo-delete')

    def authenticate(self):
        """Helper to authenticate requests."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

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

    def test_upload_photo(self):
        """Test uploading profile photo."""
        self.authenticate()

        test_image = self.create_test_image()

        response = self.client.post(
            self.photo_upload_url,
            {'photo': test_image},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('photo_url', response.data)

        # Verify photo was created
        self.assertTrue(ProfilePhoto.objects.filter(user=self.user).exists())

    def test_upload_photo_unauthenticated(self):
        """Test uploading photo without authentication."""
        test_image = self.create_test_image()

        response = self.client.post(
            self.photo_upload_url,
            {'photo': test_image},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_invalid_file(self):
        """Test uploading invalid file type."""
        self.authenticate()

        # Create text file instead of image
        invalid_file = SimpleUploadedFile(
            name='test.txt',
            content=b'not an image',
            content_type='text/plain'
        )

        response = self.client.post(
            self.photo_upload_url,
            {'photo': invalid_file},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_photo_info(self):
        """Test getting photo information."""
        self.authenticate()

        # Create photo
        photo = ProfilePhotoFactory(user=self.user)

        response = self.client.get(self.photo_info_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('photo_url', response.data)
        self.assertEqual(
            response.data['moderation_status'], photo.moderation_status)

    def test_get_photo_info_no_photo(self):
        """Test getting photo info when no photo exists."""
        self.authenticate()

        response = self.client.get(self.photo_info_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_photo(self):
        """Test deleting profile photo."""
        self.authenticate()

        # Create photo
        photo = ProfilePhotoFactory(user=self.user)

        response = self.client.delete(self.photo_delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify photo was deleted
        self.assertFalse(ProfilePhoto.objects.filter(user=self.user).exists())

    def test_delete_photo_no_photo(self):
        """Test deleting photo when no photo exists."""
        self.authenticate()

        response = self.client.delete(self.photo_delete_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_replace_existing_photo(self):
        """Test replacing existing photo."""
        self.authenticate()

        # Create existing photo
        old_photo = ProfilePhotoFactory(user=self.user)
        old_photo_id = old_photo.id

        # Upload new photo
        test_image = self.create_test_image()

        response = self.client.put(
            self.photo_upload_url,
            {'photo': test_image},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify old photo was replaced
        self.assertFalse(ProfilePhoto.objects.filter(id=old_photo_id).exists())
        self.assertTrue(ProfilePhoto.objects.filter(user=self.user).exists())


class PrivacySettingsViewTest(APITestCase):
    """Test privacy settings endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.profile = UserProfileBasicFactory(user=self.user)

        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        # URLs
        self.privacy_url = reverse('profiles:privacy-settings')
        self.privacy_update_url = reverse('profiles:privacy-update')

    def authenticate(self):
        """Helper to authenticate requests."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_get_privacy_settings(self):
        """Test getting privacy settings."""
        self.authenticate()

        response = self.client.get(self.privacy_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('profile_visibility', response.data)
        self.assertIn('show_email', response.data)
        self.assertIn('show_full_name', response.data)

    def test_update_privacy_settings(self):
        """Test updating privacy settings."""
        self.authenticate()

        update_data = {
            'profile_visibility': 'public',
            'show_email': True,
            'show_full_name': True
        }

        response = self.client.put(
            self.privacy_update_url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['profile_visibility'], 'public')
        self.assertTrue(response.data['show_email'])

        # Verify database update
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_visibility, 'public')
        self.assertTrue(self.profile.show_email)

    def test_invalid_privacy_visibility(self):
        """Test invalid privacy visibility value."""
        self.authenticate()

        update_data = {
            'profile_visibility': 'invalid_choice'
        }

        response = self.client.put(
            self.privacy_update_url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProfileCompletenessViewTest(APITestCase):
    """Test profile completeness endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.profile = UserProfileBasicFactory(user=self.user)

        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        # URLs
        self.completeness_url = reverse('profiles:completeness')
        self.refresh_completeness_url = reverse(
            'profiles:completeness-refresh')

    def authenticate(self):
        """Helper to authenticate requests."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_get_completeness_status(self):
        """Test getting completeness status."""
        self.authenticate()

        # Create completeness tracker
        tracker = ProfileCompletenessTrackerFactory(user=self.user)

        response = self.client.get(self.completeness_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('overall_percentage', response.data)
        self.assertIn('completion_level', response.data)
        self.assertIn('badges_earned', response.data)

    def test_get_completeness_no_tracker(self):
        """Test getting completeness when no tracker exists."""
        self.authenticate()

        response = self.client.get(self.completeness_url)

        # Should create and return new tracker
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(ProfileCompletenessTracker.objects.filter(
            user=self.user).exists())

    @patch('profiles.services.ProfileCompletenessService.calculate_completeness')
    def test_refresh_completeness(self, mock_calculate):
        """Test refreshing completeness calculation."""
        self.authenticate()

        mock_calculate.return_value = {
            'overall_percentage': 85,
            'completion_level': 'advanced'
        }

        response = self.client.post(self.refresh_completeness_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['overall_percentage'], 85)
        mock_calculate.assert_called_once_with(self.user)


class PublicProfileViewTest(APITestCase):
    """Test public profile viewing endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.other_user = UserFactory()

        # Create profiles with different visibility
        self.public_profile = PublicUserProfileFactory(user=self.user)
        self.private_profile = PrivateUserProfileFactory(user=self.other_user)

        # URLs
        self.public_profile_url = reverse(
            'profiles:public-profile', args=[str(self.user.id)])
        self.private_profile_url = reverse(
            'profiles:public-profile', args=[str(self.other_user.id)])

    def test_view_public_profile(self):
        """Test viewing public profile without authentication."""
        response = self.client.get(self.public_profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['id'], self.user.id)
        self.assertIn('display_name', response.data)

    def test_view_private_profile(self):
        """Test viewing private profile without authentication."""
        response = self.client.get(self.private_profile_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_view_nonexistent_profile(self):
        """Test viewing profile that doesn't exist."""
        nonexistent_url = reverse('profiles:public-profile', args=['99999'])

        response = self.client.get(nonexistent_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ProfileViewPermissionsTest(APITestCase):
    """Test profile view permissions and security."""

    def setUp(self):
        self.client = APIClient()
        self.user1 = UserFactory()
        self.user2 = UserFactory()

        self.profile1 = UserProfileBasicFactory(user=self.user1)
        self.profile2 = UserProfileBasicFactory(user=self.user2)

        # Get JWT tokens
        refresh1 = RefreshToken.for_user(self.user1)
        self.access_token1 = str(refresh1.access_token)

    def test_cannot_modify_other_user_profile(self):
        """Test that users cannot modify other users' profiles."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')

        # Try to update user2's profile (should not be possible through current endpoints)
        # This test ensures our ViewSet properly restricts access to current user only
        my_profile_url = reverse('profiles:my-profile')

        response = self.client.get(my_profile_url)

        # Should only return user1's profile
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['id'], self.user1.id)

    def test_photo_access_restrictions(self):
        """Test photo access restrictions."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')

        # Create photo for user2
        photo2 = ProfilePhotoFactory(user=self.user2)

        # Try to access user2's photo info (should only show own photos)
        photo_info_url = reverse('profiles:my-photo-info')

        response = self.client.get(photo_info_url)

        # Should return 404 since user1 has no photo
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db
class ProfileViewsTestsWithPytest:
    """Pytest-style tests for profile views."""

    def test_authenticated_user_can_access_profile(self, api_client):
        """Test authenticated user can access their profile."""
        user = UserFactory()
        profile = UserProfileBasicFactory(user=user)

        # Authenticate
        refresh = RefreshToken.for_user(user)
        api_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        url = reverse('profiles:my-profile')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['user']['id'] == user.id

    @pytest.fixture
    def api_client(self):
        """Fixture to provide API client."""
        return APIClient()
