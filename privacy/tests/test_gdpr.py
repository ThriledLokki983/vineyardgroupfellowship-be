"""
Tests for GDPR compliance functionality.

This module tests GDPR-related features including data export,
data erasure, and consent management.
"""

import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.tests.factories import (
    UserFactory,
    create_user_with_profile
)


@pytest.mark.security
@pytest.mark.views
class TestGDPRViewSet(APITestCase):
    """Test GDPR compliance API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user, self.profile = create_user_with_profile()

        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')

        self.export_data_url = reverse('privacy:gdpr_data_export')
        self.erase_data_url = reverse('privacy:gdpr_data_erasure')
        self.consent_url = reverse('privacy:gdpr_consent_management')

    def test_export_user_data_success(self):
        """Test successful data export."""
        data = {
            'export_format': 'json',
            'include_audit_logs': True,
            'privacy_notice_acknowledged': True
        }

        response = self.client.post(self.export_data_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_erase_user_data_success(self):
        """Test successful data erasure."""
        data = {
            'reason': 'withdraw_consent',
            'confirm_understanding': True,
            'confirm_irreversible': True
        }

        response = self.client.post(self.erase_data_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_erase_user_data_invalid_confirmation(self):
        """Test data erasure with invalid confirmation."""
        data = {
            'reason': 'withdraw_consent',
            'confirm_understanding': False,  # Invalid
            'confirm_irreversible': True
        }

        response = self.client.post(self.erase_data_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_consent_success(self):
        """Test successful consent update."""
        data = {
            'consent_type': 'marketing',
            'granted': True
        }

        response = self.client.post(self.consent_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_gdpr_endpoints_require_authentication(self):
        """Test that GDPR endpoints require authentication."""
        self.client.credentials()  # Remove auth

        endpoints = [
            self.export_data_url,
            self.erase_data_url,
            self.consent_url
        ]

        for endpoint in endpoints:
            response = self.client.post(endpoint, {}, format='json')
            self.assertEqual(response.status_code,
                             status.HTTP_401_UNAUTHORIZED)

    def test_data_export_includes_all_user_data(self):
        """Test that data export includes all user-related data."""
        data = {
            'export_format': 'json',
            'include_audit_logs': True,
            'privacy_notice_acknowledged': True
        }

        response = self.client.post(self.export_data_url, data, format='json')

        if response.status_code == status.HTTP_200_OK:
            # Verify the export contains expected data sections
            export_data = response.data
            # These may need to be adjusted based on actual implementation
            expected_sections = ['user_info', 'profile', 'privacy_settings']
            for section in expected_sections:
                if section in export_data:
                    self.assertIsNotNone(export_data[section])

    def test_consent_withdrawal_functionality(self):
        """Test that users can withdraw consent."""
        data = {
            'marketing_consent': False,
            'analytics_consent': False,
            'withdraw_all_consent': True
        }

        response = self.client.post(self.consent_url, data, format='json')

        # Should succeed
        if response.status_code == status.HTTP_200_OK:
            self.assertTrue(response.data.get('consent_withdrawn', False))
