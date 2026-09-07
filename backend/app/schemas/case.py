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
    findings: list[FindingOut]
    audit_log: list[AuditLogOut]


class AssignCaseRequest(BaseModel):
    planner_user_id: uuid.UUID
    note: str | None = None


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
