"""Core case-sync logic (spec sections 2, 3, 10, 19).

Shared between the periodic Celery poll, the webhook endpoint, and the
"Sync now" admin action, so all three paths create/update cases identically.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.integrations.cliniccards.base import CliniccardsAdapter
from app.integrations.cliniccards.types import CliniccardsAppointment
from app.models.enums import SyncStatus, SyncType
from app.models.sync_log import IntegrationSyncLog
from app.services.case_service import ensure_case, get_setting, import_images, upsert_appointment_cache, upsert_patient_cache


async def process_appointment(db: Session, adapter: CliniccardsAdapter, appt: CliniccardsAppointment) -> tuple[str, bool]:
    await upsert_patient_cache(db, adapter, appt.patient_id)
    upsert_appointment_cache(db, appt)
    case, created = ensure_case(db, appt)
    await import_images(db, adapter, case, appt.patient_id)
    return str(case.id), created


async def sync_second_consultations(
    db: Session,
    adapter: CliniccardsAdapter,
    sync_type: SyncType,
    only_appointment_id: str | None = None,
) -> dict:
    started_at = datetime.now(timezone.utc)
    errors: list[str] = []
    records_seen = 0
    cases_created = 0

    try:
        second_consultation_codes: list[str] = get_setting(
            db, "second_consultation_appointment_type_codes", ["consultation_2"]
        )

        appts = await adapter.get_appointments()
        if only_appointment_id:
            appts = [a for a in appts if a.appointment_id == only_appointment_id]
        appts = [a for a in appts if a.appointment_type_code in second_consultation_codes]
        records_seen = len(appts)

        for appt in appts:
            try:
                _, created = await process_appointment(db, adapter, appt)
                if created:
                    cases_created += 1
                db.commit()
            except Exception as e:  # noqa: BLE001 — one bad appointment must not abort the whole sync
                db.rollback()
                errors.append(f"{appt.appointment_id}: {e}")
    except Exception as e:  # noqa: BLE001
        errors.append(str(e))

    db.add(
        IntegrationSyncLog(
            source="cliniccards",
            sync_type=sync_type,
            status=SyncStatus.SUCCESS if not errors else (SyncStatus.PARTIAL if records_seen else SyncStatus.ERROR),
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            records_seen=records_seen,
            cases_created=cases_created,
            error="; ".join(errors) if errors else None,
        )
    )
    db.commit()

    return {"records_seen": records_seen, "cases_created": cases_created, "errors": errors}
