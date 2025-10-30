from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.safestring import mark_safe
from .models import SystemSetting


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    """Admin interface for system settings."""

    list_display = [
        'key',
        'category',
        'value_preview',
        'setting_type',
        'is_active_status',
        'environment_restriction',
        'updated_at'
    ]
    list_filter = [
        'category',
        'is_active',
        'environment_restriction',
        'setting_type'
    ]
    search_fields = ['key', 'description', 'value']
    # Remove list_editable since we have custom status display
    readonly_fields = ['created_at', 'updated_at', 'updated_by']

    fieldsets = [
        ('Setting Configuration', {
            'fields': ['key', 'value', 'setting_type', 'category'],
            'description': 'Basic setting configuration'
        }),
        ('Description & Usage', {
            'fields': ['description'],
            'description': 'What this setting controls'
        }),
        ('Access Control', {
            'fields': ['is_active', 'environment_restriction'],
            'description': 'When and where this setting applies'
        }),
        ('Audit Information', {
            'fields': ['created_at', 'updated_at', 'updated_by'],
            'classes': ['collapse'],
            'description': 'Change tracking information'
        })
    ]

    actions = [
        'disable_settings',
        'enable_settings',
        'reset_throttling_settings',
        'clear_settings_cache'
    ]

    def value_preview(self, obj):
        """Show a preview of the value."""
        value = str(obj.value)
        if len(value) > 50:
            return value[:47] + "..."
        return value
    value_preview.short_description = "Value"

    def is_active_status(self, obj):
        """Show active status with color coding."""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Inactive</span>'
            )
    is_active_status.short_description = "Status"

    def save_model(self, request, obj, form, change):
        """Track who made the change."""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

        # Clear cache
        from core.utils import SettingsManager
        SettingsManager.clear_cache()

        messages.success(
            request,
            f'Setting "{obj.key}" updated successfully. Cache cleared.'
        )

    def disable_settings(self, request, queryset):
        """Disable selected settings."""
        count = queryset.update(is_active=False)

        # Clear cache
        from core.utils import SettingsManager
        SettingsManager.clear_cache()

        self.message_user(
            request,
            f'{count} settings disabled and cache cleared.'
        )
    disable_settings.short_description = "Disable selected settings"

    def enable_settings(self, request, queryset):
        """Enable selected settings."""
        count = queryset.update(is_active=True)

        # Clear cache
        from core.utils import SettingsManager
        SettingsManager.clear_cache()

        self.message_user(
            request,
            f'{count} settings enabled and cache cleared.'
        )
    enable_settings.short_description = "Enable selected settings"

    def reset_throttling_settings(self, request, queryset):
        """Reset throttling settings to safe defaults."""
        throttling_settings = queryset.filter(category='throttling')
        for setting in throttling_settings:
            if setting.key == 'throttling_enabled':
                setting.value = 'true'
            elif setting.key == 'rate_limit_multiplier':
                setting.value = '1.0'
            elif setting.key == 'bypass_throttling_for_admin':
                setting.value = 'false'
            setting.updated_by = request.user
            setting.save()

        # Clear cache
        from core.utils import SettingsManager
        SettingsManager.clear_cache()

        self.message_user(
            request,
            'Throttling settings reset to defaults and cache cleared.'
        )
    reset_throttling_settings.short_description = "Reset throttling to defaults"

    def clear_settings_cache(self, request, queryset):
        """Clear the settings cache."""
        from core.utils import SettingsManager
        SettingsManager.clear_cache()
        self.message_user(request, 'Settings cache cleared successfully.')
    clear_settings_cache.short_description = "Clear settings cache"


# Customize admin site
admin.site.site_header = "Vineyard Group Fellowship Administration"
admin.site.site_title = "Vineyard Group Fellowship Admin"
admin.site.index_title = "Welcome to Vineyard Group Fellowship Administration"

# Register your models here.
