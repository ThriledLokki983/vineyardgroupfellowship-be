"""
Tests for peer-to-peer messaging functionality.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from messaging.models import Conversation, PrivateMessage
from group.models import Group, GroupMembership

User = get_user_model()


class PeerToPeerMessagingAPITest(TestCase):
    """Test the peer-to-peer messaging API endpoints."""

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
            leader=self.user1,
            location='Test Location'
        )

        # Add user1 and user2 as active members
        GroupMembership.objects.create(
            user=self.user1,
            group=self.group,
            status='active',
            role='leader'
        )
        GroupMembership.objects.create(
            user=self.user2,
            group=self.group,
            status='active',
            role='member'
        )

        # user3 is not in the group

        # Authenticate as user1 by default
        self.client.force_authenticate(user=self.user1)

        # URL for start action
        self.start_url = '/api/v1/messaging/conversations/start/'

    def test_start_conversation_success(self):
        """Test successfully starting a P2P conversation between group members."""
        data = {
            'recipient_id': str(self.user2.id),
            'message': 'Hi! How are you doing?'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('conversation', response.data)
        self.assertIn('message', response.data)
        self.assertIn('is_existing_conversation', response.data)
        self.assertFalse(response.data['is_existing_conversation'])

        # Check conversation details
        conversation_data = response.data['conversation']
        self.assertEqual(conversation_data['context_type'], 'direct_message')
        self.assertIsNone(conversation_data['group'])
        self.assertEqual(len(conversation_data['participants']), 2)

        # Check message details
        message_data = response.data['message']
        self.assertEqual(message_data['content'], 'Hi! How are you doing?')
        self.assertEqual(message_data['sender']['id'], str(self.user1.id))

    def test_start_conversation_with_group_context(self):
        """Test starting a P2P conversation with optional group context."""
        data = {
            'recipient_id': str(self.user2.id),
            'message': 'Let\'s discuss the group meeting',
            'group_id': str(self.group.id)
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        conversation_data = response.data['conversation']
        self.assertEqual(conversation_data['context_type'], 'direct_message')
        # Group details are in the nested context object
        self.assertIsNotNone(conversation_data['context']['group'])
        self.assertEqual(
            conversation_data['context']['group']['id'], str(self.group.id))

    def test_existing_conversation_returned(self):
        """Test that existing conversation is returned instead of creating duplicate."""
        # Create first conversation
        data = {
            'recipient_id': str(self.user2.id),
            'message': 'First message'
        }
        response1 = self.client.post(self.start_url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        conversation_id1 = response1.data['conversation']['id']

        # Try to create another conversation with same user
        data2 = {
            'recipient_id': str(self.user2.id),
            'message': 'Second message'
        }
        response2 = self.client.post(self.start_url, data2, format='json')

        # Should return 200 OK and existing conversation
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertTrue(response2.data['is_existing_conversation'])
        conversation_id2 = response2.data['conversation']['id']

        # Same conversation ID
        self.assertEqual(conversation_id1, conversation_id2)

        # But new message was created
        self.assertEqual(response2.data['message']
                         ['content'], 'Second message')

    def test_cannot_message_non_group_member(self):
        """Test that users cannot message non-group members."""
        data = {
            'recipient_id': str(self.user3.id),
            'message': 'Hi there!'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'no_shared_group')

    def test_cannot_message_self(self):
        """Test that user cannot message themselves."""
        data = {
            'recipient_id': str(self.user1.id),
            'message': 'Talking to myself'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'cannot_message_self')

    def test_inactive_membership_prevents_messaging(self):
        """Test that inactive group members cannot start conversations."""
        # Make user2's membership inactive
        membership = GroupMembership.objects.get(
            user=self.user2, group=self.group)
        membership.status = 'inactive'
        membership.save()

        data = {
            'recipient_id': str(self.user2.id),
            'message': 'Hello?'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'no_shared_group')

    def test_recipient_not_found(self):
        """Test error when recipient user does not exist."""
        import uuid
        fake_user_id = uuid.uuid4()

        data = {
            'recipient_id': str(fake_user_id),
            'message': 'Hello ghost'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check for validation error (can be in 'recipient_id' key or 'detail')
        self.assertTrue(
            'recipient_id' in response.data or
            ('detail' in response.data and 'recipient_id' in response.data['detail'])
        )

    def test_invalid_group_context(self):
        """Test error when group_id is invalid."""
        import uuid
        fake_group_id = uuid.uuid4()

        data = {
            'recipient_id': str(self.user2.id),
            'message': 'Test message',
            'group_id': str(fake_group_id)
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check for validation error (can be in 'group_id' key or 'detail')
        self.assertTrue(
            'group_id' in response.data or
            ('detail' in response.data and 'group_id' in response.data['detail'])
        )

    def test_conversation_appears_in_list(self):
        """Test that P2P conversations appear in user's conversation list."""
        # Create a P2P conversation
        data = {
            'recipient_id': str(self.user2.id),
            'message': 'Hey!'
        }
        self.client.post(self.start_url, data, format='json')

        # Get conversation list
        list_url = '/api/v1/messaging/conversations/'
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Handle paginated response
        conversations = response.data.get('results', response.data)
        self.assertGreaterEqual(len(conversations), 1)

        # Check if our conversation is in the list
        p2p_conversations = [
            c for c in conversations
            if c['context_type'] == 'direct_message'
        ]
        self.assertEqual(len(p2p_conversations), 1)

    def test_both_users_see_conversation(self):
        """Test that both participants see the conversation in their list."""
        # User1 starts conversation with user2
        data = {
            'recipient_id': str(self.user2.id),
            'message': 'Hello from user1'
        }
        response = self.client.post(self.start_url, data, format='json')
        conversation_id = response.data['conversation']['id']

        # User1 sees it
        list_url = '/api/v1/messaging/conversations/'
        response1 = self.client.get(list_url)
        conversations1 = response1.data.get('results', response1.data)
        conversation_ids_user1 = [c['id'] for c in conversations1]
        self.assertIn(conversation_id, conversation_ids_user1)

        # User2 sees it
        self.client.force_authenticate(user=self.user2)
        response2 = self.client.get(list_url)
        conversations2 = response2.data.get('results', response2.data)
        conversation_ids_user2 = [c['id'] for c in conversations2]
        self.assertIn(conversation_id, conversation_ids_user2)


class PeerToPeerIntegrationTest(TestCase):
    """Integration tests for P2P messaging full flows."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create users
        self.user1 = User.objects.create_user(
            username='alice',
            email='alice@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='bob',
            email='bob@test.com',
            password='testpass123'
        )

        # Create groups
        self.group1 = Group.objects.create(
            name='Alpha Group',
            description='First group',
            leader=self.user1,
            location='Location A'
        )
        self.group2 = Group.objects.create(
            name='Beta Group',
            description='Second group',
            leader=self.user2,
            location='Location B'
        )

        # Both users in group1
        GroupMembership.objects.create(
            user=self.user1,
            group=self.group1,
            status='active',
            role='leader'
        )
        GroupMembership.objects.create(
            user=self.user2,
            group=self.group1,
            status='active',
            role='member'
        )

        # Both users also in group2
        GroupMembership.objects.create(
            user=self.user1,
            group=self.group2,
            status='active',
            role='member'
        )
        GroupMembership.objects.create(
            user=self.user2,
            group=self.group2,
            status='active',
            role='leader'
        )

        # URL for start action
        self.start_url = '/api/v1/messaging/conversations/start/'

    def test_full_conversation_flow(self):
        """Test complete flow: start conversation, send messages, read messages."""
        # User1 starts conversation
        self.client.force_authenticate(user=self.user1)
        start_data = {
            'recipient_id': str(self.user2.id),
            'message': 'Hey Bob, how are you?'
        }
        response = self.client.post(self.start_url, start_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        conversation_id = response.data['conversation']['id']

        # User2 reads the conversation
        self.client.force_authenticate(user=self.user2)
        detail_url = f'/api/v1/messaging/conversations/{conversation_id}/'
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['messages']), 1)

        # User2 replies
        message_url = f'/api/v1/messaging/conversations/{conversation_id}/messages/'
        reply_data = {'content': 'Hi Alice! I\'m doing great, thanks!'}
        response = self.client.post(message_url, reply_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # User1 sees the reply
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(detail_url)
        self.assertEqual(len(response.data['messages']), 2)
        self.assertEqual(response.data['unread_count'], 0)  # Marked as read

    def test_multiple_shared_groups(self):
        """Test that users in multiple shared groups can message each other."""
        # Verify they're in 2 groups together
        from messaging.utils import check_shared_group_membership
        has_shared, shared_groups = check_shared_group_membership(
            self.user1, self.user2)
        self.assertTrue(has_shared)
        self.assertEqual(len(shared_groups), 2)

        # They can still message
        self.client.force_authenticate(user=self.user1)
        data = {
            'recipient_id': str(self.user2.id),
            'message': 'We have two groups in common!'
        }
        response = self.client.post(self.start_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_conversation_persists_after_leaving_group(self):
        """Test that conversation persists even after user leaves the group."""
        # Start conversation
        self.client.force_authenticate(user=self.user1)
        data = {
            'recipient_id': str(self.user2.id),
            'message': 'Let\'s stay in touch'
        }
        response = self.client.post(self.start_url, data, format='json')
        conversation_id = response.data['conversation']['id']

        # User1 leaves group1
        membership = GroupMembership.objects.get(
            user=self.user1, group=self.group1)
        membership.status = 'inactive'
        membership.save()

        # Conversation still exists and can be accessed
        detail_url = f'/api/v1/messaging/conversations/{conversation_id}/'
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # They're still in group2 together, so can send messages
        message_url = f'/api/v1/messaging/conversations/{conversation_id}/messages/'
        new_message = {'content': 'Still connected via Beta Group'}
        response = self.client.post(message_url, new_message, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
