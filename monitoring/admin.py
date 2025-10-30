"""
Django admin configuration for monitoring models.

Provides admin interface for:
- Performance metrics analysis
- Health check monitoring
- Endpoint performance tracking
- Database query analysis
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Avg, Count, Max, Min
from django.utils import timezone
from datetime import timedelta

from .models import PerformanceMetric, EndpointMetrics, DatabaseQueryMetrics, HealthCheck


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    """Admin interface for performance metrics."""

    list_display = [
        'name', 'metric_type', 'value', 'unit',
        'timestamp', 'get_context_summary'
    ]
    list_filter = [
        'metric_type', 'unit', 'timestamp',
        ('timestamp', admin.DateFieldListFilter)
    ]
    search_fields = ['name', 'context__endpoint_path', 'context__method']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp', 'get_context_display']

    fieldsets = (
        (None, {
            'fields': ('metric_type', 'name', 'value', 'unit')
        }),
        ('Context', {
            'fields': ('get_context_display',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('timestamp', 'content_type', 'object_id'),
            'classes': ('collapse',)
        })
    )

    def get_context_summary(self, obj):
        """Display a summary of the context data."""
        if obj.context:
            endpoint = obj.context.get('endpoint_path', '')
            method = obj.context.get('method', '')
            status = obj.context.get('status_code', '')

            if endpoint and method:
                return f"{method} {endpoint}"
            return str(obj.context)[:50] + "..." if len(str(obj.context)) > 50 else str(obj.context)
        return "-"
    get_context_summary.short_description = "Context"

    def get_context_display(self, obj):
        """Display formatted context data."""
        if obj.context:
            import json
            return format_html(
                '<pre>{}</pre>',
                json.dumps(obj.context, indent=2)
            )
        return "-"
    get_context_display.short_description = "Context Data"

    def get_queryset(self, request):
        """Optimize queryset for admin display."""
        return super().get_queryset(request).select_related('content_type')


@admin.register(EndpointMetrics)
class EndpointMetricsAdmin(admin.ModelAdmin):
    """Admin interface for endpoint metrics."""

    list_display = [
        'endpoint_path', 'http_method', 'time_window_start',
        'request_count', 'error_count', 'get_error_rate',
        'avg_response_time', 'p95_response_time'
    ]
    list_filter = [
        'http_method', 'time_window_start',
        ('time_window_start', admin.DateFieldListFilter)
    ]
    search_fields = ['endpoint_path']
    ordering = ['-time_window_start']
    readonly_fields = ['created_at', 'get_status_codes_display']

    fieldsets = (
        (None, {
            'fields': ('endpoint_path', 'http_method')
        }),
        ('Time Window', {
            'fields': ('time_window_start', 'time_window_end')
        }),
        ('Request Statistics', {
            'fields': ('request_count', 'error_count')
        }),
        ('Response Time Statistics', {
            'fields': (
                'avg_response_time', 'min_response_time',
                'max_response_time', 'p95_response_time'
            )
        }),
        ('Status Codes', {
            'fields': ('get_status_codes_display',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def get_error_rate(self, obj):
        """Display error rate as percentage."""
        return f"{obj.error_rate:.1f}%"
    get_error_rate.short_description = "Error Rate"
    get_error_rate.admin_order_field = 'error_count'

    def get_status_codes_display(self, obj):
        """Display formatted status codes distribution."""
        if obj.status_codes:
            import json
            return format_html(
                '<pre>{}</pre>',
                json.dumps(obj.status_codes, indent=2, sort_keys=True)
            )
        return "-"
    get_status_codes_display.short_description = "Status Codes Distribution"


@admin.register(DatabaseQueryMetrics)
class DatabaseQueryMetricsAdmin(admin.ModelAdmin):
    """Admin interface for database query metrics."""

    list_display = [
        'query_type', 'table_name', 'execution_time',
        'rows_affected', 'endpoint_path', 'timestamp'
    ]
    list_filter = [
        'query_type', 'table_name', 'timestamp',
        ('timestamp', admin.DateFieldListFilter)
    ]
    search_fields = ['table_name', 'endpoint_path', 'query_hash']
    ordering = ['-execution_time', '-timestamp']
    readonly_fields = ['timestamp', 'query_hash']

    fieldsets = (
        (None, {
            'fields': ('query_type', 'table_name', 'query_hash')
        }),
        ('Performance', {
            'fields': ('execution_time', 'rows_affected')
        }),
        ('Context', {
            'fields': ('endpoint_path',)
        }),
        ('Metadata', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        """Limit to recent queries to avoid performance issues."""
        qs = super().get_queryset(request)
        # Show only last 7 days by default
        since = timezone.now() - timedelta(days=7)
        return qs.filter(timestamp__gte=since)


@admin.register(HealthCheck)
class HealthCheckAdmin(admin.ModelAdmin):
    """Admin interface for health checks."""

    list_display = [
        'check_type', 'status', 'response_time',
        'timestamp', 'get_status_color'
    ]
    list_filter = [
        'check_type', 'status', 'timestamp',
        ('timestamp', admin.DateFieldListFilter)
    ]
    search_fields = ['check_type', 'error_message']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp', 'get_details_display']

    fieldsets = (
        (None, {
            'fields': ('check_type', 'status', 'response_time')
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Details', {
            'fields': ('get_details_display',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        })
    )

    def get_status_color(self, obj):
        """Display status with color coding."""
        colors = {
            'healthy': 'green',
            'degraded': 'orange',
            'unhealthy': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_color.short_description = "Status"
    get_status_color.admin_order_field = 'status'

    def get_details_display(self, obj):
        """Display formatted details data."""
        if obj.details:
            import json
            return format_html(
                '<pre>{}</pre>',
                json.dumps(obj.details, indent=2)
            )
        return "-"
    get_details_display.short_description = "Details"

    def get_queryset(self, request):
        """Limit to recent health checks."""
        qs = super().get_queryset(request)
        # Show only last 7 days by default
        since = timezone.now() - timedelta(days=7)
        return qs.filter(timestamp__gte=since)


# Custom admin actions
def clear_old_metrics(modeladmin, request, queryset):
    """Clear metrics older than 30 days."""
    cutoff = timezone.now() - timedelta(days=30)
    deleted_count = queryset.filter(timestamp__lt=cutoff).delete()[0]
    modeladmin.message_user(
        request,
        f"Cleared {deleted_count} metrics older than 30 days."
    )


clear_old_metrics.short_description = "Clear metrics older than 30 days"

# Add action to relevant admin classes
PerformanceMetricAdmin.actions = [clear_old_metrics]
DatabaseQueryMetricsAdmin.actions = [clear_old_metrics]
HealthCheckAdmin.actions = [clear_old_metrics]
