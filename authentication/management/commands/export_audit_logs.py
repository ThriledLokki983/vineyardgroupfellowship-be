"""
Management command to export audit logs for security analysis.
"""

import csv
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from authentication.models import AuditLog


class Command(BaseCommand):
    help = 'Export audit logs to CSV for security analysis.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to export (default: 30)',
        )
        parser.add_argument(
            '--output',
            type=str,
            default=f'audit_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv',
            help='Output CSV file name',
        )
        parser.add_argument(
            '--event-type',
            type=str,
            help='Filter by specific event type',
        )
        parser.add_argument(
            '--risk-level',
            type=str,
            choices=['low', 'medium', 'high'],
            help='Filter by risk level',
        )

    def handle(self, *args, **options):
        days = options['days']
        output_file = options['output']
        event_type = options['event_type']
        risk_level = options['risk_level']

        # Build query
        since = timezone.now() - timedelta(days=days)
        logs = AuditLog.objects.filter(
            timestamp__gte=since).order_by('-timestamp')

        if event_type:
            logs = logs.filter(event_type=event_type)

        if risk_level:
            logs = logs.filter(risk_level=risk_level)

        # Export to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'timestamp', 'user_email', 'event_type', 'description',
                'ip_address', 'user_agent', 'success', 'risk_level', 'metadata'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            count = 0
            for log in logs:
                writer.writerow({
                    'timestamp': log.timestamp.isoformat(),
                    'user_email': log.user.email if log.user else 'Anonymous',
                    'event_type': log.event_type,
                    'description': log.description,
                    'ip_address': log.ip_address,
                    'user_agent': log.user_agent,
                    'success': log.success,
                    'risk_level': log.risk_level,
                    'metadata': str(log.metadata) if log.metadata else ''
                })
                count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully exported {count} audit log entries to {output_file}'
            )
        )
