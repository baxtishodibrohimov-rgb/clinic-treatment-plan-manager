import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import CaseStatus, Priority


class PatientSummary(BaseModel):
    cliniccards_patient_id: str
    full_name: str
    birth_date: date | None
    phone: str | None


class CaseListItem(BaseModel):
    id: uuid.UUID
    status: CaseStatus
    priority: Priority
    consultation_datetime: datetime | None
    deadline: datetime | None
    images_progress_percent: int
    patient_name: str
    doctor_name: str | None
    planner_name: str | None
    clinic_id: uuid.UUID | None = None
    clinic_name: str | None = None
    face_photo_url: str | None = None


class ImageTypeOut(BaseModel):
    id: uuid.UUID
    code: str
    label: str
    category: str
    is_required: bool

    model_config = {"from_attributes": True}


class ClinicalImageOut(BaseModel):
    id: uuid.UUID
    image_type_id: uuid.UUID | None
    external_url: str | None
    source: str

    model_config = {"from_attributes": True}


class FindingOut(BaseModel):
    id: uuid.UUID
    category: str
    description: str
    severity: str | None
    is_confirmed: bool
    source_answer_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class AuditLogOut(BaseModel):
    action: str
    details: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseDetail(BaseModel):
    id: uuid.UUID
    status: CaseStatus
    priority: Priority
    consultation_datetime: datetime | None
    deadline: datetime | None
    images_progress_percent: int
    patient: PatientSummary | None
    doctor_name: str | None
    planner_id: uuid.UUID | None
    planner_name: str | None
    image_types: list[ImageTypeOut]
    images: list[ClinicalImageOut]
    pool_images: list[ClinicalImageOut]
    findings: list[FindingOut]
    audit_log: list[AuditLogOut]


class AssignFromPoolRequest(BaseModel):
    pool_image_id: uuid.UUID


class AssignCaseRequest(BaseModel):
    planner_user_id: uuid.UUID
    note: str | None = None


class ManualCaseCreateRequest(BaseModel):
    full_name: str
    birth_date: date | None = None
    phone: str | None = None
    doctor_name: str | None = None
    consultation_datetime: datetime
    priority: Priority = Priority.NORMAL
    # Required only for SUPER_ADMIN (who has no clinic of their own);
    # non-super-admins are always locked to their own clinic.
    clinic_id: uuid.UUID | None = None


class ManualCaseFromCliniccardsRequest(BaseModel):
    """Staff already knows the patient's real Cliniccards card number and
    wants to open a case for them right now, instead of waiting for their
    2nd-visit appointment to sync automatically."""

    cliniccards_patient_id: str
    doctor_name: str | None = None
    consultation_datetime: datetime
    priority: Priority = Priority.NORMAL
    clinic_id: uuid.UUID | None = None


class DoctorOut(BaseModel):
    id: uuid.UUID
    full_name: str


class ReviewRequest(BaseModel):
    plan_version_id: uuid.UUID | None = None
    decision: str  # "approve" | "revision_required"
    comment: str | None = None


class DashboardStats(BaseModel):
    today_consultations: int
    new_cases: int
    in_progress: int
    review_pending: int
    ready: int
    overdue: int


class DailyConsultationCount(BaseModel):
    date: date
    count: int
