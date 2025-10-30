"""
Factory Boy factories for profiles app testing.

Provides test data generators for all profiles models using Factory Boy.
"""

import factory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyText, FuzzyChoice
from django.contrib.auth import get_user_model
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

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for User model."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'testuser{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = factory.PostGenerationMethodCall(
        'set_password', 'testpass123')  # nosec - test password
    is_active = True
    email_verified = True


class UserProfileBasicFactory(DjangoModelFactory):
    """Factory for UserProfileBasic model."""

    class Meta:
        model = UserProfileBasic

    user = factory.SubFactory(UserFactory)
    display_name = factory.Faker('name')
    bio = factory.Faker('text', max_nb_chars=500)
    timezone = FuzzyChoice(
        ['UTC', 'America/New_York', 'Europe/London', 'Asia/Tokyo'])
    is_profile_complete = False
    profile_completion_percentage = factory.Faker('random_int', min=0, max=100)
    show_email = False
    show_full_name = False
    profile_visibility = FuzzyChoice(['private', 'community', 'public'])


class ProfilePhotoFactory(DjangoModelFactory):
    """Factory for ProfilePhoto model."""

    class Meta:
        model = ProfilePhoto

    user = factory.SubFactory(UserFactory)

    @factory.lazy_attribute
    def photo(self):
        """Generate a test image file."""
        # Create a simple test image
        image = Image.new('RGB', (300, 300), color='red')

        # Save to BytesIO
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)

        # Create uploaded file
        return SimpleUploadedFile(
            name='test_photo.jpg',
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )

    @factory.lazy_attribute
    def thumbnail(self):
        """Generate a test thumbnail file."""
        # Create a simple test thumbnail
        image = Image.new('RGB', (150, 150), color='blue')

        # Save to BytesIO
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)

        # Create uploaded file
        return SimpleUploadedFile(
            name='test_thumbnail.jpg',
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )

    is_moderated = True
    moderation_status = 'approved'
    uploaded_at = factory.Faker('date_time_this_year')


class ProfileCompletenessTrackerFactory(DjangoModelFactory):
    """Factory for ProfileCompletenessTracker model."""

    class Meta:
        model = ProfileCompletenessTracker

    user = factory.SubFactory(UserFactory)
    overall_percentage = factory.Faker('random_int', min=0, max=100)
    basic_info_score = factory.Faker('random_int', min=0, max=100)
    photo_score = factory.Faker('random_int', min=0, max=100)
    privacy_score = factory.Faker('random_int', min=0, max=100)
    has_display_name = factory.Faker('boolean')
    has_bio = factory.Faker('boolean')
    has_photo = factory.Faker('boolean')
    has_privacy_settings = factory.Faker('boolean')
    completion_level = FuzzyChoice(
        ['beginner', 'intermediate', 'advanced', 'expert'])
    badges_earned = factory.LazyFunction(
        lambda: ['first_photo', 'profile_complete'])
    last_calculated = factory.Faker('date_time_this_year')


# Trait factories for common scenarios
class PublicUserProfileFactory(UserProfileBasicFactory):
    """Factory for public user profile."""
    profile_visibility = 'public'
    show_email = True
    show_full_name = True
    is_profile_complete = True
    profile_completion_percentage = 100


class PrivateUserProfileFactory(UserProfileBasicFactory):
    """Factory for private user profile."""
    profile_visibility = 'private'
    show_email = False
    show_full_name = False


class CompleteUserProfileFactory(UserProfileBasicFactory):
    """Factory for complete user profile with photo."""
    is_profile_complete = True
    profile_completion_percentage = 100

    @factory.post_generation
    def with_photo(self, create, extracted, **kwargs):
        if create:
            ProfilePhotoFactory(user=self.user)
            ProfileCompletenessTrackerFactory(
                user=self.user,
                overall_percentage=100,
                basic_info_score=100,
                photo_score=100,
                privacy_score=100,
                has_display_name=True,
                has_bio=True,
                has_photo=True,
                has_privacy_settings=True,
                completion_level='expert'
            )


class IncompleteUserProfileFactory(UserProfileBasicFactory):
    """Factory for incomplete user profile."""
    display_name = ''
    bio = ''
    is_profile_complete = False
    profile_completion_percentage = 25


class ModeratedPhotoFactory(ProfilePhotoFactory):
    """Factory for moderated photo."""
    is_moderated = True
    moderation_status = 'approved'


class PendingPhotoFactory(ProfilePhotoFactory):
    """Factory for photo pending moderation."""
    is_moderated = False
    moderation_status = 'pending'


class RejectedPhotoFactory(ProfilePhotoFactory):
    """Factory for rejected photo."""
    is_moderated = True
    moderation_status = 'rejected'
