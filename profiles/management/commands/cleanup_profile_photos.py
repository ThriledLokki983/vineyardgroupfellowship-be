"""
Django management command to clean up orphaned photo files.

Removes photo files from storage that no longer have corresponding database records.
Also handles moderated photos that were rejected and should be cleaned up.

Usage:
    python manage.py cleanup_profile_photos
    python manage.py cleanup_profile_photos --dry-run
    python manage.py cleanup_profile_photos --rejected-only
"""

import os
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from profiles.models import ProfilePhoto


class Command(BaseCommand):
    help = 'Clean up orphaned profile photo files and rejected photos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--rejected-only',
            action='store_true',
            dest='rejected_only',
            help='Only clean up photos that were rejected during moderation',
        )
        parser.add_argument(
            '--older-than-days',
            type=int,
            default=7,
            dest='older_than_days',
            help='Only delete rejected photos older than this many days (default: 7)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            dest='batch_size',
            help='Process files in batches of this size (default: 100)',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.rejected_only = options['rejected_only']
        self.older_than_days = options['older_than_days']
        self.batch_size = options['batch_size']

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting profile photo cleanup "
                f"{'(DRY RUN)' if self.dry_run else ''}"
            )
        )

        total_deleted = 0

        if self.rejected_only:
            total_deleted += self._cleanup_rejected_photos()
        else:
            total_deleted += self._cleanup_orphaned_files()
            total_deleted += self._cleanup_rejected_photos()

        action = "Would delete" if self.dry_run else "Deleted"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {total_deleted} photo files"
            )
        )

    def _cleanup_orphaned_files(self):
        """Clean up files that exist in storage but not in database."""
        self.stdout.write("Scanning for orphaned photo files...")

        orphaned_files = []

        try:
            # Get all photo directories
            photo_dirs = ['photos/', 'photos/thumbnails/']

            for photo_dir in photo_dirs:
                if default_storage.exists(photo_dir):
                    dirs, files = default_storage.listdir(photo_dir)

                    for filename in files:
                        file_path = os.path.join(photo_dir, filename)

                        # Check if file has corresponding database record
                        if not self._file_has_db_record(file_path):
                            orphaned_files.append(file_path)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error scanning storage: {e}")
            )
            return 0

        self.stdout.write(f"Found {len(orphaned_files)} orphaned files")

        deleted_count = 0

        # Process in batches
        for i in range(0, len(orphaned_files), self.batch_size):
            batch = orphaned_files[i:i + self.batch_size]

            for file_path in batch:
                if self._delete_file(file_path):
                    deleted_count += 1

        return deleted_count

    def _cleanup_rejected_photos(self):
        """Clean up photos that were rejected during moderation."""
        cutoff_date = timezone.now() - timedelta(days=self.older_than_days)

        rejected_photos = ProfilePhoto.objects.filter(
            moderation_status='rejected',
            moderated_at__lt=cutoff_date
        )

        count = rejected_photos.count()
        self.stdout.write(
            f"Found {count} rejected photos older than {self.older_than_days} days")

        deleted_count = 0

        # Process in batches
        for i in range(0, count, self.batch_size):
            batch = rejected_photos[i:i + self.batch_size]

            for photo in batch:
                if self._delete_photo_record_and_files(photo):
                    deleted_count += 1

        return deleted_count

    def _file_has_db_record(self, file_path):
        """Check if a file path corresponds to a database record."""
        # Extract filename from path
        filename = os.path.basename(file_path)

        # Check if any ProfilePhoto has this file
        return ProfilePhoto.objects.filter(
            photo__icontains=filename
        ).exists() or ProfilePhoto.objects.filter(
            thumbnail__icontains=filename
        ).exists()

    def _delete_file(self, file_path):
        """Delete a single file from storage."""
        try:
            if not self.dry_run:
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)

            self.stdout.write(
                f"{'[DRY RUN] Would delete' if self.dry_run else 'Deleted'}: {file_path}")
            return True

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error deleting {file_path}: {e}")
            )
            return False

    def _delete_photo_record_and_files(self, photo):
        """Delete a ProfilePhoto record and its associated files."""
        try:
            photo_path = photo.photo.name if photo.photo else None
            thumbnail_path = photo.thumbnail.name if photo.thumbnail else None

            if not self.dry_run:
                with transaction.atomic():
                    # Delete files from storage
                    if photo_path and default_storage.exists(photo_path):
                        default_storage.delete(photo_path)

                    if thumbnail_path and default_storage.exists(thumbnail_path):
                        default_storage.delete(thumbnail_path)

                    # Delete database record
                    photo.delete()

            self.stdout.write(
                f"{'[DRY RUN] Would delete' if self.dry_run else 'Deleted'} "
                f"rejected photo for user {photo.user.email}"
            )
            return True

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error deleting photo {photo.id}: {e}"
                )
            )
            return False
