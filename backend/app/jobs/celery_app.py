from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery("tp_manager", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.timezone = "UTC"

celery_app.conf.beat_schedule = {
    "cliniccards-sync-every-5-min": {
        "task": "app.jobs.tasks.sync_cliniccards_task",
        "schedule": crontab(minute="*/5"),
    },
    "dispatch-notifications-every-minute": {
        "task": "app.jobs.tasks.dispatch_notifications_task",
        "schedule": crontab(minute="*"),
    },
    "run-reminders-every-5-min": {
        "task": "app.jobs.tasks.run_reminders_task",
        "schedule": crontab(minute="*/5"),
    },
}

celery_app.autodiscover_tasks(["app.jobs"])
