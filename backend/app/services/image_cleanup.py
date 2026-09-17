"""We don't keep clinical photos/x-rays forever. Once a case's consultation
is far enough in the past (see Settings.image_retention_days), the actual
image bytes are purged — the ClinicalImage row itself stays (so
analysis_answers.image_id, which CASCADEs on that row's deletion, and
findings.source_image_id keep pointing at something real, and the
diagnostic gallery still shows which slot each answer came from), only
file_data/mime_type/original_filename are cleared.

Cliniccards-sourced images (external_url set) self-heal: the next view
re-downloads and re-caches them from Cliniccards on demand (see
app/api/routers/images.py) — only the local cached copy is dropped. A
manually uploaded photo (no external_url) has no such origin, so purging
it there is permanent, which is the point: we're not the archive for
those.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.case import TreatmentPlanCase
from app.models.image import ClinicalImage


def purge_old_images(db: Session, retention_days: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    old_case_ids = select(TreatmentPlanCase.id).where(TreatmentPlanCase.consultation_datetime < cutoff)
    result = db.execute(
        update(ClinicalImage)
        .where(ClinicalImage.case_id.in_(old_case_ids))
        .where(ClinicalImage.file_data.is_not(None))
        .values(file_data=None, mime_type=None, original_filename=None)
    )
    return result.rowcount
