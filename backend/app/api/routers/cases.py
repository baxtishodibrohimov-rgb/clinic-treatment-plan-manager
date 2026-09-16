import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.case import TreatmentPlanCase
from app.models.clinic import Clinic
from app.models.cliniccards import CliniccardsPatientCache
from app.models.enums import CaseStatus, ImageSource, ReviewDecision, Role
from app.models.image import ClinicalImage, ImageType
from app.models.finding import Finding
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.schemas.case import (
    AssignCaseRequest,
    AssignFromPoolRequest,
    AuditLogOut,
    CaseDetail,
    CaseListItem,
    ClinicalImageOut,
    DashboardStats,
    DoctorOut,
    FindingOut,
    ImageTypeOut,
    ManualCaseCreateRequest,
    PatientSummary,
    ReviewRequest,
)
from app.security.deps import clinic_scope, get_current_user, require_admin, require_role
from app.services.case_service import (
    assign_case,
    assign_pool_image_to_slot,
    create_manual_case,
    save_uploaded_image,
    submit_review,
    upload_to_pool,
)

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB per photo — clinical photos, not raw video

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _bulk_names(db: Session, cases: list[TreatmentPlanCase]) -> tuple[dict[str, str], dict[uuid.UUID, str]]:
    patient_ids = {c.cliniccards_patient_id for c in cases}
    user_ids = {c.responsible_planner_user_id for c in cases if c.responsible_planner_user_id} | {
        c.primary_doctor_user_id for c in cases if c.primary_doctor_user_id
    }

    patients = (
        db.execute(select(CliniccardsPatientCache).where(CliniccardsPatientCache.cliniccards_patient_id.in_(patient_ids)))
        .scalars()
        .all()
        if patient_ids
        else []
    )
    users = db.execute(select(User).where(User.id.in_(user_ids))).scalars().all() if user_ids else []

    return {p.cliniccards_patient_id: p.full_name for p in patients}, {u.id: u.full_name for u in users}


@router.get("", response_model=list[CaseListItem], dependencies=[Depends(get_current_user)])
def list_cases(db: Session = Depends(get_db), scope_clinic_id: uuid.UUID | None = Depends(clinic_scope)) -> list[CaseListItem]:
    query = select(TreatmentPlanCase).order_by(TreatmentPlanCase.consultation_datetime)
    if scope_clinic_id is not None:
        query = query.where(TreatmentPlanCase.clinic_id == scope_clinic_id)
    cases = db.execute(query).scalars().all()
    patient_names, user_names = _bulk_names(db, cases)
    clinic_names = {c.id: c.name for c in db.execute(select(Clinic)).scalars().all()}

    return [
        CaseListItem(
            id=c.id,
            status=c.status,
            priority=c.priority,
            consultation_datetime=c.consultation_datetime,
            deadline=c.deadline,
            images_progress_percent=c.images_progress_percent,
            patient_name=patient_names.get(c.cliniccards_patient_id, "Noma'lum bemor"),
            doctor_name=c.primary_doctor_name or (user_names.get(c.primary_doctor_user_id) if c.primary_doctor_user_id else None),
            planner_name=user_names.get(c.responsible_planner_user_id) if c.responsible_planner_user_id else None,
            clinic_id=c.clinic_id,
            clinic_name=clinic_names.get(c.clinic_id) if c.clinic_id else None,
        )
        for c in cases
    ]


@router.get("/dashboard-stats", response_model=DashboardStats, dependencies=[Depends(get_current_user)])
def dashboard_stats(db: Session = Depends(get_db), scope_clinic_id: uuid.UUID | None = Depends(clinic_scope)) -> DashboardStats:
    query = select(TreatmentPlanCase)
    if scope_clinic_id is not None:
        query = query.where(TreatmentPlanCase.clinic_id == scope_clinic_id)
    cases = db.execute(query).scalars().all()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    return DashboardStats(
        today_consultations=sum(1 for c in cases if c.consultation_datetime and today_start <= c.consultation_datetime < today_end),
        new_cases=sum(1 for c in cases if c.status in (CaseStatus.NEW, CaseStatus.WAITING_ASSIGNMENT)),
        in_progress=sum(
            1
            for c in cases
            if c.status in (CaseStatus.ASSIGNED, CaseStatus.IMAGES_READY, CaseStatus.ANALYSIS_IN_PROGRESS, CaseStatus.PLAN_IN_PROGRESS)
        ),
        review_pending=sum(1 for c in cases if c.status == CaseStatus.REVIEW_REQUIRED),
        ready=sum(1 for c in cases if c.status == CaseStatus.READY),
        overdue=sum(1 for c in cases if c.status == CaseStatus.OVERDUE),
    )


@router.get("/doctors", response_model=list[DoctorOut], dependencies=[Depends(get_current_user)])
def list_doctors(db: Session = Depends(get_db), scope_clinic_id: uuid.UUID | None = Depends(clinic_scope)) -> list[DoctorOut]:
    """Roster for the manual case-entry form's doctor picker."""
    query = (
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .where(UserRole.role == Role.DOCTOR, User.is_active.is_(True))
        .order_by(User.full_name)
    )
    if scope_clinic_id is not None:
        query = query.where(User.clinic_id == scope_clinic_id)
    doctors = db.execute(query).scalars().unique().all()
    return [DoctorOut(id=d.id, full_name=d.full_name) for d in doctors]


@router.post("/manual", response_model=CaseListItem, status_code=status.HTTP_201_CREATED)
def create_manual_case_endpoint(
    payload: ManualCaseCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CaseListItem:
    """Cliniccards isn't connected yet — this lets staff register a real
    patient/case directly until it is (spec: manual data entry fallback)."""
    if user.is_super_admin:
        if payload.clinic_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "clinic_id majburiy")
        clinic_id = payload.clinic_id
    else:
        clinic_id = user.clinic_id
        if clinic_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sizga hech qanday klinika biriktirilmagan")

    case = create_manual_case(
        db,
        full_name=payload.full_name,
        birth_date=payload.birth_date,
        phone=payload.phone,
        doctor_name=payload.doctor_name,
        consultation_datetime=payload.consultation_datetime,
        clinic_id=clinic_id,
        priority=payload.priority,
    )
    db.commit()
    db.refresh(case)

    clinic_name = db.get(Clinic, clinic_id).name if clinic_id else None
    planner_name = db.get(User, case.responsible_planner_user_id).full_name if case.responsible_planner_user_id else None
    return CaseListItem(
        id=case.id,
        status=case.status,
        priority=case.priority,
        consultation_datetime=case.consultation_datetime,
        deadline=case.deadline,
        images_progress_percent=case.images_progress_percent,
        patient_name=payload.full_name,
        doctor_name=case.primary_doctor_name,
        planner_name=planner_name,
        clinic_id=clinic_id,
        clinic_name=clinic_name,
    )


def _image_out(image: ClinicalImage) -> ClinicalImageOut:
    url = image.external_url if image.source != ImageSource.UPLOAD else f"/api/images/{image.id}/file"
    return ClinicalImageOut(id=image.id, image_type_id=image.image_type_id, external_url=url, source=image.source.value)


def _get_case_or_404(db: Session, case_id: uuid.UUID, user: User) -> TreatmentPlanCase:
    case = db.get(TreatmentPlanCase, case_id)
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case topilmadi")
    if not user.is_super_admin and case.clinic_id != user.clinic_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case topilmadi")
    return case


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> CaseDetail:
    case = _get_case_or_404(db, case_id, user)

    patient = db.execute(
        select(CliniccardsPatientCache).where(CliniccardsPatientCache.cliniccards_patient_id == case.cliniccards_patient_id)
    ).scalar_one_or_none()

    planner_name = None
    if case.responsible_planner_user_id:
        planner = db.get(User, case.responsible_planner_user_id)
        planner_name = planner.full_name if planner else None

    image_types = db.execute(select(ImageType).where(ImageType.is_active.is_(True)).order_by(ImageType.sort_order)).scalars().all()
    all_images = db.execute(select(ClinicalImage).where(ClinicalImage.case_id == case.id)).scalars().all()
    images = [i for i in all_images if i.image_type_id is not None]
    pool_images = [i for i in all_images if i.image_type_id is None]
    findings = db.execute(select(Finding).where(Finding.case_id == case.id).order_by(Finding.sort_order)).scalars().all()
    audit = db.execute(select(AuditLog).where(AuditLog.case_id == case.id).order_by(AuditLog.created_at)).scalars().all()

    return CaseDetail(
        id=case.id,
        status=case.status,
        priority=case.priority,
        consultation_datetime=case.consultation_datetime,
        deadline=case.deadline,
        images_progress_percent=case.images_progress_percent,
        patient=PatientSummary(**{
            "cliniccards_patient_id": patient.cliniccards_patient_id,
            "full_name": patient.full_name,
            "birth_date": patient.birth_date,
            "phone": patient.phone,
        }) if patient else None,
        doctor_name=case.primary_doctor_name,
        planner_id=case.responsible_planner_user_id,
        planner_name=planner_name,
        image_types=[ImageTypeOut(id=t.id, code=t.code, label=t.label, category=t.category.value, is_required=t.is_required) for t in image_types],
        images=[_image_out(i) for i in images],
        pool_images=[_image_out(i) for i in pool_images],
        findings=[FindingOut.model_validate(f) for f in findings],
        audit_log=[AuditLogOut.model_validate(a) for a in audit],
    )


async def _read_upload(file: UploadFile) -> tuple[str, str, bytes]:
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{file.filename}: fayl juda katta (15 MB dan oshmasin)")
    return file.filename or "rasm", file.content_type or "application/octet-stream", data


@router.post("/{case_id}/images/bulk-upload", response_model=CaseDetail)
async def bulk_upload_case_images(
    case_id: uuid.UUID, files: list[UploadFile] = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CaseDetail:
    """"Hammasini yuklash" — there is no image classifier, so files land in
    the case's "bulut" (image_type_id=NULL) instead of being guessed into a
    slot. Staff assign each one to the right slot via assign-from-pool."""
    case = _get_case_or_404(db, case_id, user)
    read_files = [await _read_upload(f) for f in files]
    upload_to_pool(db, case, read_files)
    db.commit()
    return get_case(case_id, db, user)


@router.post("/{case_id}/images/{image_type_id}/assign-from-pool", response_model=CaseDetail)
def assign_from_pool_endpoint(
    case_id: uuid.UUID,
    image_type_id: uuid.UUID,
    payload: AssignFromPoolRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseDetail:
    """Moves one "bulut" image into a required-image slot; if that slot was
    already filled, the previous occupant returns to the bulut instead of
    being discarded (see assign_pool_image_to_slot)."""
    case = _get_case_or_404(db, case_id, user)
    if not db.get(ImageType, image_type_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rasm turi topilmadi")
    try:
        assign_pool_image_to_slot(db, case, image_type_id, payload.pool_image_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None
    db.commit()
    return get_case(case_id, db, user)


@router.post("/{case_id}/images/{image_type_id}", response_model=CaseDetail)
async def upload_case_image(
    case_id: uuid.UUID,
    image_type_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseDetail:
    """Replace/set a single required-image slot — used to fix a slot the
    bulk upload above assigned incorrectly, or to add one photo at a time."""
    case = _get_case_or_404(db, case_id, user)
    if not db.get(ImageType, image_type_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rasm turi topilmadi")
    filename, mime_type, data = await _read_upload(file)
    save_uploaded_image(db, case, image_type_id, filename=filename, mime_type=mime_type, data=data)
    db.commit()
    return get_case(case_id, db, user)


@router.post("/{case_id}/assign", status_code=status.HTTP_204_NO_CONTENT)
def assign(case_id: uuid.UUID, payload: AssignCaseRequest, db: Session = Depends(get_db), user: User = Depends(require_admin)) -> None:
    case = _get_case_or_404(db, case_id, user)
    planner = db.get(User, payload.planner_user_id)
    if not planner or Role.PLANNER not in planner.role_names:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tanlangan foydalanuvchi planner emas")
    if planner.clinic_id != case.clinic_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Planner boshqa klinikaga tegishli")
    assign_case(db, case, payload.planner_user_id, actor_user_id=user.id, note=payload.note)
    db.commit()


@router.post("/{case_id}/review", status_code=status.HTTP_204_NO_CONTENT)
def review(
    case_id: uuid.UUID,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.DOCTOR)),
) -> None:
    case = _get_case_or_404(db, case_id, user)
    try:
        decision = ReviewDecision(payload.decision)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Noto'g'ri qaror") from None

    try:
        submit_review(
            db,
            case,
            reviewer_user_id=user.id,
            decision=decision,
            plan_version_id=payload.plan_version_id,
            comment=payload.comment,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None
    db.commit()
