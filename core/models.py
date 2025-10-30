from django.db import models
from django.conf import settings
from django.core.cache import cache
import json


class SystemSetting(models.Model):
    """Dynamic system settings manageable via Django admin."""

    SETTING_TYPES = [
        ('boolean', 'Boolean (True/False)'),
        ('integer', 'Integer Number'),
        ('float', 'Decimal Number'),
        ('string', 'Text String'),
        ('json', 'JSON Object'),
    ]

    CATEGORIES = [
        ('throttling', '🔒 Throttling & Rate Limiting'),
        ('security', '🛡️ Security Features'),
        ('development', '🔧 Development Tools'),
        ('email', '📧 Email Configuration'),
        ('logging', '📊 Logging & Monitoring'),
    ]

    ENVIRONMENT_CHOICES = [
        ('any', 'Any Environment'),
        ('development', 'Development Only'),
        ('staging', 'Staging Only'),
        ('testing', 'Testing Only'),
        ('production', 'Production Only'),
    ]

    key = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique identifier for this setting"
    )
    value = models.TextField(
        help_text="Setting value (will be parsed according to setting_type)"
    )
    setting_type = models.CharField(
        max_length=20,
        choices=SETTING_TYPES,
        default='string'
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORIES,
        default='development'
    )
    description = models.TextField(
        help_text="Description of what this setting controls"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this setting is currently active"
    )
    environment_restriction = models.CharField(
        max_length=50,
        choices=ENVIRONMENT_CHOICES,
        default='development',
        help_text="Which environments this setting can be used in"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"
        ordering = ['category', 'key']

    def __str__(self):
        return f"{self.key} ({self.category})"

    def get_parsed_value(self):
        """Parse the value according to its type."""
        if self.setting_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.setting_type == 'integer':
            return int(self.value)
        elif self.setting_type == 'float':
            return float(self.value)
        elif self.setting_type == 'json':
            return json.loads(self.value)
        else:
            return self.value

    def save(self, *args, **kwargs):
        """Clear cache when settings change."""
        super().save(*args, **kwargs)
        cache.delete(f'system_setting_{self.key}')
        cache.delete('all_system_settings')

# Create your models here.
