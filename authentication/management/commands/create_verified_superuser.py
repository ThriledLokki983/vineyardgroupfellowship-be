"""
Management command to create admin user with proper verification.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
import getpass

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a verified superuser for authentication testing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address for the superuser',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Username for the superuser',
        )

    def handle(self, *args, **options):
        email = options['email']
        username = options['username']

        if not email:
            email = input('Email: ')

        if not username:
            username = input('Username: ')

        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'User with email {email} already exists.')
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.ERROR(
                    f'User with username {username} already exists.')
            )
            return

        password = getpass.getpass('Password: ')
        password_confirm = getpass.getpass('Password (again): ')

        if password != password_confirm:
            self.stdout.write(
                self.style.ERROR('Passwords do not match.')
            )
            return

        # Create verified superuser
        user = User.objects.create_superuser(
            email=email,
            username=username,
            password=password,
            first_name='Admin',
            last_name='User'
        )

        # Mark as email verified
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created verified superuser: {email}'
            )
        )
