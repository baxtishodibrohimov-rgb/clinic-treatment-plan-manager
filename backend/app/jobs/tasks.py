import asyncio

from app.database import SessionLocal
from app.integrations.cliniccards.factory import get_cliniccards_adapter
from app.jobs.celery_app import celery_app
from app.models.enums import SyncType
from app.notifications.dispatcher import dispatch_pending
from app.services.reminders import run_reminders
from app.services.sync_service import sync_second_consultations


@celery_app.task(name="app.jobs.tasks.sync_cliniccards_task")
def sync_cliniccards_task(sync_type: str = SyncType.POLL.value, only_appointment_id: str | None = None) -> dict:
    db = SessionLocal()
    try:
        adapter = get_cliniccards_adapter()
        return asyncio.run(sync_second_consultations(db, adapter, SyncType(sync_type), only_appointment_id))
    finally:
        db.close()


@celery_app.task(name="app.jobs.tasks.dispatch_notifications_task")
def dispatch_notifications_task() -> dict:
    db = SessionLocal()
    try:
        return asyncio.run(dispatch_pending(db))
    finally:
        db.close()


@celery_app.task(name="app.jobs.tasks.run_reminders_task")
def run_reminders_task() -> dict:
    db = SessionLocal()
    try:
        return run_reminders(db)
    finally:
        db.close()
