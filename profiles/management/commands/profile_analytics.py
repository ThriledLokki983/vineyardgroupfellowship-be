"""
Django management command to generate profile analytics and reports.

Provides insights into profile completion rates, photo moderation metrics,
user engagement, and other operational analytics.

Usage:
    python manage.py profile_analytics --completion-report
    python manage.py profile_analytics --moderation-report
    python manage.py profile_analytics --user-engagement
    python manage.py profile_analytics --all-reports
"""

from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncDate

from profiles.models import (
    UserProfileBasic,
    ProfilePhoto,
    ProfileCompletenessTracker
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate profile analytics and reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--completion-report',
            action='store_true',
            dest='completion_report',
            help='Generate profile completion analytics',
        )
        parser.add_argument(
            '--moderation-report',
            action='store_true',
            dest='moderation_report',
            help='Generate photo moderation analytics',
        )
        parser.add_argument(
            '--user-engagement',
            action='store_true',
            dest='user_engagement',
            help='Generate user engagement analytics',
        )
        parser.add_argument(
            '--all-reports',
            action='store_true',
            dest='all_reports',
            help='Generate all available reports',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            dest='days',
            help='Number of days to include in reports (default: 30)',
        )
        parser.add_argument(
            '--output-format',
            choices=['text', 'json', 'csv'],
            default='text',
            dest='output_format',
            help='Output format for reports (default: text)',
        )

    def handle(self, *args, **options):
        self.days = options['days']
        self.output_format = options['output_format']

        self.stdout.write(
            self.style.SUCCESS(
                f"Generating profile analytics for last {self.days} days"
            )
        )

        if options['all_reports']:
            self._generate_completion_report()
            self.stdout.write("")
            self._generate_moderation_report()
            self.stdout.write("")
            self._generate_user_engagement_report()
        else:
            if options['completion_report']:
                self._generate_completion_report()

            if options['moderation_report']:
                self._generate_moderation_report()

            if options['user_engagement']:
                self._generate_user_engagement_report()

            if not any([
                options['completion_report'],
                options['moderation_report'],
                options['user_engagement']
            ]):
                self.stdout.write(
                    self.style.ERROR(
                        "No report specified. Use --completion-report, "
                        "--moderation-report, --user-engagement, or --all-reports"
                    )
                )

    def _generate_completion_report(self):
        """Generate profile completion analytics."""
        self.stdout.write(self.style.SUCCESS("Profile Completion Report"))
        self.stdout.write("=" * 50)

        # Total profiles
        total_profiles = UserProfileBasic.objects.count()

        # Completion percentage distribution
        completion_stats = ProfileCompletenessTracker.objects.aggregate(
            avg_completion=Avg('current_percentage'),
            total_tracked=Count('id')
        )

        # Completion level distribution
        completion_levels = self._get_completion_level_distribution()

        # Recent profile creation
        cutoff_date = timezone.now() - timedelta(days=self.days)
        recent_profiles = UserProfileBasic.objects.filter(
            created_at__gte=cutoff_date
        ).count()

        # Profiles with photos
        profiles_with_photos = UserProfileBasic.objects.filter(
            user__profilephoto__isnull=False
        ).count()

        # Display results
        self.stdout.write(f"Total profiles: {total_profiles}")
        self.stdout.write(
            f"Profiles with completion tracking: {completion_stats['total_tracked']}")
        self.stdout.write(
            f"Average completion: {completion_stats['avg_completion']:.1f}%")
        self.stdout.write(
            f"Profiles created in last {self.days} days: {recent_profiles}")
        self.stdout.write(
            f"Profiles with photos: {profiles_with_photos} ({profiles_with_photos/total_profiles*100:.1f}%)")

        self.stdout.write("\nCompletion Level Distribution:")
        for level, count in completion_levels.items():
            percentage = count / \
                completion_stats['total_tracked'] * \
                100 if completion_stats['total_tracked'] > 0 else 0
            self.stdout.write(
                f"  {level.title()}: {count} ({percentage:.1f}%)")

        # Daily completion trend
        self.stdout.write(
            f"\nProfile Creation Trend (Last {min(self.days, 14)} days):")
        self._show_daily_profile_creation_trend()

    def _generate_moderation_report(self):
        """Generate photo moderation analytics."""
        self.stdout.write(self.style.SUCCESS("Photo Moderation Report"))
        self.stdout.write("=" * 50)

        # Total photos
        total_photos = ProfilePhoto.objects.count()

        # Moderation status distribution
        moderation_stats = ProfilePhoto.objects.values('moderation_status').annotate(
            count=Count('id')
        ).order_by('moderation_status')

        # Recent uploads
        cutoff_date = timezone.now() - timedelta(days=self.days)
        recent_uploads = ProfilePhoto.objects.filter(
            uploaded_at__gte=cutoff_date
        ).count()

        # Pending moderation time
        pending_photos = ProfilePhoto.objects.filter(
            moderation_status='pending'
        )

        if pending_photos.exists():
            avg_pending_hours = sum(
                (timezone.now() - photo.uploaded_at).total_seconds() / 3600
                for photo in pending_photos
            ) / pending_photos.count()
        else:
            avg_pending_hours = 0

        # Moderation efficiency
        moderated_in_period = ProfilePhoto.objects.filter(
            moderated_at__gte=cutoff_date,
            is_moderated=True
        ).count()

        # Display results
        self.stdout.write(f"Total photos: {total_photos}")
        self.stdout.write(
            f"Photos uploaded in last {self.days} days: {recent_uploads}")
        self.stdout.write(
            f"Photos moderated in last {self.days} days: {moderated_in_period}")
        self.stdout.write(
            f"Average pending time: {avg_pending_hours:.1f} hours")

        self.stdout.write("\nModeration Status Distribution:")
        for stat in moderation_stats:
            status = stat['moderation_status']
            count = stat['count']
            percentage = count / total_photos * 100 if total_photos > 0 else 0
            self.stdout.write(
                f"  {status.title()}: {count} ({percentage:.1f}%)")

        # Show pending photos by age
        if pending_photos.exists():
            self.stdout.write("\nPending Photos by Age:")
            age_buckets = self._get_pending_photos_by_age()
            for bucket, count in age_buckets.items():
                self.stdout.write(f"  {bucket}: {count} photos")

    def _generate_user_engagement_report(self):
        """Generate user engagement analytics."""
        self.stdout.write(self.style.SUCCESS("User Engagement Report"))
        self.stdout.write("=" * 50)

        cutoff_date = timezone.now() - timedelta(days=self.days)

        # Profile updates
        recent_profile_updates = UserProfileBasic.objects.filter(
            updated_at__gte=cutoff_date
        ).count()

        # Photo uploads
        recent_photo_uploads = ProfilePhoto.objects.filter(
            uploaded_at__gte=cutoff_date
        ).count()

        # Users with recent activity
        active_users = User.objects.filter(
            Q(userprofilebasic__updated_at__gte=cutoff_date) |
            Q(profilephoto__uploaded_at__gte=cutoff_date)
        ).distinct().count()

        # Completion improvements
        improved_completeness = ProfileCompletenessTracker.objects.filter(
            last_calculated__gte=cutoff_date,
            current_percentage__gt=50  # Assuming improvement if > 50%
        ).count()

        # Display results
        self.stdout.write(
            f"Active users in last {self.days} days: {active_users}")
        self.stdout.write(f"Profile updates: {recent_profile_updates}")
        self.stdout.write(f"Photo uploads: {recent_photo_uploads}")
        self.stdout.write(
            f"Users with completion improvements: {improved_completeness}")

        # Activity by day
        self.stdout.write(
            f"\nDaily Activity Trend (Last {min(self.days, 14)} days):")
        self._show_daily_activity_trend()

    def _get_completion_level_distribution(self):
        """Get distribution of completion levels."""
        trackers = ProfileCompletenessTracker.objects.all()

        levels = {
            'beginner': 0,
            'intermediate': 0,
            'advanced': 0,
            'expert': 0
        }

        for tracker in trackers:
            percentage = tracker.current_percentage
            if percentage < 25:
                levels['beginner'] += 1
            elif percentage < 50:
                levels['intermediate'] += 1
            elif percentage < 80:
                levels['advanced'] += 1
            else:
                levels['expert'] += 1

        return levels

    def _get_pending_photos_by_age(self):
        """Get pending photos grouped by age."""
        pending_photos = ProfilePhoto.objects.filter(
            moderation_status='pending')

        buckets = {
            'Less than 1 hour': 0,
            '1-6 hours': 0,
            '6-24 hours': 0,
            '1-3 days': 0,
            'More than 3 days': 0
        }

        now = timezone.now()

        for photo in pending_photos:
            age_hours = (now - photo.uploaded_at).total_seconds() / 3600

            if age_hours < 1:
                buckets['Less than 1 hour'] += 1
            elif age_hours < 6:
                buckets['1-6 hours'] += 1
            elif age_hours < 24:
                buckets['6-24 hours'] += 1
            elif age_hours < 72:
                buckets['1-3 days'] += 1
            else:
                buckets['More than 3 days'] += 1

        return buckets

    def _show_daily_profile_creation_trend(self):
        """Show daily profile creation trend."""
        days_to_show = min(self.days, 14)

        for i in range(days_to_show):
            date = timezone.now().date() - timedelta(days=i)
            count = UserProfileBasic.objects.filter(
                created_at__date=date
            ).count()

            self.stdout.write(f"  {date}: {count} profiles")

    def _show_daily_activity_trend(self):
        """Show daily activity trend."""
        days_to_show = min(self.days, 14)

        for i in range(days_to_show):
            date = timezone.now().date() - timedelta(days=i)

            profile_updates = UserProfileBasic.objects.filter(
                updated_at__date=date
            ).count()

            photo_uploads = ProfilePhoto.objects.filter(
                uploaded_at__date=date
            ).count()

            total_activity = profile_updates + photo_uploads

            self.stdout.write(
                f"  {date}: {total_activity} activities ({profile_updates} profile updates, {photo_uploads} photo uploads)")
