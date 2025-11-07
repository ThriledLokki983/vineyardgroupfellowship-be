"""
Management command to geocode groups and user profiles.

This command geocodes all groups and user profiles that have location
information but no coordinates yet.
"""

import time
from django.core.management.base import BaseCommand
from django.db.models import Q
from group.models import Group
from profiles.models import UserProfileBasic
from group.utils.distance import geocode_and_save_group, geocode_and_save_profile


class Command(BaseCommand):
    help = 'Geocode groups and user profiles with missing coordinates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-geocoding even if coordinates already exist',
        )
        parser.add_argument(
            '--groups-only',
            action='store_true',
            help='Only geocode groups, skip user profiles',
        )
        parser.add_argument(
            '--profiles-only',
            action='store_true',
            help='Only geocode user profiles, skip groups',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of records to geocode (for testing)',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay between geocoding requests in seconds (default: 1.0)',
        )

    def handle(self, *args, **options):
        force = options['force']
        groups_only = options['groups_only']
        profiles_only = options['profiles_only']
        limit = options['limit']
        delay = options['delay']

        self.stdout.write(self.style.SUCCESS('Starting geocoding process...'))
        self.stdout.write(f'Force: {force}')
        self.stdout.write(f'Delay: {delay}s between requests')

        # Geocode groups
        if not profiles_only:
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.HTTP_INFO('GEOCODING GROUPS'))
            self.stdout.write('='*60)
            self.geocode_groups(force, limit, delay)

        # Geocode user profiles
        if not groups_only:
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.HTTP_INFO('GEOCODING USER PROFILES'))
            self.stdout.write('='*60)
            self.geocode_profiles(force, limit, delay)

        self.stdout.write('\n' + self.style.SUCCESS('Geocoding complete!'))

    def geocode_groups(self, force, limit, delay):
        """Geocode all groups with location but no coordinates."""
        # Build query
        queryset = Group.objects.filter(
            is_active=True,
            archived_at__isnull=True,
        ).exclude(
            location_type='online'  # Skip online-only groups
        ).exclude(
            Q(location__isnull=True) | Q(location='')
        )

        if not force:
            # Only geocode groups without coordinates
            queryset = queryset.filter(
                Q(latitude__isnull=True) | Q(longitude__isnull=True)
            )

        if limit:
            queryset = queryset[:limit]

        total_count = queryset.count()
        self.stdout.write(f'Found {total_count} groups to geocode')

        if total_count == 0:
            self.stdout.write(self.style.WARNING('No groups to geocode'))
            return

        success_count = 0
        fail_count = 0

        for index, group in enumerate(queryset, 1):
            self.stdout.write(
                f'\n[{index}/{total_count}] Geocoding group: {group.name}'
            )
            self.stdout.write(f'  Location: {group.location}')

            try:
                success = geocode_and_save_group(group, force=force)

                if success:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Success: ({group.latitude}, {group.longitude})'
                        )
                    )
                    if group.geocoded_address:
                        self.stdout.write(
                            f'  Address: {group.geocoded_address}')
                else:
                    fail_count += 1
                    self.stdout.write(
                        self.style.ERROR('  ✗ Failed to geocode')
                    )

                # Rate limiting - sleep between requests
                if index < total_count:
                    time.sleep(delay)

            except Exception as e:
                fail_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error: {str(e)}')
                )

        # Summary
        self.stdout.write('\n' + '-'*60)
        self.stdout.write(self.style.SUCCESS(
            f'Groups geocoded: {success_count}/{total_count}'))
        if fail_count > 0:
            self.stdout.write(self.style.ERROR(f'Failed: {fail_count}'))

    def geocode_profiles(self, force, limit, delay):
        """Geocode all user profiles with location but no coordinates."""
        # Build query
        queryset = UserProfileBasic.objects.exclude(
            Q(location__isnull=True) | Q(location='')
        )

        if not force:
            # Only geocode profiles without coordinates
            queryset = queryset.filter(
                Q(latitude__isnull=True) | Q(longitude__isnull=True)
            )

        if limit:
            queryset = queryset[:limit]

        total_count = queryset.count()
        self.stdout.write(f'Found {total_count} user profiles to geocode')

        if total_count == 0:
            self.stdout.write(self.style.WARNING(
                'No user profiles to geocode'))
            return

        success_count = 0
        fail_count = 0

        for index, profile in enumerate(queryset, 1):
            # Build display address
            address_parts = []
            if profile.location:
                address_parts.append(profile.location)
            if profile.post_code:
                address_parts.append(profile.post_code)
            address = ', '.join(address_parts)

            self.stdout.write(
                f'\n[{index}/{total_count}] Geocoding profile: {profile.user.email}'
            )
            self.stdout.write(f'  Location: {address}')

            try:
                success = geocode_and_save_profile(profile, force=force)

                if success:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Success: ({profile.latitude}, {profile.longitude})'
                        )
                    )
                    if profile.geocoded_address:
                        self.stdout.write(
                            f'  Address: {profile.geocoded_address}')
                else:
                    fail_count += 1
                    self.stdout.write(
                        self.style.ERROR('  ✗ Failed to geocode')
                    )

                # Rate limiting - sleep between requests
                if index < total_count:
                    time.sleep(delay)

            except Exception as e:
                fail_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error: {str(e)}')
                )

        # Summary
        self.stdout.write('\n' + '-'*60)
        self.stdout.write(self.style.SUCCESS(
            f'Profiles geocoded: {success_count}/{total_count}'))
        if fail_count > 0:
            self.stdout.write(self.style.ERROR(f'Failed: {fail_count}'))
