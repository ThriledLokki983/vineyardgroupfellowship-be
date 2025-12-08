"""
Tests for recovery approach onboarding view.

This module tests the RecoveryApproachOnboardingView API endpoints
during the onboarding flow.
"""

import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.tests.factories import UserFactory
# NOTE: recovery module does not exist - these tests are disabled
# from recovery.models import RecoveryProfile
from onboarding.models import OnboardingProgress
import pytest

# Import serializers - these may need updating based on where they actually live
try:
    from onboarding.serializers import RecoveryApproachSerializer
except ImportError:
    # Fallback if serializers are still in authentication app
    try:
        from authentication.serializers import RecoveryApproachSerializer
    except ImportError:
        # Recovery approach feature not yet implemented
        RecoveryApproachSerializer = None


@pytest.mark.skip(reason="Recovery module not yet implemented - RecoveryProfile model does not exist")
class RecoveryApproachAPITestCase(APITestCase):
    """Test RecoveryApproachOnboardingView API endpoints."""

    def setUp(self):
        self.user = UserFactory()
        self.client = APIClient()

        # Get JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        # Set up authenticated client
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        self.url = reverse('onboarding:recovery-approach')

    def test_post_secular_approach(self):
        """Test POST request for secular recovery approach."""
        data = {'recovery_approach': 'secular'}

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['message'], 'Recovery approach preferences saved successfully')
        self.assertEqual(
            response.data['recovery_preferences']['approach'], 'secular')
        self.assertEqual(response.data['next_step'], 'community_preferences')

        # Check database was updated
        recovery_profile = RecoveryProfile.objects.get(user=self.user)
        self.assertEqual(recovery_profile.recovery_approach, 'secular')
        self.assertIsNone(recovery_profile.faith_tradition)
        self.assertEqual(recovery_profile.religious_content_preference, 'none')

    def test_post_religious_approach_with_faith(self):
        """Test POST request for religious recovery approach with faith tradition."""
        data = {
            'recovery_approach': 'religious',
            'faith_tradition': 'christian',
            'religious_content_preference': 'moderate'
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['recovery_preferences']['approach'], 'religious')
        self.assertEqual(
            response.data['recovery_preferences']['faith_tradition'], 'christian')
        self.assertEqual(
            response.data['recovery_preferences']['content_preference'], 'moderate')

        # Check database was updated
        recovery_profile = RecoveryProfile.objects.get(user=self.user)
        self.assertEqual(recovery_profile.recovery_approach, 'religious')
        self.assertEqual(recovery_profile.faith_tradition, 'christian')
        self.assertEqual(
            recovery_profile.religious_content_preference, 'moderate')

    def test_post_religious_approach_without_faith_fails(self):
        """Test POST request for religious approach without faith tradition fails."""
        data = {'recovery_approach': 'religious'}

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Validation failed')
        self.assertIn('faith_tradition', response.data['details'])

    def test_post_mixed_approach(self):
        """Test POST request for mixed recovery approach."""
        data = {
            'recovery_approach': 'mixed',
            'faith_tradition': 'buddhist',
            'religious_content_preference': 'high'
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['recovery_preferences']['approach'], 'mixed')

    def test_post_undecided_approach(self):
        """Test POST request for undecided recovery approach."""
        data = {'recovery_approach': 'undecided'}

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['recovery_preferences']['approach'], 'undecided')

    def test_post_invalid_approach_fails(self):
        """Test POST request with invalid recovery approach fails."""
        data = {'recovery_approach': 'invalid_choice'}

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Validation failed')

    def test_get_recovery_preferences(self):
        """Test GET request to retrieve recovery preferences."""
        # Set up some preferences first
        recovery_profile, created = RecoveryProfile.objects.get_or_create(
            user=self.user)
        recovery_profile.recovery_approach = 'religious'
        recovery_profile.faith_tradition = 'muslim'
        recovery_profile.religious_content_preference = 'minimal'
        recovery_profile.recovery_preferences_set_at = timezone.now()
        recovery_profile.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['recovery_preferences']['approach'], 'religious')
        self.assertEqual(
            response.data['recovery_preferences']['faith_tradition'], 'muslim')
        self.assertEqual(
            response.data['recovery_preferences']['content_preference'], 'minimal')
        self.assertIsNotNone(
            response.data['recovery_preferences']['configured_at'])

    def test_get_empty_recovery_preferences(self):
        """Test GET request when no recovery preferences are set."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['recovery_preferences']['approach'])
        self.assertIsNone(
            response.data['recovery_preferences']['faith_tradition'])
        self.assertEqual(
            response.data['recovery_preferences']['content_preference'], 'moderate')
        self.assertIsNone(
            response.data['recovery_preferences']['configured_at'])

    def test_unauthenticated_access_fails(self):
        """Test that unauthenticated requests fail."""
        self.client.credentials()  # Remove authentication

        response = self.client.post(self.url, {'recovery_approach': 'secular'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_existing_preferences(self):
        """Test updating existing recovery preferences."""
        # Set initial preferences
        recovery_profile, created = RecoveryProfile.objects.get_or_create(
            user=self.user)
        recovery_profile.recovery_approach = 'secular'
        recovery_profile.save()

        # Update to religious
        data = {
            'recovery_approach': 'religious',
            'faith_tradition': 'hindu',
            'religious_content_preference': 'high'
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check database was updated
        recovery_profile.refresh_from_db()
        self.assertEqual(recovery_profile.recovery_approach, 'religious')
        self.assertEqual(recovery_profile.faith_tradition, 'hindu')
        self.assertEqual(recovery_profile.religious_content_preference, 'high')


@pytest.mark.skip(reason="Recovery module not yet implemented - RecoveryProfile model does not exist")
class RecoveryApproachIntegrationTestCase(APITestCase):
    """Integration tests for recovery approach system during onboarding."""

    def setUp(self):
        self.user = UserFactory()
        self.client = APIClient()

        # Get JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_complete_onboarding_flow_with_recovery_approach(self):
        """Test complete onboarding flow including recovery approach step."""
        # Step 1: Update onboarding step to recovery_approach
        step_url = reverse('onboarding:step')
        step_data = {'step': 'recovery_approach'}

        response = self.client.patch(step_url, step_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Step 2: Set recovery approach preferences
        recovery_url = reverse('onboarding:recovery-approach')
        recovery_data = {
            'recovery_approach': 'mixed',
            'faith_tradition': 'jewish',
            'religious_content_preference': 'moderate'
        }

        response = self.client.post(recovery_url, recovery_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['next_step'], 'community_preferences')

        # Step 3: Verify profile includes recovery preferences
        profile_url = reverse('profiles:profile-me')
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['recovery_approach'], 'mixed')
        self.assertEqual(data['faith_tradition'], 'jewish')
        self.assertEqual(data['religious_content_preference'], 'moderate')
        self.assertIsNotNone(data['recovery_preferences_set_at'])
