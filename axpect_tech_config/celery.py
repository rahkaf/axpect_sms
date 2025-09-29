import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axpect_tech_config.settings')

app = Celery('axpect_tech')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'calculate-daily-scores': {
        'task': 'api.tasks.calculate_daily_scores',
        'schedule': 60.0 * 60.0 * 24.0,  # Daily at midnight
    },
    'generate-automatic-jobcards': {
        'task': 'api.tasks.generate_automatic_jobcards',
        'schedule': 60.0 * 60.0 * 8.0,  # Every 8 hours
    },
    'send-daily-notifications': {
        'task': 'api.tasks.send_daily_notifications',
        'schedule': 60.0 * 60.0 * 8.0,  # Every 8 hours
    },
    'sync-google-drive': {
        'task': 'api.tasks.sync_google_drive_data',
        'schedule': 60.0 * 60.0 * 24.0,  # Daily
    },
}

app.conf.timezone = 'UTC'


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
