"""
Test factories for privacy app.

Provides factory classes for creating consistent test data
for privacy-related models.
"""

from django.utils import timezone
import factory
from factory.django import DjangoModelFactory
from factory import Faker, SubFactory, LazyAttribute

from privacy.models import PrivacySettings


class PrivacySettingsFactory(DjangoModelFactory):
    """Factory for creating privacy settings."""

    class Meta:
        model = PrivacySettings

    user = SubFactory('authentication.tests.factories.UserFactory')

    # Profile visibility
    profile_visibility = factory.Iterator(
        ['public', 'community', 'supporters', 'private'])
    show_sobriety_date = False
    allow_direct_messages = True

    # Notification preferences
    email_notifications = True
    community_notifications = True
    emergency_notifications = True

    # Data processing consent
    analytics_consent = False
    marketing_consent = False
    research_participation_consent = False

    # Privacy policy and terms
    privacy_policy_version = '1.0'
    privacy_policy_accepted_at = factory.LazyFunction(lambda: timezone.now())
    terms_version = '1.0'
    terms_accepted_at = factory.LazyFunction(lambda: timezone.now())

    created_at = factory.LazyFunction(lambda: timezone.now())
    updated_at = factory.LazyFunction(lambda: timezone.now())


class PrivatePrivacySettingsFactory(PrivacySettingsFactory):
    """Factory for very private privacy settings."""

    profile_visibility = 'private'
    show_sobriety_date = False
    allow_direct_messages = False
    email_notifications = False
    community_notifications = False
    analytics_consent = False
    marketing_consent = False


class PublicPrivacySettingsFactory(PrivacySettingsFactory):
    """Factory for public privacy settings."""

    profile_visibility = 'public'
    show_sobriety_date = True
    allow_direct_messages = True
    email_notifications = True
    community_notifications = True
    analytics_consent = True
    marketing_consent = True
