"""In-process loop that purges old clinical image files — see
app/services/image_cleanup.py for what "purge" means and why. Runs the
same way as app/jobs/periodic_sync.py: a background asyncio task started
from main.py's lifespan, no separate worker deployment needed. Once a day
is plenty for a week-scale retention policy.

The actual DB work runs via asyncio.to_thread — purge_old_images() is a
synchronous, blocking SQLAlchemy call, and this loop shares its event loop
with every HTTP request the app is serving, so running it directly here
would freeze the whole app for everyone while it runs (same issue as
periodic_sync.py; see that file's docstring for how this was confirmed).
"""
import asyncio
import logging

from app.config import get_settings
from app.database import SessionLocal
from app.services.image_cleanup import purge_old_images

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS = 24 * 60 * 60


def _purge_old_images_blocking() -> int:
    db = SessionLocal()
    try:
        purged = purge_old_images(db, get_settings().image_retention_days)
        db.commit()
        return purged
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def _run_one_cleanup() -> None:
    try:
        purged = await asyncio.to_thread(_purge_old_images_blocking)
        if purged:
            logger.info("Periodic image cleanup: purged %s image(s)", purged)
    except Exception:  # noqa: BLE001 — one bad cycle must not kill the loop
        logger.exception("Periodic image cleanup cycle failed")


async def periodic_image_cleanup_loop() -> None:
    while True:
        await _run_one_cleanup()
        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)
