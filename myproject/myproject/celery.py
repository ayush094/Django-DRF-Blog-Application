from __future__ import absolute_import, unicode_literals
import os

from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

# Create Celery app
app = Celery("myproject")

# Load config from Django settings using CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# -------------------------------
# Celery Beat Schedule (EVERY 10 MINUTES)
# -------------------------------
app.conf.beat_schedule = {
    "publish-blogs-every-10-minutes": {
        "task": "blog_app.tasks.publish_due_blogs",
        "schedule": crontab(minute="*/10"),
    },
}

# Optional debug task
@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
