import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.case import TreatmentPlanCase
from app.models.clinic import Clinic
from app.models.cliniccards import CliniccardsPatientCache
from app.models.enums import CaseStatus, ReviewDecision, Role
from app.models.image import ClinicalImage, ImageType
from app.models.finding import Finding
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.case import (
    AssignCaseRequest,
    AuditLogOut,
    CaseDetail,
    CaseListItem,
    ClinicalImageOut,
    DashboardStats,
    FindingOut,
    ImageTypeOut,
    PatientSummary,
    ReviewRequest,
)
from app.security.deps import clinic_scope, get_current_user, require_admin, require_role
from app.services.case_service import assign_case, submit_review

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
    images = db.execute(select(ClinicalImage).where(ClinicalImage.case_id == case.id)).scalars().all()
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
        images=[ClinicalImageOut.model_validate(i) for i in images],
        findings=[FindingOut.model_validate(f) for f in findings],
        audit_log=[AuditLogOut.model_validate(a) for a in audit],
    )


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
