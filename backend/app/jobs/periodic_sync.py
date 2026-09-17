"""In-process Cliniccards sync loop.

Celery + celery-beat already has this same job scheduled (see
app/jobs/tasks.py / celery_app.py), but that only runs if a separate
worker + beat process is actually deployed alongside the web service —
which isn't the case here (single Railway service, no Redis-backed
worker). Running it as a background asyncio task inside the same process
that already serves the API needs no extra deployment: it starts the
moment the web service starts.

This does not replace the manual "Sync now" button (POST
/api/settings/sync-now) — that still calls the same underlying sync
independently of this loop.

sync_second_consultations_blocking() runs on its own thread + event loop
(via asyncio.to_thread below), not directly on this loop — it does a lot
of synchronous, blocking SQLAlchemy work internally, and this loop shares
its event loop with every HTTP request the app is serving. Calling it
directly here would freeze the whole app for every user for as long as
each sync cycle takes (confirmed: a concurrent 5ms heartbeat task got zero
ticks for the full ~190ms of a 5-appointment mock sync).
"""
import asyncio
import logging

from app.config import get_settings
from app.models.enums import SyncType
from app.services.sync_service import sync_second_consultations_blocking

logger = logging.getLogger(__name__)


async def _run_one_sync() -> None:
    try:
        result = await asyncio.to_thread(sync_second_consultations_blocking, SyncType.POLL)
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


async def periodic_sync_loop() -> None:
    interval_seconds = max(1, get_settings().cliniccards_auto_sync_minutes) * 60
    while True:
        await _run_one_sync()
        await asyncio.sleep(interval_seconds)
