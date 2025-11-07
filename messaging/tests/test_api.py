"""
API tests for messaging app ViewSets.

Tests all API endpoints including permissions, throttling, and business logic.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from group.models import Group, GroupMembership
from messaging.models import Discussion, Comment, Reaction, FeedItem, NotificationPreference

User = get_user_model()


class DiscussionAPITest(TestCase):
    """Test Discussion API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create users
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

        # Create group with user1 as leader
        self.group = Group.objects.create(
            name='Test Group',
            description='A test group',
            location='Test Location',
            leader=self.user1,
        )

        # Add both users as members
        GroupMembership.objects.create(
            group=self.group,
            user=self.user1,
            role='leader',
            status='active'
        )
        GroupMembership.objects.create(
            group=self.group,
            user=self.user2,
            role='member',
            status='active'
        )

    def test_list_discussions_requires_authentication(self):
        """Test that listing discussions requires authentication."""
        url = reverse('messaging:discussion-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_discussions_success(self):
        """Test listing discussions for authenticated user."""
        # Create discussion
        Discussion.objects.create(
            group=self.group,
            author=self.user1,
            title='Test Discussion',
            content='Test content',
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('messaging:discussion-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results']
                         [0]['title'], 'Test Discussion')

    def test_create_discussion_success(self):
        """Test creating a discussion."""
        self.client.force_authenticate(user=self.user1)
        url = reverse('messaging:discussion-list')

        data = {
            'group': str(self.group.id),
            'title': 'New Discussion',
            'content': 'This is a new discussion',
            'category': 'general'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Discussion.objects.count(), 1)

        # Check FeedItem was auto-created
        self.assertEqual(FeedItem.objects.count(), 1)

    def test_update_own_discussion(self):
        """Test author can update their own discussion."""
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user1,
            title='Original Title',
            content='Original content',
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('messaging:discussion-detail', args=[discussion.id])

        data = {
            'title': 'Updated Title',
            'content': 'Updated content',
        }

        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        discussion.refresh_from_db()
        self.assertEqual(discussion.title, 'Updated Title')

    def test_cannot_update_others_discussion(self):
        """Test that user cannot update another user's discussion."""
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user1,
            title='Original Title',
            content='Original content',
        )

        self.client.force_authenticate(user=self.user2)
        url = reverse('messaging:discussion-detail', args=[discussion.id])

        data = {'title': 'Hacked Title'}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_leader_can_update_any_discussion(self):
        """Test group leader can update any member's discussion."""
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user2,
            title='Original Title',
            content='Original content',
        )

        # user1 is the leader
        self.client.force_authenticate(user=self.user1)
        url = reverse('messaging:discussion-detail', args=[discussion.id])

        data = {'title': 'Moderated Title'}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_soft_delete_discussion(self):
        """Test deleting a discussion (soft delete)."""
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user1,
            title='To Delete',
            content='This will be deleted',
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('messaging:discussion-detail', args=[discussion.id])

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check soft delete
        discussion.refresh_from_db()
        self.assertTrue(discussion.is_deleted)
        self.assertIsNotNone(discussion.deleted_at)

    def test_pin_discussion_leaders_only(self):
        """Test pinning discussion requires leader permission."""
        discussion = Discussion.objects.create(
            group=self.group,
            author=self.user2,
            title='Test Discussion',
            content='Test content',
        )

        # Non-leader cannot pin
        self.client.force_authenticate(user=self.user2)
        url = reverse('messaging:discussion-pin', args=[discussion.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Leader can pin
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        discussion.refresh_from_db()
        self.assertTrue(discussion.is_pinned)


class CommentAPITest(TestCase):
    """Test Comment API endpoints."""

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

        self.discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test Discussion',
            content='Test content',
        )

    def test_create_comment_success(self):
        """Test creating a comment."""
        self.client.force_authenticate(user=self.user)
        url = reverse('messaging:comment-list')

        data = {
            'discussion': str(self.discussion.id),
            'content': 'This is a test comment',
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)

        # Check discussion comment count was updated
        self.discussion.refresh_from_db()
        self.assertEqual(self.discussion.comment_count, 1)

    def test_comment_edit_within_window(self):
        """Test editing comment within 15-minute window."""
        comment = Comment.objects.create(
            discussion=self.discussion,
            author=self.user,
            content='Original content',
        )

        self.client.force_authenticate(user=self.user)
        url = reverse('messaging:comment-detail', args=[comment.id])

        data = {'content': 'Updated content'}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'Updated content')


class ReactionAPITest(TestCase):
    """Test Reaction API endpoints."""

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

        self.discussion = Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test Discussion',
            content='Test content',
        )

    def test_create_reaction_success(self):
        """Test creating a reaction."""
        self.client.force_authenticate(user=self.user)
        url = reverse('messaging:reaction-list')

        data = {
            'discussion': str(self.discussion.id),
            'reaction_type': '👍',
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reaction.objects.count(), 1)

    def test_toggle_reaction_off(self):
        """Test toggling reaction off (delete)."""
        # Create initial reaction
        Reaction.objects.create(
            discussion=self.discussion,
            user=self.user,
            reaction_type='👍'
        )

        self.client.force_authenticate(user=self.user)
        url = reverse('messaging:reaction-list')

        # Post same reaction again (should delete)
        data = {
            'discussion': str(self.discussion.id),
            'reaction_type': '👍',
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Reaction.objects.count(), 0)

    def test_change_reaction_type(self):
        """Test changing reaction type."""
        # Create initial reaction
        Reaction.objects.create(
            discussion=self.discussion,
            user=self.user,
            reaction_type='👍'
        )

        self.client.force_authenticate(user=self.user)
        url = reverse('messaging:reaction-list')

        # Post different reaction (should update)
        data = {
            'discussion': str(self.discussion.id),
            'reaction_type': '❤️',
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Reaction.objects.count(), 1)

        reaction = Reaction.objects.first()
        self.assertEqual(reaction.reaction_type, '❤️')


class FeedAPITest(TestCase):
    """Test Feed API endpoints."""

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

    def test_feed_auto_populated_on_discussion_create(self):
        """Test feed is auto-populated when discussion is created."""
        Discussion.objects.create(
            group=self.group,
            author=self.user,
            title='Test Discussion',
            content='Test content',
        )

        # Check feed item was created
        self.assertEqual(FeedItem.objects.count(), 1)

        # Verify via API
        self.client.force_authenticate(user=self.user)
        url = reverse('messaging:feed-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_feed_readonly(self):
        """Test feed endpoints are read-only."""
        self.client.force_authenticate(user=self.user)
        url = reverse('messaging:feed-list')

        # Try to create (should fail)
        data = {'group': str(self.group.id)}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)


class NotificationPreferenceAPITest(TestCase):
    """Test NotificationPreference API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_get_or_create_preferences(self):
        """Test getting/creating user preferences."""
        self.client.force_authenticate(user=self.user)
        url = reverse('messaging:preference-list')

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Preference should be auto-created
        self.assertEqual(NotificationPreference.objects.count(), 1)

    def test_update_preferences(self):
        """Test updating notification preferences."""
        pref = NotificationPreference.objects.create(user=self.user)

        self.client.force_authenticate(user=self.user)
        url = reverse('messaging:preference-detail', args=[pref.id])

        from datetime import time
        data = {
            'email_enabled': False,
            'quiet_hours_enabled': True,
            'quiet_hours_start': '22:00:00',
            'quiet_hours_end': '08:00:00',
        }

        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        pref.refresh_from_db()
        self.assertFalse(pref.email_enabled)
        self.assertTrue(pref.quiet_hours_enabled)
