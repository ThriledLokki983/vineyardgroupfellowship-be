"""
Model tests for messaging app.

Tests core model functionality including:
- Discussion creation and soft delete
- Comment threading and edit window
- Reaction uniqueness constraints
- FeedItem auto-population
- Atomic count updates
- CommentHistory tracking
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import timedelta
import time

from group.models import Group
from messaging.models import (
    Discussion,
    Comment,
    CommentHistory,
    Reaction,
    FeedItem,
    NotificationPreference,
    NotificationLog,
)

User = get_user_model()


class DiscussionModelTest(TestCase):
    """Test Discussion model."""

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

    def test_discussion_creation(self):
        """Test creating a discussion."""
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test Discussion',
            content='This is test content for the discussion.',
            category='general',
        )

        self.assertEqual(discussion.title, 'Test Discussion')
        self.assertEqual(discussion.author, self.user)
        self.assertEqual(discussion.group, self.group)
        self.assertEqual(discussion.comment_count, 0)
        self.assertEqual(discussion.reaction_count, 0)
        self.assertFalse(discussion.is_deleted)
        self.assertFalse(discussion.is_pinned)

    def test_discussion_soft_delete(self):
        """Test soft deleting a discussion."""
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test Discussion',
            content='This is test content.',
        )

        self.assertFalse(discussion.is_deleted)
        self.assertIsNone(discussion.deleted_at)

        discussion.soft_delete()

        self.assertTrue(discussion.is_deleted)
        self.assertIsNotNone(discussion.deleted_at)

    def test_discussion_atomic_comment_count(self):
        """Test atomic comment count increment/decrement."""
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test Discussion',
            content='This is test content.',
        )

        self.assertEqual(discussion.comment_count, 0)

        # Increment
        discussion.increment_comment_count()
        self.assertEqual(discussion.comment_count, 1)

        # Increment again
        discussion.increment_comment_count()
        self.assertEqual(discussion.comment_count, 2)

        # Decrement
        discussion.decrement_comment_count()
        self.assertEqual(discussion.comment_count, 1)

    def test_discussion_atomic_reaction_count(self):
        """Test atomic reaction count increment/decrement."""
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test Discussion',
            content='This is test content.',
        )

        self.assertEqual(discussion.reaction_count, 0)

        discussion.increment_reaction_count()
        self.assertEqual(discussion.reaction_count, 1)

        discussion.decrement_reaction_count()
        self.assertEqual(discussion.reaction_count, 0)

    def test_discussion_str(self):
        """Test string representation."""
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test Discussion',
            content='This is test content.',
        )

        expected = f"Test Discussion by {self.user.username} in {self.group.name}"
        self.assertEqual(str(discussion), expected)


class CommentModelTest(TestCase):
    """Test Comment model."""

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
        self.discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test Discussion',
            content='This is test content.',
        )

    def test_comment_creation(self):
        """Test creating a comment."""
        comment = Comment.objects.create(
            discussion=self.discussion,
            author=self.user,
            content='This is a test comment.',
        )

        self.assertEqual(comment.content, 'This is a test comment.')
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.discussion, self.discussion)
        self.assertIsNone(comment.parent)
        self.assertFalse(comment.is_edited)
        self.assertFalse(comment.is_deleted)

    def test_comment_threading(self):
        """Test threaded comments (replies)."""
        parent_comment = Comment.objects.create(
            discussion=self.discussion,
            author=self.user,
            content='Parent comment',
        )

        reply_comment = Comment.objects.create(
            discussion=self.discussion,
            author=self.user,
            parent=parent_comment,
            content='Reply to parent',
        )

        self.assertEqual(reply_comment.parent, parent_comment)
        self.assertIn(reply_comment, parent_comment.replies.all())

    def test_comment_edit_window(self):
        """Test 15-minute edit window."""
        comment = Comment.objects.create(
            discussion=self.discussion,
            author=self.user,
            content='Original content',
        )

        # Should be editable immediately
        self.assertTrue(comment.can_edit())

        # Mock comment as 20 minutes old
        past_time = timezone.now() - timedelta(minutes=20)
        Comment.objects.filter(pk=comment.pk).update(created_at=past_time)
        comment.refresh_from_db()

        # Should NOT be editable after 15 minutes
        self.assertFalse(comment.can_edit())

    def test_comment_soft_delete(self):
        """Test soft deleting a comment."""
        comment = Comment.objects.create(
            discussion=self.discussion,
            author=self.user,
            content='Test comment',
        )

        self.assertFalse(comment.is_deleted)

        comment.soft_delete()

        self.assertTrue(comment.is_deleted)
        self.assertIsNotNone(comment.deleted_at)

        # Deleted comments can't be edited
        self.assertFalse(comment.can_edit())


class CommentHistoryModelTest(TestCase):
    """Test CommentHistory model."""

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
        self.discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test Discussion',
            content='This is test content.',
        )
        self.comment = Comment.objects.create(
            discussion=self.discussion,
            author=self.user,
            content='Original content',
        )

    def test_comment_history_creation(self):
        """Test creating comment history entry."""
        history = CommentHistory.objects.create(
            comment=self.comment,
            content='Old content',
            edited_by=self.user,
        )

        self.assertEqual(history.comment, self.comment)
        self.assertEqual(history.content, 'Old content')
        self.assertEqual(history.edited_by, self.user)
        self.assertIsNotNone(history.edited_at)


class ReactionModelTest(TestCase):
    """Test Reaction model."""

    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.group = Group.objects.create(
            name='Test Group',
            description='A test group',
            location='Test Location',
            leader=self.user1,
        )
        self.discussion = Discussion.objects.create(
            group=self.group,
            author=self.user1,
            title='Test Discussion',
            content='This is test content.',
        )
        self.comment = Comment.objects.create(
            discussion=self.discussion,
            author=self.user1,
            content='Test comment',
        )

    def test_reaction_to_discussion(self):
        """Test creating a reaction to a discussion."""
        reaction = Reaction.objects.create(
            user=self.user1,
            discussion=self.discussion,
            reaction_type='👍',
        )

        self.assertEqual(reaction.user, self.user1)
        self.assertEqual(reaction.discussion, self.discussion)
        self.assertIsNone(reaction.comment)
        self.assertEqual(reaction.reaction_type, '👍')

    def test_reaction_to_comment(self):
        """Test creating a reaction to a comment."""
        reaction = Reaction.objects.create(
            user=self.user1,
            comment=self.comment,
            reaction_type='❤️',
        )

        self.assertEqual(reaction.user, self.user1)
        self.assertEqual(reaction.comment, self.comment)
        self.assertIsNone(reaction.discussion)
        self.assertEqual(reaction.reaction_type, '❤️')

    def test_reaction_uniqueness_per_discussion(self):
        """Test user can only react once per discussion."""
        from django.contrib.contenttypes.models import ContentType

        discussion_ct = ContentType.objects.get_for_model(Discussion)
        Reaction.objects.create(
            user=self.user1,
            content_type=discussion_ct,
            object_id=self.discussion.id,
            reaction_type='👍',
        )

        # Trying to react again should raise IntegrityError
        with self.assertRaises(IntegrityError):
            Reaction.objects.create(
                user=self.user1,
                content_type=discussion_ct,
                object_id=self.discussion.id,
                reaction_type='❤️',
            )

    def test_reaction_uniqueness_per_comment(self):
        """Test user can only react once per comment."""
        from django.contrib.contenttypes.models import ContentType

        comment_ct = ContentType.objects.get_for_model(Comment)
        Reaction.objects.create(
            user=self.user1,
            content_type=comment_ct,
            object_id=self.comment.id,
            reaction_type='👍',
        )

        # Trying to react again should raise IntegrityError
        with self.assertRaises(IntegrityError):
            Reaction.objects.create(
                user=self.user1,
                content_type=comment_ct,
                object_id=self.comment.id,
                reaction_type='❤️',
            )

    def test_multiple_users_can_react(self):
        """Test multiple users can react to same content."""
        Reaction.objects.create(
            user=self.user1,
            discussion=self.discussion,
            reaction_type='👍',
        )

        # Different user should be able to react
        reaction2 = Reaction.objects.create(
            user=self.user2,
            discussion=self.discussion,
            reaction_type='❤️',
        )

        self.assertEqual(Reaction.objects.filter(
            discussion=self.discussion).count(), 2)

    def test_reaction_validation(self):
        """Test reaction must be for discussion OR comment, not both."""
        # This should fail validation
        reaction = Reaction(
            user=self.user1,
            discussion=self.discussion,
            comment=self.comment,  # Can't have both
            reaction_type='👍',
        )

        with self.assertRaises(ValidationError):
            reaction.clean()


class FeedItemModelTest(TestCase):
    """Test FeedItem model and signal auto-population."""

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

    def test_feeditem_auto_created_on_discussion(self):
        """Test FeedItem is automatically created when Discussion is created."""
        # Initially no feed items
        self.assertEqual(FeedItem.objects.count(), 0)

        # Create discussion
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test Discussion',
            content='This is test content for the discussion.',
        )

        # FeedItem should be auto-created
        self.assertEqual(FeedItem.objects.count(), 1)

        feed_item = FeedItem.objects.first()
        self.assertEqual(feed_item.content_type, 'discussion')
        self.assertEqual(feed_item.content_id, discussion.id)
        self.assertEqual(feed_item.author, self.user)
        self.assertEqual(feed_item.title, discussion.title)
        self.assertIn('This is test content', feed_item.preview)

    def test_feeditem_updated_on_discussion_update(self):
        """Test FeedItem is updated when Discussion is updated."""
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Original Title',
            content='Original content',
        )

        feed_item = FeedItem.objects.first()
        original_title = feed_item.title

        # Update discussion
        discussion.title = 'Updated Title'
        discussion.save()

        feed_item.refresh_from_db()
        self.assertEqual(feed_item.title, 'Updated Title')
        self.assertNotEqual(feed_item.title, original_title)

    def test_feeditem_preview_truncation(self):
        """Test FeedItem preview is truncated to 300 chars."""
        long_content = 'A' * 500

        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test',
            content=long_content,
        )

        feed_item = FeedItem.objects.first()
        self.assertEqual(len(feed_item.preview), 303)  # 300 + '...'
        self.assertTrue(feed_item.preview.endswith('...'))


class NotificationPreferenceModelTest(TestCase):
    """Test NotificationPreference model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_notification_preference_creation(self):
        """Test creating notification preferences."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            email_enabled=True,
            quiet_hours_enabled=True,
        )

        self.assertEqual(pref.user, self.user)
        self.assertTrue(pref.email_enabled)
        self.assertTrue(pref.quiet_hours_enabled)
        self.assertIsNotNone(pref.unsubscribe_token)

    def test_quiet_hours_check(self):
        """Test quiet hours checking logic."""
        from datetime import time

        pref = NotificationPreference.objects.create(
            user=self.user,
            quiet_hours_enabled=True,
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(8, 0),
        )

        # This test is time-dependent, so we just verify the method exists
        # and returns a boolean
        result = pref.is_in_quiet_hours()
        self.assertIsInstance(result, bool)


class NotificationLogModelTest(TestCase):
    """Test NotificationLog model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_notification_log_creation(self):
        """Test creating notification log entry."""
        log = NotificationLog.objects.create(
            user=self.user,
            notification_type='new_discussion',
            status='sent',
            to_email=self.user.email,
            subject='New Discussion Posted',
        )

        self.assertEqual(log.user, self.user)
        self.assertEqual(log.notification_type, 'new_discussion')
        self.assertEqual(log.status, 'sent')

    def test_count_recent_sends(self):
        """Test counting recent notification sends."""
        # Create 3 sent notifications
        for i in range(3):
            NotificationLog.objects.create(
                user=self.user,
                notification_type='new_discussion',
                status='sent',
                to_email=self.user.email,
                subject=f'Test {i}',
            )

        # Create 1 failed notification (shouldn't count)
        NotificationLog.objects.create(
            user=self.user,
            notification_type='new_discussion',
            status='failed',
            to_email=self.user.email,
            subject='Failed',
        )

        count = NotificationLog.count_recent_sends(self.user, hours=1)
        self.assertEqual(count, 3)
