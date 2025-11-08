"""
Locust Load Testing for Vineyard Group Fellowship - Messaging App
==================================================================

This file contains load testing scenarios for the messaging app endpoints.

To run load tests:
    # Start Django server first
    python manage.py runserver 8000

    # In another terminal, run Locust
    locust -f locustfile.py --host=http://localhost:8000

    # Then open browser to http://localhost:8089

For headless testing:
    locust -f locustfile.py --host=http://localhost:8000 \\
           --users 100 --spawn-rate 10 --run-time 60s --headless

Performance Targets:
    - Feed endpoint: < 200ms
    - Discussion list: < 100ms
    - Prayer request creation: < 300ms (includes email)
    - Scripture lookup (cached): < 100ms
"""

import json
import random
from locust import HttpUser, task, between, SequentialTaskSet
from faker import Faker

fake = Faker()


class AuthenticatedUser(HttpUser):
    """
    Base user class with authentication and common behaviors.
    Simulates a typical group member browsing and interacting.
    """

    abstract = True  # Mark as abstract - this is a base class only
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    def on_start(self):
        """Run once when user starts - authenticate and get token."""
        # Create a test user and authenticate
        username = f"loadtest_{fake.user_name()}_{random.randint(1000, 9999)}"
        email = f"{username}@example.com"
        # Generate a strong, unique password that won't be in breach databases
        password = f"LoadTest{random.randint(100000, 999999)}!Secure@{fake.uuid4()[:8]}"

        # Register user
        register_data = {
            "email": email,
            "username": username,
            "password": password,
            "password_confirm": password,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "privacy_policy_accepted": True,
            "terms_of_service_accepted": True,
        }

        response = self.client.post(
            "/api/v1/auth/register/",
            json=register_data,
            name="Register User"
        )

        if response.status_code == 201:
            # Login to get JWT tokens
            login_data = {
                "email_or_username": email,
                "password": password
            }

            response = self.client.post(
                "/api/v1/auth/login/",
                json=login_data,
                name="Login"
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data['access']
                self.headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                self.user_id = data.get('user', {}).get('id')
            else:
                self.access_token = None
                self.headers = {}
        else:
            self.access_token = None
            self.headers = {}

        # Create or join a test group
        self.group_id = None
        self._setup_group()

    def _setup_group(self):
        """Create or join a test group for testing."""
        # Try to list groups first
        response = self.client.get(
            "/api/v1/groups/",
            headers=self.headers,
            name="List Groups"
        )

        if response.status_code == 200:
            groups = response.json().get('results', [])
            if groups:
                # Join first available group
                self.group_id = groups[0]['id']
                return

        # If no groups available, create one
        group_data = {
            "name": f"Load Test Group {random.randint(1000, 9999)}",
            "description": "Automated load test group",
            "privacy_level": "public",
            "category": "bible_study"
        }

        response = self.client.post(
            "/api/v1/groups/",
            json=group_data,
            headers=self.headers,
            name="Create Group"
        )

        if response.status_code == 201:
            self.group_id = response.json()['id']


class MessagingUserBehavior(SequentialTaskSet):
    """
    Sequential task set simulating typical user journey:
    1. Browse feed
    2. View discussions
    3. Create prayer request
    4. React to content
    5. Post comment
    """

    @task
    def view_feed(self):
        """View the activity feed - most common action."""
        if not self.user.group_id:
            return

        self.client.get(
            f"/api/v1/messaging/feed/?group={self.user.group_id}",
            headers=self.user.headers,
            name="View Feed"
        )

    @task
    def list_discussions(self):
        """Browse discussion topics."""
        if not self.user.group_id:
            return

        self.client.get(
            f"/api/v1/messaging/discussions/?group={self.user.group_id}",
            headers=self.user.headers,
            name="List Discussions"
        )

    @task
    def view_discussion_detail(self):
        """View a specific discussion thread."""
        if not self.user.group_id:
            return

        # Get discussions first
        response = self.client.get(
            f"/api/v1/messaging/discussions/?group={self.user.group_id}",
            headers=self.user.headers,
            name="Get Discussions for Detail"
        )

        if response.status_code == 200:
            discussions = response.json().get('results', [])
            if discussions:
                discussion_id = discussions[0]['id']
                self.client.get(
                    f"/api/v1/messaging/discussions/{discussion_id}/",
                    headers=self.user.headers,
                    name="View Discussion Detail"
                )

    @task
    def create_prayer_request(self):
        """Submit a prayer request."""
        if not self.user.group_id:
            return

        prayer_data = {
            "group": self.user.group_id,
            "title": f"Prayer Request - {fake.sentence(nb_words=4)}",
            "description": fake.paragraph(nb_sentences=2),
            "prayer_type": random.choice(['personal', 'family', 'community', 'thanksgiving']),
            # 66% normal
            "urgency_level": random.choice(['normal', 'normal', 'urgent']),
        }

        self.client.post(
            "/api/v1/messaging/prayer-requests/",
            json=prayer_data,
            headers=self.user.headers,
            name="Create Prayer Request"
        )

    @task
    def list_prayer_requests(self):
        """View prayer requests in group."""
        if not self.user.group_id:
            return

        self.client.get(
            f"/api/v1/messaging/prayer-requests/?group={self.user.group_id}",
            headers=self.user.headers,
            name="List Prayer Requests"
        )

    @task
    def share_testimony(self):
        """Share a testimony (less frequent)."""
        if not self.user.group_id:
            return

        testimony_data = {
            "group": self.user.group_id,
            "title": f"God's Faithfulness - {fake.sentence(nb_words=3)}",
            "content": fake.paragraph(nb_sentences=3),
            "category": random.choice(['answered_prayer', 'healing', 'provision', 'spiritual_growth'])
        }

        self.client.post(
            "/api/v1/messaging/testimonies/",
            json=testimony_data,
            headers=self.user.headers,
            name="Share Testimony"
        )

    @task
    def share_scripture(self):
        """Share scripture with reflection."""
        if not self.user.group_id:
            return

        verses = [
            "John 3:16",
            "Philippians 4:13",
            "Psalm 23:1",
            "Romans 8:28",
            "Jeremiah 29:11"
        ]

        scripture_data = {
            "group": self.user.group_id,
            "reference": random.choice(verses),
            "translation": "KJV",
            "reflection": fake.paragraph(nb_sentences=2)
        }

        self.client.post(
            "/api/v1/messaging/scriptures/",
            json=scripture_data,
            headers=self.user.headers,
            name="Share Scripture"
        )

    @task
    def add_reaction(self):
        """React to content (like, heart, pray)."""
        if not self.user.group_id:
            return

        # Get feed items first
        response = self.client.get(
            f"/api/v1/messaging/feed/?group={self.user.group_id}",
            headers=self.user.headers,
            name="Get Feed for Reaction"
        )

        if response.status_code == 200:
            items = response.json().get('results', [])
            if items:
                # React to random item
                reaction_data = {
                    "reaction_type": random.choice(['👍', '❤️', '🙏', '🎉'])
                }

                # Note: Actual endpoint will depend on content type
                # This is a simplified version
                self.client.post(
                    "/api/v1/messaging/reactions/",
                    json=reaction_data,
                    headers=self.user.headers,
                    name="Add Reaction"
                )


class BrowsingUser(AuthenticatedUser):
    """
    User who mostly browses content (80% of users).
    Focuses on read operations.
    """

    tasks = {MessagingUserBehavior: 1}
    weight = 8  # 80% of users

    @task(10)
    def view_feed(self):
        """Most common action - view feed."""
        if not self.group_id:
            return

        self.client.get(
            f"/api/v1/messaging/feed/?group={self.group_id}",
            headers=self.headers,
            name="Browse Feed"
        )

    @task(5)
    def view_discussions(self):
        """Browse discussions."""
        if not self.group_id:
            return

        self.client.get(
            f"/api/v1/messaging/discussions/?group={self.group_id}",
            headers=self.headers,
            name="Browse Discussions"
        )


class ActiveUser(AuthenticatedUser):
    """
    User who actively posts content (20% of users).
    Balanced read/write operations.
    """

    tasks = {MessagingUserBehavior: 1}
    weight = 2  # 20% of users

    @task(5)
    def create_content(self):
        """Actively create content."""
        if not self.group_id:
            return

        # Randomly create different content types
        content_type = random.choice(
            ['discussion', 'prayer', 'testimony', 'scripture'])

        if content_type == 'discussion':
            data = {
                "group": self.group_id,
                "title": fake.sentence(nb_words=5),
                "category": "spiritual_growth",
                "content": fake.paragraph(nb_sentences=3)
            }
            self.client.post(
                "/api/v1/messaging/discussions/",
                json=data,
                headers=self.headers,
                name="Create Discussion"
            )
        elif content_type == 'prayer':
            data = {
                "group": self.group_id,
                "title": f"Prayer - {fake.sentence(nb_words=4)}",
                "description": fake.paragraph(nb_sentences=2),
                "prayer_type": "personal",
                "urgency_level": "normal"
            }
            self.client.post(
                "/api/v1/messaging/prayer-requests/",
                json=data,
                headers=self.headers,
                name="Create Prayer"
            )


class HealthCheckUser(HttpUser):
    """
    Simulates monitoring/health check pings.
    """

    wait_time = between(10, 30)  # Less frequent
    weight = 1  # Very few of these

    @task
    def health_check(self):
        """Ping health endpoint."""
        self.client.get("/api/v1/auth/health/", name="Health Check")
