"""Core TreatmentPlanCase logic: idempotent creation from a Cliniccards
appointment, status-machine enforcement, image import + progress
calculation. Shared by the sync service (app/services/sync_service.py) and
the case API router — every write to a case goes through here so the audit
trail and state machine can never be bypassed."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.cliniccards.base import CliniccardsAdapter
from app.integrations.cliniccards.types import CliniccardsAppointment
from app.integrations.image_classifier import classify_image_type
from app.models.case import ALLOWED_TRANSITIONS, TreatmentPlanCase
from app.models.cliniccards import CliniccardsAppointmentCache, CliniccardsPatientCache
from app.models.enums import CaseStatus, ReviewDecision, Role
from app.models.image import ClinicalImage, ImageSource, ImageType
from app.models.settings import AppSetting
from app.models.treatment_plan import Review
from app.models.user import User, UserRole
from app.services.audit import write_audit
from app.services.notifications import queue_notification


class InvalidTransition(ValueError):
    pass


def validate_transition(old_status: CaseStatus, new_status: CaseStatus) -> None:
    if old_status == new_status:
        return
    if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
        raise InvalidTransition(f"Invalid case status transition: {old_status} -> {new_status}")


def set_case_status(
    db: Session,
    case: TreatmentPlanCase,
    new_status: CaseStatus,
    *,
    actor_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> None:
    validate_transition(case.status, new_status)
    old_status = case.status
    case.status = new_status
    if old_status != new_status:
        write_audit(
            db,
            case_id=case.id,
            actor_user_id=actor_user_id,
            action="status_changed",
            details={"from": old_status.value, "to": new_status.value, "reason": reason},
        )


def get_setting(db: Session, key: str, default):
    row = db.get(AppSetting, key)
    return row.value if row else default


async def upsert_patient_cache(db: Session, adapter: CliniccardsAdapter, patient_id: str) -> None:
    patient = await adapter.get_patient(patient_id)
    if not patient:
        return
    row = db.execute(
        select(CliniccardsPatientCache).where(CliniccardsPatientCache.cliniccards_patient_id == patient.patient_id)
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row:
        row.full_name = patient.full_name
        row.birth_date = patient.birth_date
        row.phone = patient.phone
        row.raw_payload = patient.raw
        row.synced_at = now
    else:
        db.add(
            CliniccardsPatientCache(
                cliniccards_patient_id=patient.patient_id,
                full_name=patient.full_name,
                birth_date=patient.birth_date,
                phone=patient.phone,
                raw_payload=patient.raw,
                synced_at=now,
            )
        )
    db.flush()


def upsert_appointment_cache(db: Session, appt: CliniccardsAppointment) -> None:
    row = db.execute(
        select(CliniccardsAppointmentCache).where(
            CliniccardsAppointmentCache.cliniccards_appointment_id == appt.appointment_id
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row:
        row.appointment_type_code = appt.appointment_type_code
        row.appointment_type_label = appt.appointment_type_label
        row.doctor_name = appt.doctor_name
        row.scheduled_at = appt.scheduled_at
        row.raw_payload = appt.raw
        row.synced_at = now
    else:
        db.add(
            CliniccardsAppointmentCache(
                cliniccards_appointment_id=appt.appointment_id,
                cliniccards_patient_id=appt.patient_id,
                appointment_type_code=appt.appointment_type_code,
                appointment_type_label=appt.appointment_type_label,
                doctor_name=appt.doctor_name,
                scheduled_at=appt.scheduled_at,
                raw_payload=appt.raw,
                synced_at=now,
            )
        )
    db.flush()


def resolve_internal_doctor(db: Session, doctor_name: str | None, clinic_id: uuid.UUID | None) -> User | None:
    if not doctor_name:
        return None
    query = (
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .where(UserRole.role == Role.DOCTOR, User.full_name.ilike(doctor_name.strip()))
    )
    if clinic_id is not None:
        query = query.where(User.clinic_id == clinic_id)
    return db.execute(query).scalars().first()


def ensure_case(
    db: Session, appt: CliniccardsAppointment, clinic_id: uuid.UUID | None, *, source: str = "cliniccards"
) -> tuple[TreatmentPlanCase, bool]:
    """Idempotent case creation (spec section 3): a unique constraint on
    cliniccards_appointment_id guarantees one appointment never produces two
    cases, even under concurrent sync runs.

    `clinic_id` is resolved by the caller (see
    app.services.sync_service.resolve_clinic_for_appointment) — every
    clinic shares one Cliniccards account, so this function itself has no
    way to know which branch an appointment belongs to."""
    existing = db.execute(
        select(TreatmentPlanCase).where(TreatmentPlanCase.cliniccards_appointment_id == appt.appointment_id)
    ).scalar_one_or_none()
    if existing:
        # Cliniccards is the source of truth for scheduling — keep the case
        # in sync with it on every re-sync (this is also how an existing
        # case picks up a corrected time after a parsing bug like the +5h
        # timezone issue: the DB row was written with the old, wrong value
        # and nothing re-syncs it unless we actively update it here).
        deadline_hours = float(get_setting(db, "default_deadline_hours_before_consultation", 24))
        existing.consultation_datetime = appt.scheduled_at
        existing.deadline = appt.scheduled_at - timedelta(hours=deadline_hours)
        existing.primary_doctor_name = appt.doctor_name
        db.flush()
        return existing, False

    deadline_hours = float(get_setting(db, "default_deadline_hours_before_consultation", 24))
    deadline = appt.scheduled_at - timedelta(hours=deadline_hours)
    primary_doctor = resolve_internal_doctor(db, appt.doctor_name, clinic_id)

    case = TreatmentPlanCase(
        clinic_id=clinic_id,
        cliniccards_patient_id=appt.patient_id,
        cliniccards_appointment_id=appt.appointment_id,
        consultation_datetime=appt.scheduled_at,
        primary_doctor_user_id=primary_doctor.id if primary_doctor else None,
        primary_doctor_name=appt.doctor_name,
        deadline=deadline,
        status=CaseStatus.NEW,
    )
    db.add(case)
    try:
        db.flush()
    except IntegrityError:
        # Another concurrent sync run created it first.
        db.rollback()
        existing = db.execute(
            select(TreatmentPlanCase).where(TreatmentPlanCase.cliniccards_appointment_id == appt.appointment_id)
        ).scalar_one_or_none()
        if existing:
            return existing, False
        raise

    write_audit(
        db,
        case_id=case.id,
        action="case_created",
        details={"source": source, "cliniccards_appointment_id": appt.appointment_id},
    )

    from app.services.assignment import auto_assign_planner  # local import: avoid circular import

    assigned = auto_assign_planner(db, case)
    if not assigned:
        set_case_status(db, case, CaseStatus.WAITING_ASSIGNMENT)

    return case, True


def create_manual_case(
    db: Session,
    *,
    full_name: str,
    birth_date,
    phone: str | None,
    doctor_name: str | None,
    consultation_datetime: datetime,
    clinic_id: uuid.UUID,
    priority=None,
) -> TreatmentPlanCase:
    """Fully manual data entry, for a patient who isn't in Cliniccards at
    all (or staff doesn't want to look them up by card number — see
    create_case_from_cliniccards_patient below for that). Synthesizes a
    "MANUAL-..." patient id and appointment id so this reuses the exact
    same CliniccardsPatientCache/CliniccardsAppointmentCache/ensure_case
    pipeline as a real Cliniccards sync — nothing about downstream case
    handling (state machine, assignment, deadlines) has a separate code
    path to maintain for manually-entered cases."""
    patient_id = f"MANUAL-{uuid.uuid4()}"
    now = datetime.now(timezone.utc)
    db.add(
        CliniccardsPatientCache(
            cliniccards_patient_id=patient_id,
            full_name=full_name,
            birth_date=birth_date,
            phone=phone,
            raw_payload={"manual": True},
            synced_at=now,
        )
    )
    db.flush()

    appt = CliniccardsAppointment(
        appointment_id=f"MANUAL-{uuid.uuid4()}",
        patient_id=patient_id,
        doctor_name=doctor_name,
        appointment_type_code="manual",
        appointment_type_label="Qo'lda kiritilgan",
        scheduled_at=consultation_datetime,
        note=None,
        raw={"manual": True},
    )
    upsert_appointment_cache(db, appt)
    case, _ = ensure_case(db, appt, clinic_id, source="manual")
    if priority is not None:
        case.priority = priority
    return case


async def create_case_from_cliniccards_patient(
    db: Session,
    adapter: CliniccardsAdapter,
    *,
    cliniccards_patient_id: str,
    doctor_name: str | None,
    consultation_datetime: datetime,
    clinic_id: uuid.UUID,
    priority=None,
) -> TreatmentPlanCase:
    """Staff already knows the patient's real Cliniccards card number and
    wants to open a case for them right now, rather than waiting for their
    2nd-visit appointment to sync automatically. Unlike create_manual_case
    above, this keeps the real cliniccards_patient_id — not a synthesized
    "MANUAL-..." one — so the case's patient identity matches Cliniccards
    exactly and we can pull that patient's existing images immediately."""
    entered_card_number = cliniccards_patient_id.strip()
    patient = await adapter.get_patient(entered_card_number)
    if not patient:
        patient = await adapter.get_patient_by_card_number(entered_card_number)
    if not patient:
        raise ValueError(f"Clinic Cards'da {entered_card_number} raqamli bemor kartasi topilmadi")

    # The visible card number (`code`) and Clinic Cards' internal patient_id
    # are different fields. Store and sync with the canonical patient_id.
    cliniccards_patient_id = patient.patient_id

    await upsert_patient_cache(db, adapter, cliniccards_patient_id)

    appt = CliniccardsAppointment(
        appointment_id=f"MANUAL-{uuid.uuid4()}",
        patient_id=cliniccards_patient_id,
        doctor_name=doctor_name,
        appointment_type_code="manual_by_card",
        appointment_type_label="Karta raqami orqali kiritilgan",
        scheduled_at=consultation_datetime,
        note=None,
        raw={"manual_by_card": True},
    )
    upsert_appointment_cache(db, appt)
    case, _ = ensure_case(db, appt, clinic_id, source="manual_by_card")
    if priority is not None:
        case.priority = priority

    await import_images(db, adapter, case, cliniccards_patient_id)
    return case


async def import_images(db: Session, adapter: CliniccardsAdapter, case: TreatmentPlanCase, patient_id: str) -> None:
    images = await adapter.get_patient_images(patient_id)
    image_types = db.execute(select(ImageType).where(ImageType.is_active.is_(True))).scalars().all()
    by_label = {t.label.lower(): t.id for t in image_types}

    for img in images:
        image = db.execute(
            select(ClinicalImage).where(
                ClinicalImage.case_id == case.id, ClinicalImage.cliniccards_document_id == img.image_id
            )
        ).scalar_one_or_none()
        if image:
            # image_type_id is deliberately NOT touched here: once an image
            # exists, its slot may have been set by the label guess below,
            # by staff moving it from the bulut, or by auto-classification
            # — re-running this same label lookup on every sync (this
            # function runs automatically every 30 minutes) was wiping all
            # of that out and dropping the image back in the pool.
            image.external_url = img.url
            image.captured_at = img.captured_at
        else:
            image_type_id = by_label.get(img.label_hint.lower()) if img.label_hint else None
            image = ClinicalImage(
                case_id=case.id,
                image_type_id=image_type_id,
                source=ImageSource.CLINICCARDS,
                cliniccards_document_id=img.image_id,
                external_url=img.url,
                captured_at=img.captured_at,
            )
            db.add(image)
            db.flush()

        # Store a private local copy. Existing images are not downloaded
        # again; newly uploaded Cliniccards files are picked up next sync.
        if image.file_data is None and img.url:
            try:
                file_data, mime_type = await adapter.download_file(img.url)
            except Exception:  # noqa: BLE001 - leave metadata for the next retry/proxy fallback
                continue
            image.file_data = file_data
            image.mime_type = mime_type
            image.original_filename = img.url.rsplit("/", 1)[-1][:255] or "cliniccards-image"
    db.flush()
    recompute_images_progress(db, case)


def recompute_images_progress(db: Session, case: TreatmentPlanCase) -> None:
    required_ids = set(
        db.execute(
            select(ImageType.id).where(ImageType.is_active.is_(True), ImageType.is_required.is_(True))
        ).scalars()
    )
    if not required_ids:
        return

    present_ids = set(
        db.execute(
            select(ClinicalImage.image_type_id).where(
                ClinicalImage.case_id == case.id, ClinicalImage.image_type_id.isnot(None)
            )
        ).scalars()
    )
    have = len(required_ids & present_ids)
    percent = round((have / len(required_ids)) * 100)
    case.images_progress_percent = percent

    if percent == 100 and case.status == CaseStatus.ASSIGNED:
        set_case_status(db, case, CaseStatus.IMAGES_READY, reason="all required images present")


def save_uploaded_image(
    db: Session, case: TreatmentPlanCase, image_type_id: uuid.UUID, *, filename: str, mime_type: str, data: bytes
) -> ClinicalImage:
    """Manual upload (Cliniccards not connected yet): creates or replaces
    the one image this case has for a given required-image slot. Reuses
    `recompute_images_progress`/the same 100%-triggers-IMAGES_READY rule
    real Cliniccards-synced images follow."""
    existing = db.execute(
        select(ClinicalImage).where(ClinicalImage.case_id == case.id, ClinicalImage.image_type_id == image_type_id)
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if existing:
        existing.source = ImageSource.UPLOAD
        existing.file_data = data
        existing.thumbnail_data = None
        existing.thumbnail_mime_type = None
        existing.mime_type = mime_type
        existing.original_filename = filename
        existing.external_url = None
        existing.captured_at = now
        image = existing
    else:
        image = ClinicalImage(
            case_id=case.id,
            image_type_id=image_type_id,
            source=ImageSource.UPLOAD,
            file_data=data,
            mime_type=mime_type,
            original_filename=filename,
            captured_at=now,
        )
        db.add(image)
    db.flush()
    recompute_images_progress(db, case)
    return image


def upload_to_pool(db: Session, case: TreatmentPlanCase, files: list[tuple[str, str, bytes]]) -> list[ClinicalImage]:
    """"Hammasini yuklash": files land in the case's "bulut"
    (image_type_id=NULL) first. The caller (bulk_upload_case_images) then
    runs auto_classify_pool_images on the result to try placing each one
    automatically; anything it can't confidently place — or everything, if
    GEMINI_API_KEY isn't configured — stays here for staff to drag/pick
    into the right slot themselves via assign_pool_image_to_slot. Doesn't
    touch progress: only images actually assigned to a required slot count
    toward it."""
    now = datetime.now(timezone.utc)
    images = []
    for filename, mime_type, data in files:
        image = ClinicalImage(
            case_id=case.id,
            image_type_id=None,
            source=ImageSource.UPLOAD,
            file_data=data,
            mime_type=mime_type,
            original_filename=filename,
            captured_at=now,
        )
        db.add(image)
        images.append(image)
    db.flush()
    return images


def _place_image_in_slot(db: Session, case: TreatmentPlanCase, image: ClinicalImage, image_type_id: uuid.UUID) -> None:
    """Shared by manual (assign_pool_image_to_slot) and automatic
    (auto_classify_pool_images) placement: if the slot already had a
    (different) image, the old occupant goes back to the bulut instead of
    being deleted — spec: "xato kiritgan rasmim bulutga qayta qo'shilsin"."""
    existing = db.execute(
        select(ClinicalImage).where(ClinicalImage.case_id == case.id, ClinicalImage.image_type_id == image_type_id)
    ).scalar_one_or_none()
    if existing and existing.id != image.id:
        existing.image_type_id = None  # back to the bulut, not deleted

    image.image_type_id = image_type_id
    db.flush()
    recompute_images_progress(db, case)


def assign_pool_image_to_slot(
    db: Session, case: TreatmentPlanCase, image_type_id: uuid.UUID, pool_image_id: uuid.UUID
) -> ClinicalImage:
    """Moves one "bulut" image into a required-image slot (staff picking it
    by hand — see auto_classify_pool_images for the automatic version)."""
    pool_image = db.execute(
        select(ClinicalImage).where(ClinicalImage.id == pool_image_id, ClinicalImage.case_id == case.id)
    ).scalar_one_or_none()
    if not pool_image:
        raise ValueError("Bulutda bunday rasm topilmadi")
    if pool_image.image_type_id is not None:
        raise ValueError("Bu rasm allaqachon boshqa joyga biriktirilgan")

    _place_image_in_slot(db, case, pool_image, image_type_id)
    return pool_image


def batch_assign_pool_images(
    db: Session,
    case: TreatmentPlanCase,
    assignments: list[tuple[uuid.UUID, uuid.UUID]],
) -> None:
    """Apply the sorter screen's draft in one atomic transaction.

    Validation happens before any slot is changed, so a stale or duplicated
    selection cannot leave half of the case saved.
    """
    type_ids = [image_type_id for image_type_id, _ in assignments]
    image_ids = [image_id for _, image_id in assignments]
    if len(type_ids) != len(set(type_ids)) or len(image_ids) != len(set(image_ids)):
        raise ValueError("Bir rasm yoki joy bir necha marta tanlangan")

    valid_type_ids = set(
        db.execute(
            select(ImageType.id).where(ImageType.id.in_(type_ids), ImageType.is_active.is_(True))
        ).scalars()
    )
    if valid_type_ids != set(type_ids):
        raise ValueError("Rasm turi topilmadi yoki faol emas")

    pool_images = {
        image.id: image
        for image in db.execute(
            select(ClinicalImage).where(
                ClinicalImage.id.in_(image_ids),
                ClinicalImage.case_id == case.id,
                ClinicalImage.image_type_id.is_(None),
            )
        ).scalars()
    }
    if set(pool_images) != set(image_ids):
        raise ValueError("Tanlangan rasmlardan biri bulutda mavjud emas")

    for image_type_id, image_id in assignments:
        _place_image_in_slot(db, case, pool_images[image_id], image_type_id)


async def auto_classify_pool_images(db: Session, case: TreatmentPlanCase, images: list[ClinicalImage]) -> None:
    """Best-effort automatic recognition for freshly-uploaded "bulut" images
    (see app/integrations/image_classifier.py) — tries to place each one
    straight into its slot, with the same non-destructive swap-to-pool
    behavior as assign_pool_image_to_slot. A no-op (images stay in the pool
    for manual sorting, exactly like before this feature existed) if
    GEMINI_API_KEY isn't configured, or per-image if Gemini can't
    confidently classify it.

    Sequential, not parallel: free-tier Gemini API quotas are a handful of
    requests per minute, and a burst of concurrent calls from one bulk
    upload would blow through that immediately."""
    image_types = db.execute(select(ImageType).where(ImageType.is_active.is_(True))).scalars().all()
    if not image_types:
        return
    candidates = [(t.code, t.label) for t in image_types]
    by_code = {t.code: t.id for t in image_types}

    for image in images:
        if image.image_type_id is not None or not image.file_data:
            continue
        code = await classify_image_type(image.file_data, image.mime_type or "image/jpeg", candidates)
        if code and code in by_code:
            _place_image_in_slot(db, case, image, by_code[code])


def assign_case(db: Session, case: TreatmentPlanCase, planner_user_id: uuid.UUID, *, actor_user_id: uuid.UUID, note: str | None = None) -> None:
    """Admin action (spec section 5, Variant A). Atomic: updates the
    assignment, transitions NEW/WAITING_ASSIGNMENT -> ASSIGNED, writes the
    audit entry, and queues the Telegram notification — all in the same
    DB transaction the caller commits."""
    case.responsible_planner_user_id = planner_user_id
    if case.status in (CaseStatus.NEW, CaseStatus.WAITING_ASSIGNMENT):
        set_case_status(db, case, CaseStatus.ASSIGNED, actor_user_id=actor_user_id)
        # Images may have already reached 100% while the case was still
        # unassigned (recompute_images_progress only auto-advances from
        # ASSIGNED, so that check needs re-running now that we just got here).
        recompute_images_progress(db, case)

    write_audit(
        db,
        case_id=case.id,
        actor_user_id=actor_user_id,
        action="assigned",
        details={"planner_user_id": str(planner_user_id), "note": note},
    )
    queue_notification(db, case_id=case.id, recipient_user_id=planner_user_id, type="case_assigned")


def submit_review(
    db: Session,
    case: TreatmentPlanCase,
    *,
    reviewer_user_id: uuid.UUID,
    decision: ReviewDecision,
    plan_version_id: uuid.UUID | None,
    comment: str | None,
) -> None:
    """Doctor review (spec section 23): approve moves the case to READY,
    revision_required sends it back to PLAN_IN_PROGRESS and requires a
    comment. Callers must already have checked the caller holds the DOCTOR
    role (see app.security.deps.require_role) — this function only enforces
    the data-level invariant (comment required on revision)."""
    if decision == ReviewDecision.REVISION_REQUIRED and not (comment and comment.strip()):
        raise ValueError("Revision uchun izoh majburiy")

    db.add(
        Review(
            case_id=case.id,
            plan_version_id=plan_version_id,
            reviewer_user_id=reviewer_user_id,
            decision=decision,
            comment=comment,
        )
    )

    new_status = CaseStatus.READY if decision == ReviewDecision.APPROVE else CaseStatus.PLAN_IN_PROGRESS
    set_case_status(db, case, new_status, actor_user_id=reviewer_user_id)

    write_audit(
        db,
        case_id=case.id,
        actor_user_id=reviewer_user_id,
        action="review_submitted",
        details={"decision": decision.value, "comment": comment},
    )
