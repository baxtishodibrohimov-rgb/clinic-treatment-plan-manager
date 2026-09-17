"""In-process Cliniccards sync loop.

Celery + celery-beat already has this same job scheduled (see
app/jobs/tasks.py / celery_app.py), but that only runs if a separate
worker + beat process is actually deployed alongside the web service —
which isn't the case here (single Railway service, no Redis-backed
worker). Running it as a background asyncio task inside the same process
that already serves the API needs no extra deployment: it starts the
moment the web service starts.

This does not replace the manual "Sync now" button (POST
/api/settings/sync-now) — that still calls sync_second_consultations()
directly and works independently of this loop.
"""
import asyncio
import logging

from app.config import get_settings
from app.database import SessionLocal
from app.integrations.cliniccards.factory import get_cliniccards_adapter
from app.models.enums import SyncType
from app.services.sync_service import sync_second_consultations

logger = logging.getLogger(__name__)


async def _run_one_sync() -> None:
    db = SessionLocal()
    try:
        adapter = get_cliniccards_adapter()
        result = await sync_second_consultations(db, adapter, SyncType.POLL)
        if result.get("errors"):
            logger.warning("Periodic Cliniccards sync finished with errors: %s", result["errors"])
        else:
            logger.info(
                "Periodic Cliniccards sync: %s appointment(s) seen, %s case(s) created",
                result.get("records_seen"),
                result.get("cases_created"),
            )
    except Exception:  # noqa: BLE001 — one bad cycle must not kill the loop
        logger.exception("Periodic Cliniccards sync cycle failed")
    finally:
        db.close()


async def periodic_sync_loop() -> None:
    interval_seconds = max(1, get_settings().cliniccards_auto_sync_minutes) * 60
    while True:
        await _run_one_sync()
        await asyncio.sleep(interval_seconds)
