"""In-process loop that purges old clinical image files — see
app/services/image_cleanup.py for what "purge" means and why. Runs the
same way as app/jobs/periodic_sync.py: a background asyncio task started
from main.py's lifespan, no separate worker deployment needed. Once a day
is plenty for a week-scale retention policy.
"""
import asyncio
import logging

from app.config import get_settings
from app.database import SessionLocal
from app.services.image_cleanup import purge_old_images

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS = 24 * 60 * 60


async def _run_one_cleanup() -> None:
    db = SessionLocal()
    try:
        purged = purge_old_images(db, get_settings().image_retention_days)
        db.commit()
        if purged:
            logger.info("Periodic image cleanup: purged %s image(s)", purged)
    except Exception:  # noqa: BLE001 — one bad cycle must not kill the loop
        logger.exception("Periodic image cleanup cycle failed")
        db.rollback()
    finally:
        db.close()


async def periodic_image_cleanup_loop() -> None:
    while True:
        await _run_one_cleanup()
        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)
