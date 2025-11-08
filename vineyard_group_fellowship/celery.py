"""
Celery configuration for Vineyard Group Fellowship.

This module configures Celery for background task processing including:
- Async email notifications
- Periodic cleanup tasks
- Database maintenance
- Cache management
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'vineyard_group_fellowship.settings.production')

# Create Celery app
app = Celery('vineyard_group_fellowship')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Daily cleanup of soft-deleted content (2am)
    'cleanup-soft-deleted-content': {
        'task': 'messaging.tasks.cleanup_soft_deleted_content',
        'schedule': crontab(hour=2, minute=0),
        # Task expires after 1 hour if not executed
        'options': {'expires': 3600},
    },

    # Daily cleanup of old notification logs (2:30am)
    'cleanup-old-notification-logs': {
        'task': 'messaging.tasks.cleanup_old_notification_logs',
        'schedule': crontab(hour=2, minute=30),
        'options': {'expires': 3600},
    },

    # Weekly recount of denormalized counts (Sunday 3am)
    'recount-denormalized-counts': {
        'task': 'messaging.tasks.recount_denormalized_counts',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
        'options': {'expires': 7200},  # 2 hours
    },

    # Daily cleanup of expired tokens (1am)
    'cleanup-expired-tokens': {
        'task': 'authentication.tasks.cleanup_expired_tokens',
        'schedule': crontab(hour=1, minute=0),
        'options': {'expires': 3600},
    },
}

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Task execution settings
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={'visibility_timeout': 3600},

    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,

    # Retry settings
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,  # Reject lost tasks
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'
