"""
Phase 2 API Tests for Faith Features.

Tests for:
- PrayerRequest API endpoints
- Testimony API endpoints
- Scripture API endpoints
- Bible verse lookup
- Permissions and authentication
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from group.models import Group, GroupMembership
from messaging.models import (
    PrayerRequest,
    Testimony,
    Scripture,
)

User = get_user_model()


class PrayerRequestAPITest(TestCase):
    """Test PrayerRequest API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )

        # Create group
        self.group = Group.objects.create(
            name='Test Group',
            description='A test group',
            location='Test Location',
            leader=self.user,
        )

        # Add users to group
        GroupMembership.objects.create(
            group=self.group,
            user=self.user,
            role='leader',
            status='active'
        )
        GroupMembership.objects.create(
            group=self.group,
            user=self.other_user,
            role='member',
            status='active'
        )

        self.client.force_authenticate(user=self.user)

    def test_create_prayer_request(self):
        """Test creating a prayer request via API."""
        url = '/api/v1/messaging/prayer-requests/'
        data = {
            'group': self.group.id,
            'title': 'Prayer for healing',
            'content': 'Please pray for my friend who is sick.',
            'category': 'personal',
            'urgency': 'normal',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PrayerRequest.objects.count(), 1)

        prayer = PrayerRequest.objects.first()
        self.assertEqual(prayer.author, self.user)
        self.assertEqual(prayer.title, 'Prayer for healing')

    def test_create_urgent_prayer_request(self):
        """Test creating urgent prayer request."""
        url = '/api/v1/messaging/prayer-requests/'
        data = {
            'group': self.group.id,
            'title': 'URGENT: Critical surgery',
            'content': 'Please pray immediately for healing.',
            'urgency': 'urgent',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        prayer = PrayerRequest.objects.first()
        self.assertEqual(prayer.urgency, 'urgent')

    def test_list_prayer_requests(self):
        """Test listing prayer requests."""
        # Create some prayers
        PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Prayer 1',
            content='Content 1',
        )
        PrayerRequest.objects.create(
            group=self.group,
            author=self.other_user,
            title='Prayer 2',
            content='Content 2',
            urgency='urgent',
        )

        url = '/api/v1/messaging/prayer-requests/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_urgency(self):
        """Test filtering prayers by urgency."""
        PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Normal prayer',
            content='Content',
            urgency='normal',
        )
        PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Urgent prayer',
            content='Content',
            urgency='urgent',
        )

        url = '/api/v1/messaging/prayer-requests/?urgency=urgent'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['urgency'], 'urgent')

    def test_mark_prayer_as_answered(self):
        """Test marking prayer as answered via API."""
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Prayer for job',
            content='Need a job',
        )

        url = f'/api/v1/messaging/prayer-requests/{prayer.id}/mark-answered/'
        data = {
            'answer_description': 'Got the job! Praise God!'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        prayer.refresh_from_db()
        self.assertTrue(prayer.is_answered)
        self.assertEqual(prayer.answer_description, 'Got the job! Praise God!')

    def test_only_author_can_mark_answered(self):
        """Test that only author can mark prayer as answered."""
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.other_user,
            title='Prayer',
            content='Content',
        )

        url = f'/api/v1/messaging/prayer-requests/{prayer.id}/mark-answered/'
        data = {'answer_description': 'Answered'}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pray_action(self):
        """Test pray action increments count."""
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.other_user,
            title='Prayer',
            content='Please pray',
        )

        initial_count = prayer.prayer_count

        url = f'/api/v1/messaging/prayer-requests/{prayer.id}/pray/'
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        prayer.refresh_from_db()
        self.assertEqual(prayer.prayer_count, initial_count + 1)

    def test_unauthenticated_cannot_create_prayer(self):
        """Test that unauthenticated users cannot create prayers."""
        self.client.force_authenticate(user=None)

        url = '/api/v1/messaging/prayer-requests/'
        data = {
            'group': self.group.id,
            'title': 'Prayer',
            'content': 'Content',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestimonyAPITest(TestCase):
    """Test Testimony API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.leader = User.objects.create_user(
            username='leader',
            email='leader@example.com',
            password='testpass123'
        )

        self.group = Group.objects.create(
            name='Test Group',
            description='A test group',
            location='Test Location',
            leader=self.leader,
        )

        GroupMembership.objects.create(
            group=self.group,
            user=self.user,
            role='member',
            status='active'
        )
        GroupMembership.objects.create(
            group=self.group,
            user=self.leader,
            role='leader',
            status='active'
        )

        self.client.force_authenticate(user=self.user)

    def test_create_testimony(self):
        """Test creating a testimony via API."""
        url = '/api/v1/messaging/testimonies/'
        data = {
            'group': self.group.id,
            'title': 'God healed me',
            'content': 'This is my testimony of healing and restoration.',
            'is_public': False,
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Testimony.objects.count(), 1)

        testimony = Testimony.objects.first()
        self.assertEqual(testimony.author, self.user)
        self.assertFalse(testimony.is_public)

    def test_create_testimony_with_prayer_link(self):
        """Test creating testimony linked to answered prayer."""
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Prayer for healing',
            content='Pray for healing',
            is_answered=True,
        )

        url = '/api/v1/messaging/testimonies/'
        data = {
            'group': self.group.id,
            'title': 'Healing testimony',
            'content': 'God healed me as you prayed!',
            'answered_prayer': prayer.id,
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        testimony = Testimony.objects.first()
        self.assertEqual(testimony.answered_prayer, prayer)

    def test_share_testimony_publicly(self):
        """Test sharing testimony publicly."""
        testimony = Testimony.objects.create(
            group=self.group,
            author=self.user,
            title='Testimony',
            content='God is good!',
        )

        url = f'/api/v1/messaging/testimonies/{testimony.id}/share-public/'
        data = {'confirm': True}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        testimony.refresh_from_db()
        self.assertTrue(testimony.is_public)
        self.assertFalse(testimony.is_public_approved)  # Pending approval

    def test_only_author_can_share_publicly(self):
        """Test that only author can share testimony publicly."""
        testimony = Testimony.objects.create(
            group=self.group,
            author=self.leader,
            title='Testimony',
            content='Content',
        )

        url = f'/api/v1/messaging/testimonies/{testimony.id}/share-public/'
        data = {'confirm': True}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_testimonies(self):
        """Test listing testimonies."""
        Testimony.objects.create(
            group=self.group,
            author=self.user,
            title='Testimony 1',
            content='Content 1',
        )
        Testimony.objects.create(
            group=self.group,
            author=self.leader,
            title='Testimony 2',
            content='Content 2',
        )

        url = '/api/v1/messaging/testimonies/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)


class ScriptureAPITest(TestCase):
    """Test Scripture API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.group = Group.objects.create(
            name='Test Group',
            description='A test group',
            location='Test Location',
            leader=self.user,
        )

        GroupMembership.objects.create(
            group=self.group,
            user=self.user,
            role='leader',
            status='active'
        )

        self.client.force_authenticate(user=self.user)

    def test_create_scripture(self):
        """Test creating a scripture share via API."""
        url = '/api/v1/messaging/scriptures/'
        data = {
            'group': self.group.id,
            'reference': 'John 3:16',
            'verse_text': 'For God so loved the world...',
            'translation': 'KJV',
            'source': 'manual',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Scripture.objects.count(), 1)

        scripture = Scripture.objects.first()
        self.assertEqual(scripture.reference, 'John 3:16')
        self.assertEqual(scripture.translation, 'KJV')

    def test_create_scripture_with_reflection(self):
        """Test creating scripture with personal reflection."""
        url = '/api/v1/messaging/scriptures/'
        data = {
            'group': self.group.id,
            'reference': 'Psalm 23:1',
            'verse_text': 'The Lord is my shepherd...',
            'translation': 'NIV',
            'personal_reflection': 'This verse reminds me of God\'s provision.',
            'source': 'manual',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        scripture = Scripture.objects.first()
        self.assertIsNotNone(scripture.personal_reflection)

    @patch('messaging.services.bible_api.bible_service.get_verse')
    def test_verse_lookup_api(self, mock_get_verse):
        """Test Bible verse lookup via API."""
        # Mock the Bible API response
        mock_get_verse.return_value = {
            'reference': 'John 3:16',
            'text': 'For God so loved the world that he gave his one and only Son...',
            'translation': 'NIV',
            'source': 'bible-api.com',
        }

        url = '/api/v1/messaging/scriptures/verse-lookup/'
        data = {
            'reference': 'John 3:16',
            'translation': 'NIV',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('verse', response.data)
        self.assertEqual(response.data['verse']['reference'], 'John 3:16')

        # Verify the service was called
        mock_get_verse.assert_called_once_with('John 3:16', 'NIV')

    @patch('messaging.services.bible_api.bible_service.get_verse')
    def test_verse_lookup_not_found(self, mock_get_verse):
        """Test verse lookup when verse not found."""
        from rest_framework.exceptions import ValidationError

        # Mock API failure
        mock_get_verse.side_effect = ValidationError('Verse not found')

        url = '/api/v1/messaging/scriptures/verse-lookup/'
        data = {
            'reference': 'InvalidBook 999:999',
            'translation': 'KJV',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_scriptures(self):
        """Test listing scriptures."""
        Scripture.objects.create(
            group=self.group,
            author=self.user,
            reference='John 3:16',
            verse_text='Verse text',
            translation='KJV',
        )
        Scripture.objects.create(
            group=self.group,
            author=self.user,
            reference='Psalm 23:1',
            verse_text='Verse text',
            translation='NIV',
        )

        url = '/api/v1/messaging/scriptures/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_translation(self):
        """Test filtering scriptures by translation."""
        Scripture.objects.create(
            group=self.group,
            author=self.user,
            reference='John 3:16',
            verse_text='KJV text',
            translation='KJV',
        )
        Scripture.objects.create(
            group=self.group,
            author=self.user,
            reference='John 3:16',
            verse_text='NIV text',
            translation='NIV',
        )

        url = '/api/v1/messaging/scriptures/?translation=NIV'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['translation'], 'NIV')
