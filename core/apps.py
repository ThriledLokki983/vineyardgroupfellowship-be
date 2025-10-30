"""
Core application configuration for Vineyard Group Fellowship.

This app contains shared utilities, exception handlers, and middleware
used across the entire project.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core'
