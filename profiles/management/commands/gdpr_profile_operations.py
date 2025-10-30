"""
Django management command for GDPR compliance operations.

Handles data export, deletion, and privacy compliance tasks for user profiles.
Supports batch operations and audit logging for compliance tracking.

Usage:
    python manage.py gdpr_profile_operations --export-user user@example.com
    python manage.py gdpr_profile_operations --delete-user user@example.com
    python manage.py gdpr_profile_operations --audit-exports
    python manage.py gdpr_profile_operations --cleanup-anonymized --older-than-days 90
"""

import json
import os
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from profiles.models import (
    UserProfileBasic,
    ProfilePhoto,
    ProfileCompletenessTracker
)
from profiles.services import ProfileService

User = get_user_model()


class Command(BaseCommand):
    help = 'Handle GDPR compliance operations for user profiles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--export-user',
            type=str,
            dest='export_user_email',
            help='Export all profile data for specific user email',
        )
        parser.add_argument(
            '--delete-user',
            type=str,
            dest='delete_user_email',
            help='Delete all profile data for specific user email',
        )
        parser.add_argument(
            '--export-all-users',
            action='store_true',
            dest='export_all_users',
            help='Export profile data for all users (use with caution)',
        )
        parser.add_argument(
            '--audit-exports',
            action='store_true',
            dest='audit_exports',
            help='Show audit log of data exports',
        )
        parser.add_argument(
            '--cleanup-anonymized',
            action='store_true',
            dest='cleanup_anonymized',
            help='Clean up old anonymized profile data',
        )
        parser.add_argument(
            '--older-than-days',
            type=int,
            default=90,
            dest='older_than_days',
            help='Only process records older than this many days (default: 90)',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='/tmp/gdpr_exports',
            dest='output_dir',
            help='Directory to save export files (default: /tmp/gdpr_exports)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what would be processed without actually processing',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.output_dir = options['output_dir']
        self.older_than_days = options['older_than_days']

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting GDPR profile operations "
                f"{'(DRY RUN)' if self.dry_run else ''}"
            )
        )

        # Ensure output directory exists
        if not self.dry_run and not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Process requested operation
        if options['export_user_email']:
            self._export_user_data(options['export_user_email'])
        elif options['delete_user_email']:
            self._delete_user_data(options['delete_user_email'])
        elif options['export_all_users']:
            self._export_all_users_data()
        elif options['audit_exports']:
            self._audit_exports()
        elif options['cleanup_anonymized']:
            self._cleanup_anonymized_data()
        else:
            self.stdout.write(
                self.style.ERROR(
                    "No operation specified. Use --export-user, --delete-user, "
                    "--export-all-users, --audit-exports, or --cleanup-anonymized"
                )
            )

    def _export_user_data(self, user_email):
        """Export all profile data for a specific user."""
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            raise CommandError(f"User {user_email} does not exist")

        self.stdout.write(f"Exporting data for user: {user_email}")

        try:
            # Get all user profile data
            export_data = ProfileService.export_user_profile_data(user)

            # Add export metadata
            export_data['export_metadata'] = {
                'exported_at': timezone.now().isoformat(),
                'exported_by': 'gdpr_profile_operations',
                'user_email': user_email,
                'user_id': user.id
            }

            # Generate filename
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"profile_export_{user.id}_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)

            if not self.dry_run:
                # Save export file
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, default=str)

                # Log the export
                self._log_export_operation(user, filepath)

                self.stdout.write(
                    self.style.SUCCESS(f"Data exported to: {filepath}")
                )
            else:
                self.stdout.write(
                    f"[DRY RUN] Would export data to: {filepath}"
                )
                self.stdout.write(f"Export would contain:")
                self.stdout.write(
                    f"  - Profile data: {bool(export_data.get('profile'))}")
                self.stdout.write(
                    f"  - Photos: {len(export_data.get('photos', []))}")
                self.stdout.write(
                    f"  - Completeness history: {bool(export_data.get('completeness_history'))}")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error exporting data for {user_email}: {e}")
            )

    def _delete_user_data(self, user_email):
        """Delete all profile data for a specific user."""
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            raise CommandError(f"User {user_email} does not exist")

        self.stdout.write(f"Deleting profile data for user: {user_email}")

        # Get data counts before deletion
        profile_exists = UserProfileBasic.objects.filter(user=user).exists()
        photo_count = ProfilePhoto.objects.filter(user=user).count()
        tracker_exists = ProfileCompletenessTracker.objects.filter(
            user=user).exists()

        self.stdout.write(f"Data to delete:")
        self.stdout.write(f"  - Profile: {'Yes' if profile_exists else 'No'}")
        self.stdout.write(f"  - Photos: {photo_count}")
        self.stdout.write(
            f"  - Completeness tracker: {'Yes' if tracker_exists else 'No'}")

        if not self.dry_run:
            try:
                with transaction.atomic():
                    ProfileService.delete_user_profile_data(user)

                # Log the deletion
                self._log_deletion_operation(user)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Profile data deleted for user: {user_email}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error deleting data for {user_email}: {e}")
                )
        else:
            self.stdout.write(
                f"[DRY RUN] Would delete all profile data for {user_email}")

    def _export_all_users_data(self):
        """Export profile data for all users."""
        users = User.objects.filter(
            userprofilebasic__isnull=False
        ).select_related('userprofilebasic')

        total_users = users.count()
        self.stdout.write(f"Exporting data for {total_users} users")

        if not self.dry_run:
            # Create timestamp directory
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            batch_dir = os.path.join(
                self.output_dir, f"batch_export_{timestamp}")
            os.makedirs(batch_dir, exist_ok=True)

        exported_count = 0

        for user in users:
            try:
                if not self.dry_run:
                    export_data = ProfileService.export_user_profile_data(user)

                    filename = f"profile_export_{user.id}.json"
                    filepath = os.path.join(batch_dir, filename)

                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, indent=2, default=str)

                exported_count += 1

                if exported_count % 100 == 0:
                    self.stdout.write(
                        f"Exported {exported_count}/{total_users} users...")

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error exporting data for user {user.email}: {e}")
                )

        action = "Would export" if self.dry_run else "Exported"
        self.stdout.write(
            self.style.SUCCESS(f"{action} data for {exported_count} users")
        )

    def _cleanup_anonymized_data(self):
        """Clean up old anonymized profile data."""
        cutoff_date = timezone.now() - timedelta(days=self.older_than_days)

        # Find profiles that were anonymized (display_name contains "Anonymous")
        anonymized_profiles = UserProfileBasic.objects.filter(
            display_name__icontains='anonymous',
            updated_at__lt=cutoff_date
        )

        count = anonymized_profiles.count()
        self.stdout.write(
            f"Found {count} anonymized profiles older than {self.older_than_days} days")

        if not self.dry_run and count > 0:
            with transaction.atomic():
                deleted_count = anonymized_profiles.delete()[0]
                self.stdout.write(
                    f"Cleaned up {deleted_count} anonymized profiles")
        else:
            self.stdout.write(
                f"[DRY RUN] Would clean up {count} anonymized profiles")

    def _audit_exports(self):
        """Show audit log of data exports."""
        # This would integrate with a proper audit logging system
        # For now, show recent export files

        if not os.path.exists(self.output_dir):
            self.stdout.write("No export directory found")
            return

        export_files = []
        for file in os.listdir(self.output_dir):
            if file.startswith('profile_export_') and file.endswith('.json'):
                filepath = os.path.join(self.output_dir, file)
                stat = os.stat(filepath)
                export_files.append({
                    'filename': file,
                    'created': datetime.fromtimestamp(stat.st_mtime),
                    'size': stat.st_size
                })

        export_files.sort(key=lambda x: x['created'], reverse=True)

        self.stdout.write(
            f"\nRecent profile data exports ({len(export_files)} files):\n")

        for export_file in export_files[:20]:  # Show last 20
            self.stdout.write(
                f"{export_file['filename']} | "
                f"Created: {export_file['created'].strftime('%Y-%m-%d %H:%M')} | "
                f"Size: {export_file['size']} bytes"
            )

    def _log_export_operation(self, user, filepath):
        """Log data export operation."""
        # This would integrate with proper audit logging system
        log_entry = {
            'operation': 'profile_data_export',
            'user_id': user.id,
            'user_email': user.email,
            'filepath': filepath,
            'timestamp': timezone.now().isoformat()
        }

        # For now, just log to stdout
        self.stdout.write(
            f"AUDIT: Exported profile data for user {user.email}")

    def _log_deletion_operation(self, user):
        """Log data deletion operation."""
        # This would integrate with proper audit logging system
        log_entry = {
            'operation': 'profile_data_deletion',
            'user_id': user.id,
            'user_email': user.email,
            'timestamp': timezone.now().isoformat()
        }

        # For now, just log to stdout
        self.stdout.write(f"AUDIT: Deleted profile data for user {user.email}")
