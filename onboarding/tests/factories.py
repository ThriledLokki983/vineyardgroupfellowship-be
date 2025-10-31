"""
Test factories for onboarding app.

Provides factory classes for creating consistent test data
for onboarding-related models.
"""

from django.utils import timezone
import factory
from factory.django import DjangoModelFactory
from factory import Faker, SubFactory, LazyAttribute

from onboarding.models import OnboardingProgress, SupporterQualifications, OnboardingFeedback


class OnboardingProgressFactory(DjangoModelFactory):
    """Factory for creating onboarding progress records."""

    class Meta:
        model = OnboardingProgress

    user_profile = SubFactory(
        'authentication.tests.factories.UserProfileFactory')

    steps_completed = factory.LazyAttribute(lambda o: {})
    total_steps = 6
    completion_percentage = 0.0

    started_at = factory.LazyFunction(lambda: timezone.now())
    last_activity_at = factory.LazyFunction(lambda: timezone.now())
    time_spent_minutes = 0
    dropped_off_at_step = None


class CompletedOnboardingProgressFactory(OnboardingProgressFactory):
    """Factory for completed onboarding progress."""

    completion_percentage = 100.0
    total_steps = 6
    steps_completed = factory.LazyAttribute(lambda o: {
        'welcome': timezone.now().isoformat(),
        'user_purpose': timezone.now().isoformat(),
        'recovery_approach': timezone.now().isoformat(),
        'profile_setup': timezone.now().isoformat(),
        'privacy_settings': timezone.now().isoformat(),
        'completion': timezone.now().isoformat(),
    })


class SupporterQualificationsFactory(DjangoModelFactory):
    """Factory for creating supporter qualifications."""

    class Meta:
        model = SupporterQualifications

    user_profile = SubFactory(
        'authentication.tests.factories.UserProfileFactory')

    personal_recovery_story = Faker('text', max_nb_chars=500)
    addiction_types_experienced = factory.LazyAttribute(
        lambda o: ['substance', 'behavioral'])

    has_professional_credentials = False
    professional_credentials = factory.LazyAttribute(lambda o: [])
    credentials_file_path = None

    years_in_recovery = factory.Iterator([1, 2, 3, 5, 10])
    support_experience_description = Faker('text', max_nb_chars=300)

    available_for_one_on_one = True
    available_for_group_leadership = False
    max_mentees = 2

    background_check_completed = False
    references_verified = False

    supporter_status = 'pending'

    created_at = factory.LazyFunction(lambda: timezone.now())
    updated_at = factory.LazyFunction(lambda: timezone.now())


class ApprovedSupporterQualificationsFactory(SupporterQualificationsFactory):
    """Factory for approved supporter qualifications."""

    background_check_completed = True
    references_verified = True
    supporter_status = 'approved'


class OnboardingFeedbackFactory(DjangoModelFactory):
    """Factory for creating onboarding feedback."""

    class Meta:
        model = OnboardingFeedback

    user_profile = SubFactory(
        'authentication.tests.factories.UserProfileFactory')

    step_name = factory.Iterator(
        ['welcome', 'user_purpose', 'recovery_approach', 'profile_setup'])
    rating = factory.Iterator([3, 4, 5])
    feedback_text = Faker('text', max_nb_chars=200)
    was_helpful = True

    created_at = factory.LazyFunction(lambda: timezone.now())
