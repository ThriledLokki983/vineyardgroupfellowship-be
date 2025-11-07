"""
Phase 2 Model Tests for Faith Features.

Tests for:
- PrayerRequest (creation, urgency, answer tracking)
- Testimony (creation, public sharing, approval)
- Scripture (creation, Bible API integration)
- Model methods and validation
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta

from group.models import Group
from messaging.models import (
    PrayerRequest,
    Testimony,
    Scripture,
    FeedItem,
)

User = get_user_model()


class PrayerRequestModelTest(TestCase):
    """Test PrayerRequest model."""

    def setUp(self):
        """Set up test data."""
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

    def test_create_prayer_request(self):
        """Test creating a prayer request."""
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Prayer for healing',
            content='Please pray for my friend who is sick.',
            category=PrayerRequest.PERSONAL,
            urgency=PrayerRequest.NORMAL,
        )

        self.assertEqual(prayer.title, 'Prayer for healing')
        self.assertEqual(prayer.urgency, PrayerRequest.NORMAL)
        self.assertEqual(prayer.category, PrayerRequest.PERSONAL)
        self.assertFalse(prayer.is_answered)
        self.assertEqual(prayer.prayer_count, 0)
        self.assertEqual(prayer.comment_count, 0)

    def test_urgent_prayer_request(self):
        """Test creating urgent prayer request."""
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='URGENT: Critical surgery',
            content='Please pray immediately.',
            urgency=PrayerRequest.URGENT,
        )

        self.assertEqual(prayer.urgency, PrayerRequest.URGENT)
        # Check string representation includes urgent icon
        self.assertIn('🔥', str(prayer))

    def test_mark_prayer_as_answered(self):
        """Test marking prayer as answered."""
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Prayer for job',
            content='Praying for new job opportunity.',
        )

        # Initially not answered
        self.assertFalse(prayer.is_answered)
        self.assertIsNone(prayer.answered_at)

        # Mark as answered
        answer_description = 'Got the job! Praise God!'
        prayer.mark_answered(answer_description=answer_description)

        # Refresh from database
        prayer.refresh_from_db()

        self.assertTrue(prayer.is_answered)
        self.assertIsNotNone(prayer.answered_at)
        self.assertEqual(prayer.answer_description, answer_description)

    def test_increment_prayer_count(self):
        """Test incrementing prayer count atomically."""
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Prayer request',
            content='Please pray.',
        )

        initial_count = prayer.prayer_count
        prayer.increment_prayer_count()

        self.assertEqual(prayer.prayer_count, initial_count + 1)

    def test_prayer_request_ordering(self):
        """Test that urgent prayers appear first."""
        normal_prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Normal prayer',
            content='Content',
            urgency=PrayerRequest.NORMAL,
        )

        urgent_prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Urgent prayer',
            content='Content',
            urgency=PrayerRequest.URGENT,
        )

        prayers = list(PrayerRequest.objects.all())
        # Urgent should be first due to ordering
        self.assertEqual(prayers[0].id, urgent_prayer.id)

    def test_prayer_categories(self):
        """Test all prayer categories."""
        categories = [
            PrayerRequest.PERSONAL,
            PrayerRequest.FAMILY,
            PrayerRequest.COMMUNITY,
            PrayerRequest.THANKSGIVING,
        ]

        for category in categories:
            prayer = PrayerRequest.objects.create(
                group=self.group,
                author=self.user,
                title=f'Prayer - {category}',
                content='Prayer content',
                category=category,
            )
            self.assertEqual(prayer.category, category)

    def test_prayer_content_validation(self):
        """Test that prayer content must be at least 10 characters."""
        # This will be validated by serializer, but test the model accepts it
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Short prayer',
            content='123456789',  # 9 chars - model accepts, serializer rejects
        )
        self.assertIsNotNone(prayer)


class TestimonyModelTest(TestCase):
    """Test Testimony model."""

    def setUp(self):
        """Set up test data."""
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

    def test_create_testimony(self):
        """Test creating a testimony."""
        testimony = Testimony.objects.create(
            group=self.group,
            author=self.user,
            title='God answered my prayer',
            content='This is how God worked in my life...',
        )

        self.assertEqual(testimony.title, 'God answered my prayer')
        self.assertFalse(testimony.is_public)
        self.assertFalse(testimony.is_public_approved)
        self.assertEqual(testimony.reaction_count, 0)

    def test_testimony_with_answered_prayer(self):
        """Test linking testimony to answered prayer."""
        # Create answered prayer
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Prayer for healing',
            content='Pray for healing',
            is_answered=True,
        )

        # Create testimony linked to prayer
        testimony = Testimony.objects.create(
            group=self.group,
            author=self.user,
            title='Healing testimony',
            content='God healed me!',
            answered_prayer=prayer,
        )

        self.assertEqual(testimony.answered_prayer, prayer)
        self.assertIn(testimony, prayer.testimonies.all())

    def test_share_testimony_publicly(self):
        """Test sharing testimony publicly."""
        testimony = Testimony.objects.create(
            group=self.group,
            author=self.user,
            title='Amazing testimony',
            content='God is good!',
        )

        # Initially private
        self.assertFalse(testimony.is_public)
        self.assertIsNone(testimony.public_shared_at)

        # Share publicly (without approval)
        testimony.share_publicly()

        testimony.refresh_from_db()
        self.assertTrue(testimony.is_public)
        self.assertIsNotNone(testimony.public_shared_at)
        self.assertFalse(testimony.is_public_approved)

    def test_approve_testimony_for_public(self):
        """Test leader approving testimony for public sharing."""
        testimony = Testimony.objects.create(
            group=self.group,
            author=self.user,
            title='Testimony to approve',
            content='This will be public',
        )

        # Share publicly first
        testimony.share_publicly()

        # Leader approves
        testimony.share_publicly(approved_by=self.leader)

        testimony.refresh_from_db()
        self.assertTrue(testimony.is_public)
        self.assertTrue(testimony.is_public_approved)
        self.assertEqual(testimony.approved_by, self.leader)

    def test_testimony_string_representation(self):
        """Test testimony string representation with icons."""
        # Private testimony
        private = Testimony.objects.create(
            group=self.group,
            author=self.user,
            title='Private',
            content='Content',
        )
        self.assertIn('👥', str(private))

        # Public testimony
        public = Testimony.objects.create(
            group=self.group,
            author=self.user,
            title='Public',
            content='Content',
            is_public=True,
        )
        self.assertIn('🌍', str(public))


class ScriptureModelTest(TestCase):
    """Test Scripture model."""

    def setUp(self):
        """Set up test data."""
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

    def test_create_scripture(self):
        """Test creating a scripture share."""
        scripture = Scripture.objects.create(
            group=self.group,
            author=self.user,
            reference='John 3:16',
            verse_text='For God so loved the world...',
            translation='KJV',
            source=Scripture.MANUAL,
        )

        self.assertEqual(scripture.reference, 'John 3:16')
        self.assertEqual(scripture.translation, 'KJV')
        self.assertEqual(scripture.source, Scripture.MANUAL)
        self.assertEqual(scripture.reaction_count, 0)

    def test_scripture_with_reflection(self):
        """Test scripture with personal reflection."""
        scripture = Scripture.objects.create(
            group=self.group,
            author=self.user,
            reference='Psalm 23:1',
            verse_text='The Lord is my shepherd...',
            translation='NIV',
            personal_reflection='This verse reminds me that God provides.',
        )

        self.assertIsNotNone(scripture.personal_reflection)
        self.assertIn('God provides', scripture.personal_reflection)

    def test_scripture_from_api(self):
        """Test scripture marked as from API."""
        scripture = Scripture.objects.create(
            group=self.group,
            author=self.user,
            reference='Philippians 4:13',
            verse_text='I can do all things through Christ...',
            translation='ESV',
            source=Scripture.API,
        )

        self.assertEqual(scripture.source, Scripture.API)

    def test_scripture_string_representation(self):
        """Test scripture string includes reference and icon."""
        scripture = Scripture.objects.create(
            group=self.group,
            author=self.user,
            reference='Romans 8:28',
            verse_text='And we know that in all things...',
            translation='NIV',
        )

        str_repr = str(scripture)
        self.assertIn('📖', str_repr)
        self.assertIn('Romans 8:28', str_repr)
        self.assertIn(self.user.username, str_repr)

    def test_multiple_translations(self):
        """Test scriptures can have different translations."""
        translations = ['KJV', 'NIV', 'ESV', 'NKJV']

        for translation in translations:
            scripture = Scripture.objects.create(
                group=self.group,
                author=self.user,
                reference='John 3:16',
                verse_text=f'Verse in {translation}',
                translation=translation,
            )
            self.assertEqual(scripture.translation, translation)


class Phase2FeedItemIntegrationTest(TestCase):
    """Test FeedItem integration with Phase 2 models."""

    def setUp(self):
        """Set up test data."""
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

    def test_prayer_request_creates_feed_item(self):
        """Test that creating prayer creates feed item."""
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Test Prayer',
            content='Please pray for this important matter.',
        )

        # Feed item should be auto-created by signal
        feed_items = FeedItem.objects.filter(
            content_type='prayer_request',
            content_id=prayer.id
        )

        self.assertEqual(feed_items.count(), 1)
        feed_item = feed_items.first()
        self.assertEqual(feed_item.author, self.user)
        self.assertEqual(feed_item.group, self.group)

    def test_urgent_prayer_feed_item_is_pinned(self):
        """Test that urgent prayers are auto-pinned in feed."""
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='URGENT Prayer',
            content='Urgent matter',
            urgency=PrayerRequest.URGENT,
        )

        feed_item = FeedItem.objects.get(
            content_type='prayer_request',
            content_id=prayer.id
        )

        # Urgent prayers should be pinned
        self.assertTrue(feed_item.is_pinned)
        self.assertIn('🔥', feed_item.title)

    def test_answered_prayer_updates_feed_item(self):
        """Test that answering prayer updates feed item."""
        prayer = PrayerRequest.objects.create(
            group=self.group,
            author=self.user,
            title='Prayer for job',
            content='Need a job',
            urgency=PrayerRequest.URGENT,
        )

        # Mark as answered
        prayer.mark_answered('Got the job!')

        # Feed item should be updated
        feed_item = FeedItem.objects.get(
            content_type='prayer_request',
            content_id=prayer.id
        )

        self.assertIn('✅', feed_item.title)
        self.assertIn('ANSWERED', feed_item.title)
        # Answered prayers no longer pinned
        self.assertFalse(feed_item.is_pinned)

    def test_testimony_creates_feed_item(self):
        """Test that creating testimony creates feed item."""
        testimony = Testimony.objects.create(
            group=self.group,
            author=self.user,
            title='Amazing Testimony',
            content='God is faithful!',
        )

        feed_items = FeedItem.objects.filter(
            content_type='testimony',
            content_id=testimony.id
        )

        self.assertEqual(feed_items.count(), 1)

    def test_public_testimony_updates_feed_item(self):
        """Test that making testimony public updates feed item."""
        testimony = Testimony.objects.create(
            group=self.group,
            author=self.user,
            title='Testimony',
            content='Content',
        )

        # Share publicly and approve
        testimony.share_publicly(approved_by=self.user)

        feed_item = FeedItem.objects.get(
            content_type='testimony',
            content_id=testimony.id
        )

        self.assertIn('🌍', feed_item.title)

    def test_scripture_creates_feed_item(self):
        """Test that creating scripture creates feed item."""
        scripture = Scripture.objects.create(
            group=self.group,
            author=self.user,
            reference='John 3:16',
            verse_text='For God so loved the world...',
            translation='KJV',
        )

        feed_items = FeedItem.objects.filter(
            content_type='scripture',
            content_id=scripture.id
        )

        self.assertEqual(feed_items.count(), 1)
        feed_item = feed_items.first()
        self.assertIn('📖', feed_item.title)
        self.assertIn('John 3:16', feed_item.title)
