from django.core.management.base import BaseCommand
from core.models import SystemSetting


class Command(BaseCommand):
    help = 'Set up default system settings for admin management'

    def handle(self, *args, **options):
        """Create default settings."""

        default_settings = [
            # Throttling & Rate Limiting
            {
                'key': 'throttling_enabled',
                'value': 'true',
                'setting_type': 'boolean',
                'category': 'throttling',
                'description': 'Master switch for all API rate limiting and throttling. When disabled, all rate limits are bypassed.',
                'environment_restriction': 'any'
            },
            {
                'key': 'rate_limit_multiplier',
                'value': '1.0',
                'setting_type': 'float',
                'category': 'throttling',
                'description': 'Multiply all rate limits by this factor. Use 10.0 for testing to make limits 10x more permissive.',
                'environment_restriction': 'any'
            },
            {
                'key': 'bypass_throttling_for_admin',
                'value': 'false',
                'setting_type': 'boolean',
                'category': 'throttling',
                'description': 'Allow admin users to bypass all throttling limits.',
                'environment_restriction': 'any'
            },
            {
                'key': 'login_rate_limit_override',
                'value': '',
                'setting_type': 'string',
                'category': 'throttling',
                'description': 'Override login rate limit (e.g., "1000/hour"). Leave empty to use default.',
                'environment_restriction': 'any'
            },

            # Security Features
            {
                'key': 'csrf_protection_enabled',
                'value': 'true',
                'setting_type': 'boolean',
                'category': 'security',
                'description': 'Enable/disable CSRF protection for API endpoints.',
                'environment_restriction': 'development'
            },
            {
                'key': 'secure_cookies_enabled',
                'value': 'true',
                'setting_type': 'boolean',
                'category': 'security',
                'description': 'Enable secure cookie flags (HTTPS only).',
                'environment_restriction': 'development'
            },
            {
                'key': 'audit_logging_enabled',
                'value': 'true',
                'setting_type': 'boolean',
                'category': 'security',
                'description': 'Enable detailed security audit logging.',
                'environment_restriction': 'any'
            },

            # Development Tools
            {
                'key': 'debug_mode_override',
                'value': 'false',
                'setting_type': 'boolean',
                'category': 'development',
                'description': 'Force enable debug mode regardless of environment.',
                'environment_restriction': 'development'
            },
            {
                'key': 'api_docs_enabled',
                'value': 'true',
                'setting_type': 'boolean',
                'category': 'development',
                'description': 'Enable API documentation endpoints.',
                'environment_restriction': 'development'
            },
            {
                'key': 'detailed_error_responses',
                'value': 'false',
                'setting_type': 'boolean',
                'category': 'development',
                'description': 'Return detailed error messages and stack traces.',
                'environment_restriction': 'development'
            },

            # Email Configuration
            {
                'key': 'email_backend_override',
                'value': '',
                'setting_type': 'string',
                'category': 'email',
                'description': 'Override email backend (e.g., "console", "sendgrid"). Leave empty for default.',
                'environment_restriction': 'development'
            },
            {
                'key': 'email_rate_limiting_enabled',
                'value': 'true',
                'setting_type': 'boolean',
                'category': 'email',
                'description': 'Enable rate limiting for email sending.',
                'environment_restriction': 'any'
            },

            # Logging & Monitoring
            {
                'key': 'verbose_logging_enabled',
                'value': 'false',
                'setting_type': 'boolean',
                'category': 'logging',
                'description': 'Enable verbose logging for debugging.',
                'environment_restriction': 'development'
            },
            {
                'key': 'performance_monitoring_enabled',
                'value': 'false',
                'setting_type': 'boolean',
                'category': 'logging',
                'description': 'Enable performance metrics collection.',
                'environment_restriction': 'any'
            },
        ]

        created_count = 0
        updated_count = 0

        for setting_data in default_settings:
            setting, created = SystemSetting.objects.get_or_create(
                key=setting_data['key'],
                defaults=setting_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created setting: {setting.key}')
                )
            else:
                # Update description and other fields but keep user values
                setting.description = setting_data['description']
                setting.category = setting_data['category']
                setting.setting_type = setting_data['setting_type']
                setting.environment_restriction = setting_data['environment_restriction']
                setting.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated setting: {setting.key}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSetup complete: {created_count} created, {updated_count} updated'
            )
        )
        self.stdout.write('')
        self.stdout.write('📋 Quick Start Guide:')
        self.stdout.write('1. Go to Django admin: /admin/')
        self.stdout.write('2. Navigate to "System Settings"')
        self.stdout.write('3. To disable throttling: Set "throttling_enabled" to False')
        self.stdout.write('4. To increase rate limits: Set "rate_limit_multiplier" to 10.0')
        self.stdout.write('5. Changes take effect immediately!')