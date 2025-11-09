"""
Tests for private messaging models (Conversation and PrivateMessage).
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from messaging.models import Conversation, PrivateMessage
from group.models import Group

User = get_user_model()


class ConversationModelTest(TestCase):
    """Test the Conversation model."""

    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='testpass123'
        )

        # Create a group for testing
        self.group = Group.objects.create(
            name='Test Group',
            description='A test group',
            leader=self.user2,
            location='Test Location'
        )

    def test_create_conversation(self):
        """Test creating a basic conversation."""
        conversation = Conversation.objects.create(
            context_type='group_inquiry',
            group=self.group,
            status='active'
        )
        conversation.participants.add(self.user1, self.user2)

        self.assertEqual(conversation.status, 'active')
        self.assertEqual(conversation.participants.count(), 2)
        self.assertIn(self.user1, conversation.participants.all())
        self.assertIn(self.user2, conversation.participants.all())

    def test_get_other_participant(self):
        """Test getting the other participant in a conversation."""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)

        other = conversation.get_other_participant(self.user1)
        self.assertEqual(other, self.user2)

        other = conversation.get_other_participant(self.user2)
        self.assertEqual(other, self.user1)

    def test_get_unread_count(self):
        """Test getting unread message count."""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)

        # Create some messages
        msg1 = PrivateMessage.objects.create(
            conversation=conversation,
            sender=self.user1,
            content='Hello',
            is_read=True  # Mark as read since user1 sent it
        )
        PrivateMessage.objects.create(
            conversation=conversation,
            sender=self.user2,
            content='Hi there',
            is_read=False
        )
        PrivateMessage.objects.create(
            conversation=conversation,
            sender=self.user2,
            content='How are you?',
            is_read=False
        )

        # User1 should have 2 unread messages from user2
        unread = conversation.get_unread_count(self.user1)
        self.assertEqual(unread, 2)

        # User2 should have 0 unread messages (the message from user1 is marked as read)
        unread = conversation.get_unread_count(self.user2)
        self.assertEqual(unread, 0)

    def test_mark_messages_as_read(self):
        """Test marking messages as read."""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)

        # Create unread messages
        msg1 = PrivateMessage.objects.create(
            conversation=conversation,
            sender=self.user2,
            content='Message 1',
            is_read=False
        )
        msg2 = PrivateMessage.objects.create(
            conversation=conversation,
            sender=self.user2,
            content='Message 2',
            is_read=False
        )

        # Mark as read for user1
        conversation.mark_messages_as_read(self.user1)

        # Refresh from database
        msg1.refresh_from_db()
        msg2.refresh_from_db()

        self.assertTrue(msg1.is_read)
        self.assertTrue(msg2.is_read)

    def test_close_conversation(self):
        """Test closing a conversation."""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)

        self.assertEqual(conversation.status, 'active')
        self.assertIsNone(conversation.closed_at)
        self.assertIsNone(conversation.closed_by)

        # Close the conversation
        conversation.close(user=self.user1, reason='resolved')

        self.assertEqual(conversation.status, 'closed')
        self.assertIsNotNone(conversation.closed_at)
        self.assertEqual(conversation.closed_by, self.user1)
        self.assertEqual(conversation.close_reason, 'resolved')

    def test_reopen_conversation(self):
        """Test reopening a closed conversation."""
        conversation = Conversation.objects.create(
            status='closed',
            closed_at=timezone.now(),
            close_reason='not_interested'
        )
        conversation.participants.add(self.user1, self.user2)
        conversation.closed_by = self.user1
        conversation.save()

        # Reopen the conversation
        conversation.reopen()

        self.assertEqual(conversation.status, 'active')
        self.assertIsNone(conversation.closed_at)
        self.assertIsNone(conversation.closed_by)
        self.assertIsNone(conversation.close_reason)

    def test_archive_conversation(self):
        """Test archiving a conversation."""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)

        conversation.archive()

        self.assertEqual(conversation.status, 'archived')

    def test_conversation_ordering(self):
        """Test that conversations are ordered by last_message_at."""
        conv1 = Conversation.objects.create(
            last_message_at=timezone.now() - timezone.timedelta(hours=2)
        )
        conv1.participants.add(self.user1, self.user2)

        conv2 = Conversation.objects.create(
            last_message_at=timezone.now() - timezone.timedelta(hours=1)
        )
        conv2.participants.add(self.user1, self.user2)

        conv3 = Conversation.objects.create(
            last_message_at=timezone.now()
        )
        conv3.participants.add(self.user1, self.user2)

        # Get all conversations
        conversations = list(Conversation.objects.all())

        # Should be ordered by last_message_at descending
        self.assertEqual(conversations[0], conv3)
        self.assertEqual(conversations[1], conv2)
        self.assertEqual(conversations[2], conv1)


class PrivateMessageModelTest(TestCase):
    """Test the PrivateMessage model."""

    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )

        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)

    def test_create_message(self):
        """Test creating a message."""
        message = PrivateMessage.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='Hello, world!'
        )

        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.content, 'Hello, world!')
        self.assertFalse(message.is_read)
        self.assertIsNotNone(message.created_at)

    def test_message_updates_conversation_last_message_at(self):
        """Test that creating a message updates conversation's last_message_at."""
        self.assertIsNone(self.conversation.last_message_at)

        message = PrivateMessage.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='Test message'
        )

        # Refresh conversation from database
        self.conversation.refresh_from_db()

        self.assertIsNotNone(self.conversation.last_message_at)
        self.assertEqual(
            self.conversation.last_message_at.replace(microsecond=0),
            message.created_at.replace(microsecond=0)
        )

    def test_message_ordering(self):
        """Test that messages are ordered by created_at."""
        msg1 = PrivateMessage.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='First message'
        )

        msg2 = PrivateMessage.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            content='Second message'
        )

        msg3 = PrivateMessage.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='Third message'
        )

        messages = list(self.conversation.private_messages.all())

        # Should be ordered by created_at ascending
        self.assertEqual(messages[0], msg1)
        self.assertEqual(messages[1], msg2)
        self.assertEqual(messages[2], msg3)

    def test_message_string_representation(self):
        """Test the string representation of a message."""
        message = PrivateMessage.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='Test message'
        )

        str_repr = str(message)
        self.assertIn('user1', str_repr)
        self.assertIn('Message from', str_repr)
