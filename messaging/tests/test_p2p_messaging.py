"""
Tests for peer-to-peer messaging functionality.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from messaging.models import Conversation, PrivateMessage
from group.models import Group, GroupMembership

User = get_user_model()


class PeerToPeerMessagingTest(TestCase):
    """Test peer-to-peer messaging between group members."""

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
        self.user4 = User.objects.create_user(
            username='user4',
            email='user4@test.com',
            password='testpass123'
        )

        # Create groups
        self.group1 = Group.objects.create(
            name='Test Group 1',
            description='First test group',
            leader=self.user1,
            location='Test Location 1'
        )
        self.group2 = Group.objects.create(
            name='Test Group 2',
            description='Second test group',
            leader=self.user3,
            location='Test Location 2'
        )

        # Create active memberships
        # user1 and user2 in group1
        GroupMembership.objects.create(
            group=self.group1,
            user=self.user1,
            status='active',
            role='leader'
        )
        GroupMembership.objects.create(
            group=self.group1,
            user=self.user2,
            status='active',
            role='member'
        )

        # user2 and user3 in group2
        GroupMembership.objects.create(
            group=self.group2,
            user=self.user2,
            status='active',
            role='member'
        )
        GroupMembership.objects.create(
            group=self.group2,
            user=self.user3,
            status='active',
            role='leader'
        )

        # user4 has no memberships (isolated user)

        # URL for starting conversations
        self.start_url = reverse('conversation-start')

        # Authenticate as user1 by default
        self.client.force_authenticate(user=self.user1)

    def test_start_conversation_with_group_member_succeeds(self):
        """Test that users in the same group can start a conversation."""
        data = {
            'recipient_id': str(self.user2.id),
            'message': 'Hi! How are you?'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('conversation', response.data)
        self.assertIn('message', response.data)
        self.assertFalse(response.data['is_existing_conversation'])

        # Verify conversation created
        conversation = Conversation.objects.filter(
            context_type='direct_message',
            participants=self.user1
        ).filter(participants=self.user2).first()

        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.participants.count(), 2)
        self.assertEqual(conversation.private_messages.count(), 1)

        # Verify message created
        message = conversation.private_messages.first()
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.content, 'Hi! How are you?')

    def test_start_conversation_returns_existing_conversation(self):
        """Test that starting a conversation again returns the existing one."""
        # Create initial conversation
        data = {
            'recipient_id': str(self.user2.id),
            'message': 'First message'
        }
        response1 = self.client.post(self.start_url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        conversation_id = response1.data['conversation']['id']

        # Try to start conversation again
        data2 = {
            'recipient_id': str(self.user2.id),
            'message': 'Second message'
        }
        response2 = self.client.post(self.start_url, data2, format='json')

        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertTrue(response2.data['is_existing_conversation'])
        self.assertEqual(response2.data['conversation']['id'], conversation_id)

        # Verify only one conversation exists
        conversation_count = Conversation.objects.filter(
            context_type='direct_message',
            participants=self.user1
        ).filter(participants=self.user2).count()

        self.assertEqual(conversation_count, 1)

        # Verify both messages exist
        conversation = Conversation.objects.get(id=conversation_id)
        self.assertEqual(conversation.private_messages.count(), 2)

    def test_cannot_message_non_group_member(self):
        """Test that users not in the same group cannot message each other."""
        # user1 and user4 share no groups
        data = {
            'recipient_id': str(self.user4.id),
            'message': 'Hello stranger'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'no_shared_group')

        # Verify no conversation created
        conversation_exists = Conversation.objects.filter(
            context_type='direct_message',
            participants=self.user1
        ).filter(participants=self.user4).exists()

        self.assertFalse(conversation_exists)

    def test_cannot_message_self(self):
        """Test that users cannot message themselves."""
        data = {
            'recipient_id': str(self.user1.id),
            'message': 'Talking to myself'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'cannot_message_self')

    def test_inactive_membership_prevents_messaging(self):
        """Test that inactive group members cannot start conversations."""
        # Make user2's membership inactive
        membership = GroupMembership.objects.get(
            group=self.group1,
            user=self.user2
        )
        membership.status = 'inactive'
        membership.save()

        data = {
            'recipient_id': str(self.user2.id),
            'message': 'Can I message you?'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'no_shared_group')

    def test_pending_membership_prevents_messaging(self):
        """Test that pending group members cannot start conversations."""
        # Create pending membership for user4 in group1
        GroupMembership.objects.create(
            group=self.group1,
            user=self.user4,
            status='pending',
            role='member'
        )

        data = {
            'recipient_id': str(self.user4.id),
            'message': 'Hello pending member'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'no_shared_group')

    def test_conversation_with_optional_group_context(self):
        """Test starting a conversation with optional group context."""
        data = {
            'recipient_id': str(self.user2.id),
            'message': 'About our group activities',
            'group_id': str(self.group1.id)
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify conversation has group context
        conversation = Conversation.objects.filter(
            context_type='direct_message',
            participants=self.user1
        ).filter(participants=self.user2).first()

        self.assertIsNotNone(conversation.group)
        self.assertEqual(conversation.group.id, self.group1.id)

    def test_invalid_recipient_id_returns_404(self):
        """Test that invalid recipient ID returns 404."""
        import uuid
        fake_uuid = uuid.uuid4()

        data = {
            'recipient_id': str(fake_uuid),
            'message': 'Hello ghost'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'user_not_found')

    def test_invalid_group_id_returns_404(self):
        """Test that invalid group ID returns 404."""
        import uuid
        fake_uuid = uuid.uuid4()

        data = {
            'recipient_id': str(self.user2.id),
            'message': 'Hello',
            'group_id': str(fake_uuid)
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'group_not_found')

    def test_unauthenticated_user_cannot_start_conversation(self):
        """Test that unauthenticated users cannot start conversations."""
        self.client.force_authenticate(user=None)

        data = {
            'recipient_id': str(self.user2.id),
            'message': 'Anonymous message'
        }

        response = self.client.post(self.start_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PeerToPeerIntegrationTest(TestCase):
    """Integration tests for P2P messaging workflows."""

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

        # Create group
        self.group = Group.objects.create(
            name='Fellowship Group',
            description='Test fellowship',
            leader=self.user1,
            location='Test Location'
        )

        # Create active memberships
        GroupMembership.objects.create(
            group=self.group,
            user=self.user1,
            status='active',
            role='leader'
        )
        GroupMembership.objects.create(
            group=self.group,
            user=self.user2,
            status='active',
            role='member'
        )

        self.start_url = reverse('conversation-start')

    def test_full_conversation_flow(self):
        """Test complete conversation flow: start, send, read, reply."""
        # User1 starts conversation with User2
        self.client.force_authenticate(user=self.user1)
        response1 = self.client.post(self.start_url, {
            'recipient_id': str(self.user2.id),
            'message': 'Hi Bob, how are you?'
        }, format='json')

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        conversation_id = response1.data['conversation']['id']

        # User2 retrieves conversation detail (marks messages as read)
        self.client.force_authenticate(user=self.user2)
        detail_url = reverse('conversation-detail',
                             kwargs={'pk': conversation_id})
        response2 = self.client.get(detail_url)

        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response2.data['messages']), 1)

        # User2 replies
        send_url = reverse('conversation-send-message',
                           kwargs={'pk': conversation_id})
        response3 = self.client.post(send_url, {
            'content': 'Hi Alice! I\'m doing great, thanks!'
        }, format='json')

        self.assertEqual(response3.status_code, status.HTTP_201_CREATED)

        # User1 sees the reply
        self.client.force_authenticate(user=self.user1)
        response4 = self.client.get(detail_url)

        self.assertEqual(len(response4.data['messages']), 2)
        # Marked as read on retrieval
        self.assertEqual(response4.data['unread_count'], 0)

    def test_conversation_appears_in_both_users_lists(self):
        """Test that P2P conversations appear in both participants' conversation lists."""
        # User1 starts conversation
        self.client.force_authenticate(user=self.user1)
        response1 = self.client.post(self.start_url, {
            'recipient_id': str(self.user2.id),
            'message': 'Test message'
        }, format='json')

        conversation_id = response1.data['conversation']['id']

        # Check User1's conversation list
        list_url = reverse('conversation-list')
        response2 = self.client.get(list_url)

        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        conversation_ids = [c['id'] for c in response2.data['results']]
        self.assertIn(conversation_id, conversation_ids)

        # Check User2's conversation list
        self.client.force_authenticate(user=self.user2)
        response3 = self.client.get(list_url)

        self.assertEqual(response3.status_code, status.HTTP_200_OK)
        conversation_ids = [c['id'] for c in response3.data['results']]
        self.assertIn(conversation_id, conversation_ids)

    def test_user_leaves_group_conversation_persists(self):
        """Test that conversation persists even after user leaves group."""
        # User1 starts conversation with User2
        self.client.force_authenticate(user=self.user1)
        response1 = self.client.post(self.start_url, {
            'recipient_id': str(self.user2.id),
            'message': 'Important message'
        }, format='json')

        conversation_id = response1.data['conversation']['id']

        # User2 leaves the group
        membership = GroupMembership.objects.get(
            group=self.group,
            user=self.user2
        )
        membership.status = 'inactive'
        membership.save()

        # Both users can still access the conversation
        detail_url = reverse('conversation-detail',
                             kwargs={'pk': conversation_id})

        # User1 can access
        response2 = self.client.get(detail_url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # User2 can access
        self.client.force_authenticate(user=self.user2)
        response3 = self.client.get(detail_url)
        self.assertEqual(response3.status_code, status.HTTP_200_OK)

        # But they cannot start new conversations
        self.client.force_authenticate(user=self.user1)
        response4 = self.client.post(self.start_url, {
            'recipient_id': str(self.user2.id),
            'message': 'New message after leaving'
        }, format='json')

        # Should return existing conversation (already created before leaving)
        self.assertEqual(response4.status_code, status.HTTP_200_OK)
        self.assertTrue(response4.data['is_existing_conversation'])
