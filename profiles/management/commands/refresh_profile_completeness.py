"""
Django management command to refresh profile completeness calculations.

Recalculates profile completeness for all users or specific users.
Useful for updating completeness after changing completion criteria.

Usage:
    python manage.py refresh_profile_completeness
    python manage.py refresh_profile_completeness --user-id 123
    python manage.py refresh_profile_completeness --incomplete-only
    python manage.py refresh_profile_completeness --reset-all
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from profiles.models import (
    UserProfileBasic,
    ProfileCompletenessTracker
)
from profiles.services import ProfileCompletenessService

User = get_user_model()


class Command(BaseCommand):
    help = 'Refresh profile completeness calculations for users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            dest='user_id',
            help='Refresh completeness for specific user ID only',
        )
        parser.add_argument(
            '--email',
            type=str,
            dest='email',
            help='Refresh completeness for specific user email only',
        )
        parser.add_argument(
            '--incomplete-only',
            action='store_true',
            dest='incomplete_only',
            help='Only refresh users with completeness < 100%',
        )
        parser.add_argument(
            '--reset-all',
            action='store_true',
            dest='reset_all',
            help='Reset all completeness trackers before recalculating',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            dest='batch_size',
            help='Process users in batches of this size (default: 100)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what would be updated without actually updating',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.batch_size = options['batch_size']

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting profile completeness refresh "
                f"{'(DRY RUN)' if self.dry_run else ''}"
            )
        )

        # Reset trackers if requested
        if options['reset_all']:
            self._reset_completeness_trackers()

        # Get users to process
        users_queryset = self._get_users_queryset(options)
        total_users = users_queryset.count()

        self.stdout.write(f"Processing {total_users} users...")

        processed_count = 0
        updated_count = 0

        # Process users in batches
        for i in range(0, total_users, self.batch_size):
            batch = users_queryset[i:i + self.batch_size]

            for user in batch:
                if self._refresh_user_completeness(user):
                    updated_count += 1
                processed_count += 1

                if processed_count % 50 == 0:
                    self.stdout.write(
                        f"Processed {processed_count}/{total_users} users...")

        action = "Would update" if self.dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} completeness for {updated_count}/{processed_count} users"
            )
        )

    def _get_users_queryset(self, options):
        """Get the queryset of users to process."""
        queryset = User.objects.all()

        # Filter by specific user
        if options['user_id']:
            try:
                user = User.objects.get(id=options['user_id'])
                return User.objects.filter(id=user.id)
            except User.DoesNotExist:
                raise CommandError(
                    f"User with ID {options['user_id']} does not exist")

        if options['email']:
            try:
                user = User.objects.get(email=options['email'])
                return User.objects.filter(id=user.id)
            except User.DoesNotExist:
                raise CommandError(
                    f"User with email {options['email']} does not exist")

        # Filter by incomplete profiles only
        if options['incomplete_only']:
            incomplete_tracker_ids = ProfileCompletenessTracker.objects.filter(
                current_percentage__lt=100
            ).values_list('user_id', flat=True)

            queryset = queryset.filter(
                id__in=incomplete_tracker_ids
            )

        # Only include users who have profiles
        queryset = queryset.filter(
            userprofilebasic__isnull=False
        ).select_related('userprofilebasic')

        return queryset

    def _reset_completeness_trackers(self):
        """Reset all completeness trackers."""
        if self.dry_run:
            count = ProfileCompletenessTracker.objects.count()
            self.stdout.write(
                f"[DRY RUN] Would reset {count} completeness trackers")
        else:
            with transaction.atomic():
                count = ProfileCompletenessTracker.objects.all().delete()[0]
                self.stdout.write(f"Reset {count} completeness trackers")

    def _refresh_user_completeness(self, user):
        """Refresh completeness for a single user."""
        try:
            # Calculate new completeness
            old_completeness = self._get_current_completeness(user)
            new_completeness = ProfileCompletenessService.calculate_completeness(
                user)

            # Check if update is needed
            if old_completeness and old_completeness == new_completeness['overall_percentage']:
                return False  # No change needed

            if not self.dry_run:
                # Update the tracker
                ProfileCompletenessService.update_completeness_tracker(user)

            self.stdout.write(
                f"{'[DRY RUN] Would update' if self.dry_run else 'Updated'} "
                f"user {user.email}: "
                f"{old_completeness or 0}% → {new_completeness['overall_percentage']}%"
            )

            return True

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error refreshing completeness for user {user.email}: {e}"
                )
            )
            return False

    def _get_current_completeness(self, user):
        """Get current completeness percentage for user."""
        try:
            tracker = ProfileCompletenessTracker.objects.get(user=user)
            return tracker.current_percentage
        except ProfileCompletenessTracker.DoesNotExist:
            return None
