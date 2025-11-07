"""
Tests for content reporting functionality.

Tests signal automation, permissions, and moderation workflow.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse

from group.models import Group, GroupMembership
from messaging.models import Discussion, Comment, ContentReport

User = get_user_model()


class ContentReportModelTest(TestCase):
    """Test ContentReport model functionality."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.leader = User.objects.create_user(
            username='leader',
            email='leader@test.com',
            password='testpass123'
        )
        self.member = User.objects.create_user(
            username='member',
            email='member@test.com',
            password='testpass123'
        )

        # Create group
        self.group = Group.objects.create(
            name='Test Group',
            description='Test description',
            leader=self.leader
        )

        # Add leader as active member
        GroupMembership.objects.create(
            user=self.leader,
            group=self.group,
            role='leader',
            status='active'
        )

        # Add member
        GroupMembership.objects.create(
            user=self.member,
            group=self.group,
            role='member',
            status='active'
        )

        # Create discussion
        self.discussion = Discussion.objects.create(
            group=self.group,
            author=self.leader,
            title='Test Discussion',
            content='Test content',
            category='bible_study'
        )

    def test_create_report(self):
        """Test creating a content report."""
        ct = ContentType.objects.get_for_model(Discussion)

        report = ContentReport.objects.create(
            reporter=self.member,
            content_type=ct,
            object_id=self.discussion.id,
            reason=ContentReport.SPAM,
            details='This is spam content'
        )

        self.assertEqual(report.status, ContentReport.PENDING)
        self.assertEqual(report.content_object, self.discussion)
        self.assertIsNone(report.reviewed_by)

    def test_report_updates_discussion_flags(self):
        """Test that creating a report updates discussion flags."""
        ct = ContentType.objects.get_for_model(Discussion)

        # Initially not reported
        self.assertFalse(self.discussion.is_reported)
        self.assertEqual(self.discussion.report_count, 0)

        # Create report
        ContentReport.objects.create(
            reporter=self.member,
            content_type=ct,
            object_id=self.discussion.id,
            reason=ContentReport.SPAM,
        )

        # Check flags updated
        self.discussion.refresh_from_db()
        self.assertTrue(self.discussion.is_reported)
        self.assertEqual(self.discussion.report_count, 1)

    def test_multiple_reports_increment_count(self):
        """Test multiple reports increment count."""
        ct = ContentType.objects.get_for_model(Discussion)

        # Create another member
        member2 = User.objects.create_user(
            username='member2',
            email='member2@test.com',
            password='testpass123'
        )
        GroupMembership.objects.create(
            user=member2,
            group=self.group,
            role='member',
            status='active'
        )

        # Create two reports
        ContentReport.objects.create(
            reporter=self.member,
            content_type=ct,
            object_id=self.discussion.id,
            reason=ContentReport.SPAM,
        )

        ContentReport.objects.create(
            reporter=member2,
            content_type=ct,
            object_id=self.discussion.id,
            reason=ContentReport.INAPPROPRIATE,
        )

        self.discussion.refresh_from_db()
        self.assertEqual(self.discussion.report_count, 2)

    def test_resolve_report_updates_flags(self):
        """Test resolving a report updates flags."""
        ct = ContentType.objects.get_for_model(Discussion)

        report = ContentReport.objects.create(
            reporter=self.member,
            content_type=ct,
            object_id=self.discussion.id,
            reason=ContentReport.SPAM,
        )

        # Resolve the report
        report.resolve(reviewed_by=self.leader, notes='Action taken')

        # Check status updated
        self.assertEqual(report.status, ContentReport.RESOLVED)
        self.assertEqual(report.reviewed_by, self.leader)
        self.assertIsNotNone(report.reviewed_at)

        # Check discussion flags updated (no active reports)
        self.discussion.refresh_from_db()
        self.assertFalse(self.discussion.is_reported)
        self.assertEqual(self.discussion.report_count, 0)

    def test_dismiss_report_updates_flags(self):
        """Test dismissing a report updates flags."""
        ct = ContentType.objects.get_for_model(Discussion)

        report = ContentReport.objects.create(
            reporter=self.member,
            content_type=ct,
            object_id=self.discussion.id,
            reason=ContentReport.SPAM,
        )

        # Dismiss the report
        report.dismiss(reviewed_by=self.leader, notes='Not spam')

        # Check status updated
        self.assertEqual(report.status, ContentReport.DISMISSED)

        # Check flags cleared
        self.discussion.refresh_from_db()
        self.assertFalse(self.discussion.is_reported)
        self.assertEqual(self.discussion.report_count, 0)

    def test_unique_constraint_prevents_duplicate_reports(self):
        """Test user cannot report same content twice."""
        from django.db import IntegrityError

        ct = ContentType.objects.get_for_model(Discussion)

        # Create first report
        ContentReport.objects.create(
            reporter=self.member,
            content_type=ct,
            object_id=self.discussion.id,
            reason=ContentReport.SPAM,
        )

        # Try to create duplicate
        with self.assertRaises(IntegrityError):
            ContentReport.objects.create(
                reporter=self.member,
                content_type=ct,
                object_id=self.discussion.id,
                reason=ContentReport.INAPPROPRIATE,
            )

    def test_report_comment(self):
        """Test reporting a comment works."""
        comment = Comment.objects.create(
            discussion=self.discussion,
            author=self.member,
            content='Test comment'
        )

        ct = ContentType.objects.get_for_model(Comment)

        report = ContentReport.objects.create(
            reporter=self.leader,
            content_type=ct,
            object_id=comment.id,
            reason=ContentReport.HARASSMENT,
            details='Inappropriate language'
        )

        self.assertEqual(report.content_object, comment)

        # Check comment flags
        comment.refresh_from_db()
        self.assertTrue(comment.is_reported)
        self.assertEqual(comment.report_count, 1)


class ContentReportAPITest(APITestCase):
    """Test Content Reporting API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create users
        self.leader = User.objects.create_user(
            username='leader',
            email='leader@test.com',
            password='testpass123'
        )
        self.member = User.objects.create_user(
            username='member',
            email='member@test.com',
            password='testpass123'
        )
        self.outsider = User.objects.create_user(
            username='outsider',
            email='outsider@test.com',
            password='testpass123'
        )

        # Create group
        self.group = Group.objects.create(
            name='Test Group',
            description='Test description',
            leader=self.leader
        )

        # Add leader as active member
        GroupMembership.objects.create(
            user=self.leader,
            group=self.group,
            role='leader',
            status='active'
        )

        # Add member
        GroupMembership.objects.create(
            user=self.member,
            group=self.group,
            role='member',
            status='active'
        )

        # Create discussion
        self.discussion = Discussion.objects.create(
            group=self.group,
            author=self.leader,
            title='Test Discussion',
            content='Test content',
            category='bible_study'
        )

    def test_report_discussion(self):
        """Test reporting a discussion via API."""
        self.client.force_authenticate(user=self.member)
        url = reverse('messaging:discussion-report',
                      kwargs={'pk': self.discussion.id})

        data = {
            'reason': 'spam',
            'details': 'This is spam content'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check report created
        self.assertEqual(ContentReport.objects.count(), 1)
        report = ContentReport.objects.first()
        self.assertEqual(report.reporter, self.member)
        self.assertEqual(report.reason, 'spam')

    def test_cannot_report_twice(self):
        """Test user cannot report same content twice."""
        ct = ContentType.objects.get_for_model(Discussion)

        # Create first report
        ContentReport.objects.create(
            reporter=self.member,
            content_type=ct,
            object_id=self.discussion.id,
            reason=ContentReport.SPAM,
        )

        # Try to report again
        self.client.force_authenticate(user=self.member)
        url = reverse('messaging:discussion-report',
                      kwargs={'pk': self.discussion.id})

        data = {'reason': 'inappropriate'}

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_member_cannot_report(self):
        """Test non-group members cannot report content."""
        self.client.force_authenticate(user=self.outsider)
        url = reverse('messaging:discussion-report',
                      kwargs={'pk': self.discussion.id})

        data = {'reason': 'spam'}

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_leader_can_view_reports(self):
        """Test group leaders can view reports for their groups."""
        ct = ContentType.objects.get_for_model(Discussion)

        # Create report
        ContentReport.objects.create(
            reporter=self.member,
            content_type=ct,
            object_id=self.discussion.id,
            reason=ContentReport.SPAM,
        )

        # Leader views reports
        self.client.force_authenticate(user=self.leader)
        url = reverse('messaging:report-list')

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_member_cannot_view_reports(self):
        """Test regular members cannot view reports list."""
        self.client.force_authenticate(user=self.member)
        url = reverse('messaging:report-list')

        response = self.client.get(url)
        # Should return empty list (no groups they lead)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_leader_can_resolve_report(self):
        """Test leaders can resolve reports."""
        ct = ContentType.objects.get_for_model(Discussion)

        report = ContentReport.objects.create(
            reporter=self.member,
            content_type=ct,
            object_id=self.discussion.id,
            reason=ContentReport.SPAM,
        )

        self.client.force_authenticate(user=self.leader)
        url = reverse('messaging:report-review', kwargs={'pk': report.id})

        data = {
            'action': 'resolve',
            'notes': 'Content removed'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check report updated
        report.refresh_from_db()
        self.assertEqual(report.status, ContentReport.RESOLVED)
        self.assertEqual(report.reviewed_by, self.leader)

    def test_leader_can_dismiss_report(self):
        """Test leaders can dismiss reports."""
        ct = ContentType.objects.get_for_model(Discussion)

        report = ContentReport.objects.create(
            reporter=self.member,
            content_type=ct,
            object_id=self.discussion.id,
            reason=ContentReport.SPAM,
        )

        self.client.force_authenticate(user=self.leader)
        url = reverse('messaging:report-review', kwargs={'pk': report.id})

        data = {
            'action': 'dismiss',
            'notes': 'False report'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check report updated
        report.refresh_from_db()
        self.assertEqual(report.status, ContentReport.DISMISSED)

    def test_report_comment_via_api(self):
        """Test reporting a comment via API."""
        comment = Comment.objects.create(
            discussion=self.discussion,
            author=self.member,
            content='Test comment'
        )

        # Leader needs to be added as active member to access comment endpoint
        self.client.force_authenticate(user=self.leader)
        url = reverse('messaging:comment-report', kwargs={'pk': comment.id})

        data = {
            'reason': 'harassment',
            'details': 'Inappropriate language'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check report created
        self.assertEqual(ContentReport.objects.count(), 1)
        report = ContentReport.objects.first()
        self.assertEqual(report.content_object, comment)
