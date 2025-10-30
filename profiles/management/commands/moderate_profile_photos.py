"""
Django management command to moderate profile photos in batch.

Lists pending photos for moderation and allows batch approval/rejection.
Useful for moderators to efficiently process photo moderation queues.

Usage:
    python manage.py moderate_profile_photos
    python manage.py moderate_profile_photos --auto-approve-safe
    python manage.py moderate_profile_photos --list-pending
    python manage.py moderate_profile_photos --approve-all --moderator admin@example.com
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from profiles.models import ProfilePhoto
from profiles.services import PhotoService

User = get_user_model()


class Command(BaseCommand):
    help = 'Moderate profile photos in batch'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list-pending',
            action='store_true',
            dest='list_pending',
            help='List all pending photos without moderation actions',
        )
        parser.add_argument(
            '--approve-all',
            action='store_true',
            dest='approve_all',
            help='Approve all pending photos (use with caution)',
        )
        parser.add_argument(
            '--reject-all',
            action='store_true',
            dest='reject_all',
            help='Reject all pending photos (use with caution)',
        )
        parser.add_argument(
            '--auto-approve-safe',
            action='store_true',
            dest='auto_approve_safe',
            help='Auto-approve photos from users with good history',
        )
        parser.add_argument(
            '--moderator',
            type=str,
            dest='moderator_email',
            help='Email of moderator performing the action',
        )
        parser.add_argument(
            '--older-than-hours',
            type=int,
            default=0,
            dest='older_than_hours',
            help='Only process photos older than this many hours',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            dest='batch_size',
            help='Process photos in batches of this size (default: 50)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what would be moderated without actually moderating',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.batch_size = options['batch_size']

        if options['list_pending']:
            self._list_pending_photos(options)
            return

        # Validate moderator
        moderator_email = options.get('moderator_email')
        if not moderator_email and not self.dry_run:
            raise CommandError(
                "--moderator email is required for moderation actions")

        if moderator_email:
            try:
                moderator = User.objects.get(email=moderator_email)
                if not moderator.is_staff:
                    raise CommandError(
                        f"User {moderator_email} is not staff/moderator")
            except User.DoesNotExist:
                raise CommandError(
                    f"Moderator {moderator_email} does not exist")
        else:
            moderator = None

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting photo moderation "
                f"{'(DRY RUN)' if self.dry_run else ''}"
            )
        )

        # Get pending photos
        pending_photos = self._get_pending_photos(options)
        total_photos = pending_photos.count()

        if total_photos == 0:
            self.stdout.write("No pending photos found")
            return

        self.stdout.write(f"Found {total_photos} pending photos")

        # Perform moderation action
        if options['approve_all']:
            moderated_count = self._moderate_all_photos(
                pending_photos, 'approved', moderator, "Batch approved"
            )
        elif options['reject_all']:
            moderated_count = self._moderate_all_photos(
                pending_photos, 'rejected', moderator, "Batch rejected"
            )
        elif options['auto_approve_safe']:
            moderated_count = self._auto_approve_safe_photos(
                pending_photos, moderator)
        else:
            self.stdout.write(
                self.style.ERROR(
                    "No moderation action specified. Use --approve-all, --reject-all, "
                    "or --auto-approve-safe"
                )
            )
            return

        action = "Would moderate" if self.dry_run else "Moderated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {moderated_count}/{total_photos} photos"
            )
        )

    def _get_pending_photos(self, options):
        """Get queryset of pending photos to process."""
        queryset = ProfilePhoto.objects.filter(
            moderation_status='pending'
        ).select_related('user')

        # Filter by age if specified
        if options['older_than_hours'] > 0:
            from datetime import timedelta
            cutoff_time = timezone.now() - \
                timedelta(hours=options['older_than_hours'])
            queryset = queryset.filter(uploaded_at__lt=cutoff_time)

        return queryset.order_by('uploaded_at')

    def _list_pending_photos(self, options):
        """List all pending photos with details."""
        pending_photos = self._get_pending_photos(options)

        self.stdout.write(
            f"\nFound {pending_photos.count()} pending photos:\n")

        for photo in pending_photos:
            user = photo.user
            days_pending = (timezone.now() - photo.uploaded_at).days

            self.stdout.write(
                f"Photo ID: {photo.id} | "
                f"User: {user.email} | "
                f"Uploaded: {photo.uploaded_at.strftime('%Y-%m-%d %H:%M')} | "
                f"Days pending: {days_pending}"
            )

        self.stdout.write("")

    def _moderate_all_photos(self, photos, status, moderator, notes):
        """Moderate all photos with the same status."""
        moderated_count = 0

        # Process in batches
        for i in range(0, photos.count(), self.batch_size):
            batch = photos[i:i + self.batch_size]

            for photo in batch:
                if self._moderate_single_photo(photo, status, moderator, notes):
                    moderated_count += 1

        return moderated_count

    def _auto_approve_safe_photos(self, photos, moderator):
        """Auto-approve photos from users with good moderation history."""
        moderated_count = 0

        for photo in photos:
            if self._is_user_safe_for_auto_approval(photo.user):
                if self._moderate_single_photo(
                    photo, 'approved', moderator, "Auto-approved: good history"
                ):
                    moderated_count += 1

        return moderated_count

    def _is_user_safe_for_auto_approval(self, user):
        """Check if user has good moderation history for auto-approval."""
        # Get user's photo history
        user_photos = ProfilePhoto.objects.filter(
            user=user,
            is_moderated=True
        ).exclude(moderation_status='pending')

        total_photos = user_photos.count()

        # If user has no history, don't auto-approve
        if total_photos == 0:
            return False

        # If user has less than 3 photos, require manual review
        if total_photos < 3:
            return False

        # Check rejection rate
        rejected_count = user_photos.filter(
            moderation_status='rejected').count()
        rejection_rate = rejected_count / total_photos

        # Auto-approve if rejection rate is less than 10%
        return rejection_rate < 0.1

    def _moderate_single_photo(self, photo, status, moderator, notes):
        """Moderate a single photo."""
        try:
            if not self.dry_run:
                with transaction.atomic():
                    photo.moderation_status = status
                    photo.is_moderated = True
                    photo.moderated_at = timezone.now()
                    photo.moderated_by = moderator.email if moderator else 'system'
                    photo.moderation_notes = notes
                    photo.save()

            self.stdout.write(
                f"{'[DRY RUN] Would moderate' if self.dry_run else 'Moderated'} "
                f"photo {photo.id} for {photo.user.email}: {status}"
            )

            return True

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error moderating photo {photo.id}: {e}"
                )
            )
            return False
