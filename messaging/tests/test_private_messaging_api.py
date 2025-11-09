"""
Tests for private messaging API endpoints.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from messaging.models import Conversation, PrivateMessage
from group.models import Group

User = get_user_model()


class ConversationAPITest(TestCase):
    """Test the Conversation API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create users
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

        # Create a group
        self.group = Group.objects.create(
            name='Test Group',
            description='A test group',
            leader=self.user2,
            location='Test Location'
        )

        # Authenticate as user1 by default
        self.client.force_authenticate(user=self.user1)

    def test_list_conversations(self):
        """Test listing user's conversations."""
        # Create conversations
        conv1 = Conversation.objects.create()
        conv1.participants.add(self.user1, self.user2)

        conv2 = Conversation.objects.create()
        conv2.participants.add(self.user1, self.user3)

        # Create a conversation without user1 (should not appear)
        conv3 = Conversation.objects.create()
        conv3.participants.add(self.user2, self.user3)

        url = reverse('messaging:conversation-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_conversations_unauthenticated(self):
        """Test that unauthenticated users cannot list conversations."""
        self.client.force_authenticate(user=None)

        url = reverse('messaging:conversation-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_conversation(self):
        """Test retrieving a single conversation."""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)

        # Add some messages
        PrivateMessage.objects.create(
            conversation=conversation,
            sender=self.user1,
            content='Hello'
        )
        PrivateMessage.objects.create(
            conversation=conversation,
            sender=self.user2,
            content='Hi there'
        )

        url = reverse('messaging:conversation-detail', args=[conversation.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['messages']), 2)
        self.assertEqual(response.data['message_count'], 2)

    def test_retrieve_conversation_not_participant(self):
        """Test that users cannot retrieve conversations they're not part of."""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user2, self.user3)

        url = reverse('messaging:conversation-detail', args=[conversation.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_group_inquiry_conversation(self):
        """Test creating a conversation via group inquiry."""
        url = reverse('messaging:conversation-group-inquiry')
        data = {
            'group_id': str(self.group.id),
            'message': 'Hi, I\'m interested in joining your group!'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('conversation', response.data)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['is_existing_conversation'], False)

        # Verify conversation was created
        conversation_id = response.data['conversation']['id']
        conversation = Conversation.objects.get(id=conversation_id)
        self.assertEqual(conversation.context_type, 'group_inquiry')
        self.assertEqual(conversation.group, self.group)
        self.assertIn(self.user1, conversation.participants.all())
        self.assertIn(self.user2, conversation.participants.all())

    def test_create_group_inquiry_conversation_existing(self):
        """Test creating a conversation when one already exists."""
        # Create existing conversation
        existing_conv = Conversation.objects.create(
            context_type='group_inquiry',
            group=self.group
        )
        existing_conv.participants.add(self.user1, self.user2)

        url = reverse('messaging:conversation-group-inquiry')
        data = {
            'group_id': str(self.group.id),
            'message': 'Another message'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_existing_conversation'], True)
        self.assertEqual(response.data['conversation']
                         ['id'], str(existing_conv.id))

    def test_create_group_inquiry_invalid_group(self):
        """Test creating conversation with invalid group ID."""
        url = reverse('messaging:conversation-group-inquiry')
        data = {
            'group_id': '00000000-0000-0000-0000-000000000000',
            'message': 'Test message'
        }

        response = self.client.post(url, data, format='json')

        # Serializer validation returns 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check that the error is about group_id
        self.assertTrue('group_id' in str(response.data)
                        or 'invalid_params' in response.data)

    def test_create_group_inquiry_message_self(self):
        """Test that users cannot message themselves."""
        # Authenticate as the group leader
        self.client.force_authenticate(user=self.user2)

        url = reverse('messaging:conversation-group-inquiry')
        data = {
            'group_id': str(self.group.id),
            'message': 'Test message'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'cannot_message_self')

    def test_send_message_in_conversation(self):
        """Test sending a message in an existing conversation."""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)

        url = reverse('messaging:conversation-send-message',
                      args=[conversation.id])
        data = {
            'content': 'This is a new message'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message']
                         ['content'], 'This is a new message')

        # Verify message was created
        message = PrivateMessage.objects.get(id=response.data['message']['id'])
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.content, 'This is a new message')

    def test_send_message_closed_conversation(self):
        """Test that messages cannot be sent in closed conversations."""
        conversation = Conversation.objects.create(status='closed')
        conversation.participants.add(self.user1, self.user2)

        url = reverse('messaging:conversation-send-message',
                      args=[conversation.id])
        data = {
            'content': 'This should fail'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'conversation_closed')

    def test_send_message_not_participant(self):
        """Test that non-participants cannot send messages."""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user2, self.user3)

        url = reverse('messaging:conversation-send-message',
                      args=[conversation.id])
        data = {
            'content': 'This should fail'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_close_conversation(self):
        """Test closing a conversation."""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)

        url = reverse('messaging:conversation-close', args=[conversation.id])
        data = {
            'reason': 'joined_group'
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['conversation']['status'], 'closed')
        self.assertEqual(response.data['conversation']
                         ['close_reason'], 'joined_group')

        # Verify in database
        conversation.refresh_from_db()
        self.assertEqual(conversation.status, 'closed')
        self.assertEqual(conversation.closed_by, self.user1)

    def test_close_already_closed_conversation(self):
        """Test closing an already closed conversation."""
        conversation = Conversation.objects.create(status='closed')
        conversation.participants.add(self.user1, self.user2)

        url = reverse('messaging:conversation-close', args=[conversation.id])
        data = {
            'reason': 'resolved'
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'already_closed')

    def test_reopen_conversation(self):
        """Test reopening a closed conversation."""
        conversation = Conversation.objects.create(status='closed')
        conversation.participants.add(self.user1, self.user2)
        conversation.closed_by = self.user1
        conversation.save()

        url = reverse('messaging:conversation-reopen', args=[conversation.id])
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['conversation']['status'], 'active')

        # Verify in database
        conversation.refresh_from_db()
        self.assertEqual(conversation.status, 'active')
        self.assertIsNone(conversation.closed_by)

    def test_reopen_active_conversation(self):
        """Test that active conversations cannot be reopened."""
        conversation = Conversation.objects.create(status='active')
        conversation.participants.add(self.user1, self.user2)

        url = reverse('messaging:conversation-reopen', args=[conversation.id])
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'not_closed')

    def test_filter_conversations_by_status(self):
        """Test filtering conversations by status."""
        # Create active conversation
        conv1 = Conversation.objects.create(status='active')
        conv1.participants.add(self.user1, self.user2)

        # Create closed conversation
        conv2 = Conversation.objects.create(status='closed')
        conv2.participants.add(self.user1, self.user3)

        # Filter by active
        url = reverse('messaging:conversation-list')
        response = self.client.get(url, {'status': 'active'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'active')

        # Filter by closed
        response = self.client.get(url, {'status': 'closed'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'closed')

    def test_mark_messages_as_read_on_retrieve(self):
        """Test that retrieving a conversation marks messages as read."""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)

        # Create unread messages from user2
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

        # Retrieve conversation as user1
        url = reverse('messaging:conversation-detail', args=[conversation.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Messages should now be marked as read
        msg1.refresh_from_db()
        msg2.refresh_from_db()

        self.assertTrue(msg1.is_read)
        self.assertTrue(msg2.is_read)
