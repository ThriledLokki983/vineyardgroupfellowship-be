"""
Management command to clean up expired tokens and sessions.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from authentication.models import (
    TokenBlacklist, EmailVerificationToken, PasswordResetToken, UserSession
)


class Command(BaseCommand):
    help = 'Clean up expired authentication tokens and inactive sessions.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()

        # Clean up expired blacklisted tokens
        expired_blacklist = TokenBlacklist.objects.filter(expires_at__lt=now)
        blacklist_count = expired_blacklist.count()

        # Clean up expired email verification tokens
        expired_email_tokens = EmailVerificationToken.objects.filter(
            expires_at__lt=now)
        email_token_count = expired_email_tokens.count()

        # Clean up expired password reset tokens
        expired_password_tokens = PasswordResetToken.objects.filter(
            expires_at__lt=now)
        password_token_count = expired_password_tokens.count()

        # Clean up inactive sessions older than 30 days
        inactive_sessions = UserSession.objects.filter(
            is_active=False,
            terminated_at__lt=now - timezone.timedelta(days=30)
        )
        session_count = inactive_sessions.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN - Would delete:')
            )
            self.stdout.write(
                f'  - {blacklist_count} expired blacklisted tokens')
            self.stdout.write(
                f'  - {email_token_count} expired email verification tokens')
            self.stdout.write(
                f'  - {password_token_count} expired password reset tokens')
            self.stdout.write(f'  - {session_count} old inactive sessions')
        else:
            expired_blacklist.delete()
            expired_email_tokens.delete()
            expired_password_tokens.delete()
            inactive_sessions.delete()

            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleaned up:')
            )
            self.stdout.write(
                f'  - {blacklist_count} expired blacklisted tokens')
            self.stdout.write(
                f'  - {email_token_count} expired email verification tokens')
            self.stdout.write(
                f'  - {password_token_count} expired password reset tokens')
            self.stdout.write(f'  - {session_count} old inactive sessions')
