"""
Django management command to create an admin user.

Usage:
    python manage.py create_admin_user --email admin@example.com --password mypassword

Or use environment variables:
    ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=mypassword python manage.py create_admin_user
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from decouple import config
import getpass

User = get_user_model()


class Command(BaseCommand):
    help = 'Create an admin user for production deployment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Admin user email address',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Admin user password',
        )
        parser.add_argument(
            '--skip-if-exists',
            action='store_true',
            help='Skip creation if user already exists',
        )

    def handle(self, *args, **options):
        # Get email from argument, environment variable, or prompt
        email = (
            options.get('email') or
            config('ADMIN_EMAIL', default='') or
            input('Enter admin email: ')
        )

        if not email:
            self.stdout.write(
                self.style.ERROR('Email is required')
            )
            return

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            if options.get('skip_if_exists'):
                self.stdout.write(
                    self.style.WARNING(
                        f'Admin user with email {email} already exists. Skipping.')
                )
                return
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'User with email {email} already exists!')
                )
                return

        # Get password from argument, environment variable, or prompt
        password = (
            options.get('password') or
            config('ADMIN_PASSWORD', default='')
        )

        if not password:
            password = getpass.getpass('Enter admin password: ')
            password_confirm = getpass.getpass('Confirm admin password: ')

            if password != password_confirm:
                self.stdout.write(
                    self.style.ERROR('Passwords do not match!')
                )
                return

        if not password:
            self.stdout.write(
                self.style.ERROR('Password is required')
            )
            return

        # Create the admin user
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    is_staff=True,
                    is_superuser=True,
                    is_verified=True,  # Skip email verification for admin
                )

                # Create user profile if it doesn't exist
                from profiles.models import UserProfileBasic
                profile, created = UserProfileBasic.objects.get_or_create(
                    user=user,
                    defaults={
                        'display_name': 'Admin User',
                        'bio': 'System Administrator',
                    }
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Admin user created successfully!\n'
                        f'   Email: {email}\n'
                        f'   Profile: {"Created" if created else "Already exists"}\n'
                        f'   Permissions: Staff + Superuser\n'
                        f'   Status: Email verified'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating admin user: {str(e)}')
            )
