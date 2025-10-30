"""
Celery configuration for Hotspot Detection System
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotspot_detection.settings')

# Create Celery app
app = Celery('hotspot_detection')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    # Run clustering daily at 2 AM
    'run-daily-clustering': {
        'task': 'accidents.tasks.run_clustering_task',
        'schedule': crontab(hour=2, minute=0),
        'args': (),
    },
    # Clear old cache entries every 6 hours
    'clear-expired-cache': {
        'task': 'accidents.tasks.clear_expired_cache_task',
        'schedule': crontab(hour='*/6', minute=0),
        'args': (),
    },
    # Generate weekly statistics report
    'generate-weekly-stats': {
        'task': 'accidents.tasks.generate_weekly_statistics_task',
        'schedule': crontab(day_of_week=1, hour=8, minute=0),  # Monday 8 AM
        'args': (),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery setup"""
    print(f'Request: {self.request!r}')
