from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Manually create SystemSetting table and populate with defaults'

    def handle(self, *args, **options):
        """Manually create the SystemSetting table and populate it."""

        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = 'core_systemsetting'
            """)
            table_exists = cursor.fetchone()[0] > 0

            if table_exists:
                self.stdout.write(
                    self.style.SUCCESS('SystemSetting table already exists')
                )
            else:
                # Create the table manually
                self.stdout.write('Creating SystemSetting table manually...')
                cursor.execute("""
                    CREATE TABLE core_systemsetting (
                        id SERIAL PRIMARY KEY,
                        key VARCHAR(100) NOT NULL UNIQUE,
                        value TEXT NOT NULL,
                        setting_type VARCHAR(20) NOT NULL DEFAULT 'string',
                        category VARCHAR(50) NOT NULL DEFAULT 'general',
                        description TEXT,
                        environment_restriction VARCHAR(20),
                        is_active BOOLEAN NOT NULL DEFAULT true,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        created_by_id INTEGER,
                        updated_by_id INTEGER
                    )
                """)
                self.stdout.write(
                    self.style.SUCCESS('SystemSetting table created successfully')
                )

        # Now run the default settings setup
        from django.core.management import call_command
        self.stdout.write('Setting up default system settings...')
        call_command('setup_default_settings')
        self.stdout.write(
            self.style.SUCCESS('SystemSetting table setup completed!')
        )