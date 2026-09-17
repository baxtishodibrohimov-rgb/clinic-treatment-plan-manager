"""Core case-sync logic (spec sections 2, 3, 10, 19).

Shared between the periodic Celery poll, the webhook endpoint, and the
"Sync now" admin action, so all three paths create/update cases identically.
"""
import asyncio
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.integrations.cliniccards.base import CliniccardsAdapter
from app.integrations.cliniccards.factory import get_cliniccards_adapter
from app.integrations.cliniccards.types import CliniccardsAppointment
from app.models.clinic import Clinic
from app.models.enums import SyncStatus, SyncType
from app.models.sync_log import IntegrationSyncLog
from app.services.case_service import ensure_case, import_images, upsert_appointment_cache, upsert_patient_cache

# Every clinic shares one Cliniccards account — there is no per-clinic API
# credential. These are best-effort field names to check on the raw
# appointment payload for a branch identifier; update once real Cliniccards
# API docs show what that field is actually called (same caveat as
# app/integrations/cliniccards/http_provider.py).
BRANCH_FIELD_CANDIDATES = ("branchCode", "branch_code", "branch", "clinicCode", "clinic_code", "location", "filialCode", "filial")

# Confirmed against real Cliniccards data: staff mark a 2nd-consultation
# booking by starting the visit's note/title with "2nd cons", "2and cons",
# or the observed typo "2and cond" — always "2" + an optional "nd"/"and" +
# "cons"/"cond". This is intentionally NOT a bare "starts with 2" check:
# real patient histories also contain routine treatment notes like "2ta bss
# qoyiladi" or "2 TA IZC" ("install 2 of ...") that must NOT match — a
# patient already deep into active treatment can have any number of these,
# and none of them mean "this is their 2nd consultation".
_SECOND_CONSULTATION_RE = re.compile(r"^2\s*(a?nd)?\s*con[sd]")


def is_second_consultation(appt: CliniccardsAppointment) -> bool:
    note = re.sub(r"\s+", " ", (appt.note or "").strip().casefold())
    return bool(_SECOND_CONSULTATION_RE.match(note))


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
        appts = await adapter.get_appointments()
        if only_appointment_id:
            appts = [a for a in appts if a.appointment_id == only_appointment_id]
        appts = [a for a in appts if is_second_consultation(a)]
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


def sync_second_consultations_blocking(sync_type: SyncType, only_appointment_id: str | None = None) -> dict:
    """Entry point for anywhere that isn't already running its own
    dedicated background loop: the manual "Sync now" endpoint and the
    Cliniccards webhook handler.

    sync_second_consultations() above is `async def`, but everything it
    actually does — every db.execute/commit/flush inside ensure_case,
    upsert_patient_cache, import_images, etc. — is a *synchronous*, blocking
    SQLAlchemy call. Calling it directly with `await` from a FastAPI
    `async def` route runs all of that on the one shared event loop that
    serves every other request, so the whole app freezes for every user for
    as long as the sync takes (confirmed: a concurrent 5ms heartbeat task
    got zero ticks for the full ~190ms of a 5-appointment mock sync — with
    real Cliniccards network calls this is seconds, not milliseconds).

    This function builds its own DB session and Cliniccards adapter and
    runs the whole sync on a fresh event loop, so it's safe to call via
    `await asyncio.to_thread(sync_second_consultations_blocking, ...)` —
    the shared event loop stays free to keep serving everyone else while
    this runs on its own thread."""
    db = SessionLocal()
    try:
        adapter = get_cliniccards_adapter()
        return asyncio.run(sync_second_consultations(db, adapter, sync_type, only_appointment_id))
    finally:
        db.close()
