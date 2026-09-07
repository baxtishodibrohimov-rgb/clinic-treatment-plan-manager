"""Core case-sync logic (spec sections 2, 3, 10, 19).

Shared between the periodic Celery poll, the webhook endpoint, and the
"Sync now" admin action, so all three paths create/update cases identically.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.cliniccards.base import CliniccardsAdapter
from app.integrations.cliniccards.types import CliniccardsAppointment
from app.models.clinic import Clinic
from app.models.enums import SyncStatus, SyncType
from app.models.sync_log import IntegrationSyncLog
from app.services.case_service import ensure_case, get_setting, import_images, upsert_appointment_cache, upsert_patient_cache

# Every clinic shares one Cliniccards account — there is no per-clinic API
# credential. These are best-effort field names to check on the raw
# appointment payload for a branch identifier; update once real Cliniccards
# API docs show what that field is actually called (same caveat as
# app/integrations/cliniccards/http_provider.py).
BRANCH_FIELD_CANDIDATES = ("branchCode", "branch_code", "branch", "clinicCode", "clinic_code", "location", "filialCode", "filial")


def resolve_clinic_for_appointment(db: Session, appt: CliniccardsAppointment) -> uuid.UUID | None:
    clinics = db.execute(select(Clinic).where(Clinic.is_active.is_(True))).scalars().all()
    if not clinics:
        return None
    if len(clinics) == 1:
        return clinics[0].id

    by_code = {c.cliniccards_branch_code: c.id for c in clinics if c.cliniccards_branch_code}
    raw = appt.raw or {}
    for field in BRANCH_FIELD_CANDIDATES:
        value = raw.get(field)
        if value is not None and str(value) in by_code:
            return by_code[str(value)]

    default = next((c for c in clinics if c.is_default), None)
    return default.id if default else None


async def process_appointment(db: Session, adapter: CliniccardsAdapter, appt: CliniccardsAppointment) -> tuple[str, bool]:
    await upsert_patient_cache(db, adapter, appt.patient_id)
    upsert_appointment_cache(db, appt)
    clinic_id = resolve_clinic_for_appointment(db, appt)
    case, created = ensure_case(db, appt, clinic_id)
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
