import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import CaseStatus, Priority

case_status_enum = PGEnum(CaseStatus, name="case_status", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])
priority_enum = PGEnum(Priority, name="priority", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])

# The state machine (spec section 4) is enforced in code, not the database —
# see app/services/case_service.py:validate_transition. Every write to
# TreatmentPlanCase.status goes through that one function, since (unlike the
# earlier Supabase/RLS build) nothing outside the FastAPI service layer ever
# writes to this table directly.
ALLOWED_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.NEW: {CaseStatus.WAITING_ASSIGNMENT, CaseStatus.ASSIGNED, CaseStatus.OVERDUE},
    CaseStatus.WAITING_ASSIGNMENT: {CaseStatus.ASSIGNED, CaseStatus.OVERDUE},
    CaseStatus.ASSIGNED: {CaseStatus.IMAGES_READY, CaseStatus.OVERDUE},
    CaseStatus.IMAGES_READY: {CaseStatus.ANALYSIS_IN_PROGRESS, CaseStatus.OVERDUE},
    CaseStatus.ANALYSIS_IN_PROGRESS: {CaseStatus.PLAN_IN_PROGRESS, CaseStatus.OVERDUE},
    CaseStatus.PLAN_IN_PROGRESS: {CaseStatus.REVIEW_REQUIRED, CaseStatus.OVERDUE},
    CaseStatus.REVIEW_REQUIRED: {CaseStatus.PLAN_IN_PROGRESS, CaseStatus.READY, CaseStatus.OVERDUE},
    CaseStatus.READY: {CaseStatus.CONSULTATION_COMPLETED},
    CaseStatus.CONSULTATION_COMPLETED: set(),
    CaseStatus.OVERDUE: {
        CaseStatus.ASSIGNED,
        CaseStatus.IMAGES_READY,
        CaseStatus.ANALYSIS_IN_PROGRESS,
        CaseStatus.PLAN_IN_PROGRESS,
        CaseStatus.REVIEW_REQUIRED,
        CaseStatus.READY,
    },
}


class TreatmentPlanCase(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "cases"

    cliniccards_patient_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("cliniccards_patients.cliniccards_patient_id"), nullable=False, index=True
    )
    # UNIQUE — this is the idempotency guarantee from spec section 3: one
    # Cliniccards appointment can never produce two cases.
    cliniccards_appointment_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("cliniccards_appointments.cliniccards_appointment_id"), nullable=False, unique=True
    )
    consultation_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    primary_doctor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    primary_doctor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsible_planner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[CaseStatus] = mapped_column(case_status_enum, nullable=False, default=CaseStatus.NEW, index=True)
    priority: Mapped[Priority] = mapped_column(priority_enum, nullable=False, default=Priority.NORMAL)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    images_progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
