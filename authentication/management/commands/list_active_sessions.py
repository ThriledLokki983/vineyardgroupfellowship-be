from django.core.management.base import BaseCommand
from authentication.models import UserSession


class Command(BaseCommand):
    help = 'List all active user sessions.'

    def handle(self, *args, **options):
        sessions = UserSession.objects.filter(is_active=True)
        if not sessions.exists():
            self.stdout.write(self.style.WARNING('No active sessions found.'))
            return
        for session in sessions:
            self.stdout.write(
                f"User: {session.user.email} | Device: {session.device_type} | IP: {session.ip_address} | Last Activity: {session.last_activity}")
