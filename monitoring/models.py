"""
Performance monitoring models for tracking application metrics.

Stores performance data for analysis and alerting:
- Request/response metrics by endpoint
- Database query performance
- Error rates and response times
- System health snapshots
"""

from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json


class MetricType(models.TextChoices):
    """Types of metrics tracked by the monitoring system."""
    REQUEST_RESPONSE = 'request_response', 'Request/Response'
    DATABASE_QUERY = 'database_query', 'Database Query'
    BUSINESS_METRIC = 'business_metric', 'Business Metric'
    SYSTEM_HEALTH = 'system_health', 'System Health'
    ERROR_RATE = 'error_rate', 'Error Rate'


class PerformanceMetric(models.Model):
    """
    Model for storing application performance metrics.

    Captures performance data points for monitoring and alerting.
    """
    metric_type = models.CharField(
        max_length=50,
        choices=MetricType.choices,
        help_text="Type of metric being tracked"
    )

    name = models.CharField(
        max_length=200,
        help_text="Name/identifier for this metric"
    )

    value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Numeric value of the metric"
    )

    unit = models.CharField(
        max_length=20,
        help_text="Unit of measurement (ms, count, bytes, etc.)"
    )

    # Additional context data as JSON
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context data for this metric"
    )

    # Generic foreign key for linking to related objects
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When this metric was recorded"
    )

    class Meta:
        verbose_name = "Performance Metric"
        verbose_name_plural = "Performance Metrics"
        indexes = [
            models.Index(fields=['metric_type', '-timestamp']),
            models.Index(fields=['name', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.name}: {self.value} {self.unit} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"


class EndpointMetrics(models.Model):
    """
    Aggregated metrics for API endpoints.

    Tracks performance statistics for each endpoint over time windows.
    """
    endpoint_path = models.CharField(
        max_length=500,
        help_text="API endpoint path (e.g., /api/v1/users/)"
    )

    http_method = models.CharField(
        max_length=10,
        help_text="HTTP method (GET, POST, etc.)"
    )

    # Time window for aggregation
    time_window_start = models.DateTimeField(
        help_text="Start of the time window for these metrics"
    )
    time_window_end = models.DateTimeField(
        help_text="End of the time window for these metrics"
    )

    # Request statistics
    request_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of requests in this time window"
    )

    error_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of requests that resulted in errors (4xx, 5xx)"
    )

    # Response time statistics (in milliseconds)
    avg_response_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Average response time in milliseconds"
    )

    min_response_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Minimum response time in milliseconds"
    )

    max_response_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Maximum response time in milliseconds"
    )

    p95_response_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="95th percentile response time in milliseconds"
    )

    # Status code distribution
    status_codes = models.JSONField(
        default=dict,
        help_text="Distribution of HTTP status codes {code: count}"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this metrics record was created"
    )

    class Meta:
        verbose_name = "Endpoint Metrics"
        verbose_name_plural = "Endpoint Metrics"
        unique_together = [
            ['endpoint_path', 'http_method', 'time_window_start']]
        indexes = [
            models.Index(fields=['endpoint_path', '-time_window_start']),
            models.Index(fields=['-time_window_start']),
        ]
        ordering = ['-time_window_start']

    def __str__(self):
        return f"{self.http_method} {self.endpoint_path} ({self.time_window_start.strftime('%Y-%m-%d %H:%M')})"

    @property
    def error_rate(self):
        """Calculate error rate as a percentage."""
        if self.request_count == 0:
            return 0
        return (self.error_count / self.request_count) * 100


class DatabaseQueryMetrics(models.Model):
    """
    Metrics for database query performance.

    Tracks slow queries and database performance over time.
    """
    query_type = models.CharField(
        max_length=50,
        help_text="Type of query (SELECT, INSERT, UPDATE, DELETE, etc.)"
    )

    table_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primary table involved in the query"
    )

    # Query performance
    execution_time = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Query execution time in milliseconds"
    )

    rows_affected = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of rows affected by the query"
    )

    # Query identification (hashed for privacy)
    query_hash = models.CharField(
        max_length=64,
        help_text="Hash of the query for identification"
    )

    # Optional query context
    endpoint_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="API endpoint that triggered this query"
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When this query was executed"
    )

    class Meta:
        verbose_name = "Database Query Metrics"
        verbose_name_plural = "Database Query Metrics"
        indexes = [
            models.Index(fields=['-execution_time']),
            models.Index(fields=['query_type', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.query_type} on {self.table_name or 'unknown'} ({self.execution_time}ms)"


class HealthCheck(models.Model):
    """
    System health check results.

    Stores results of periodic health checks for monitoring system status.
    """

    class Status(models.TextChoices):
        HEALTHY = 'healthy', 'Healthy'
        DEGRADED = 'degraded', 'Degraded'
        UNHEALTHY = 'unhealthy', 'Unhealthy'

    check_type = models.CharField(
        max_length=50,
        help_text="Type of health check (database, cache, external_api, etc.)"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        help_text="Status of the health check"
    )

    response_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Response time for the health check in milliseconds"
    )

    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional details about the health check"
    )

    error_message = models.TextField(
        blank=True,
        help_text="Error message if the health check failed"
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When this health check was performed"
    )

    class Meta:
        verbose_name = "Health Check"
        verbose_name_plural = "Health Checks"
        indexes = [
            models.Index(fields=['check_type', '-timestamp']),
            models.Index(fields=['status', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.check_type}: {self.status} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"
