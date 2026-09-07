import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import ReviewDecision

review_decision_enum = PGEnum(ReviewDecision, name="review_decision", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])


class TreatmentProblem(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "treatment_problems"

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TreatmentObjective(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "treatment_objectives"

    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treatment_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    objective_text: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TreatmentPlan(Base, UUIDPKMixin, TimestampMixin):
    """A named plan variant for a case (spec section 22: "Plan A / Plan B /
    Alternative"). Full history of edits lives in TreatmentPlanVersion."""

    __tablename__ = "treatment_plans"

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_label: Mapped[str] = mapped_column(String(50), nullable=False, default="A")
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class TreatmentPlanVersion(Base, UUIDPKMixin):
    __tablename__ = "treatment_plan_versions"
    __table_args__ = (UniqueConstraint("plan_id", "version_no", name="uq_plan_version"),)

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treatment_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Review(Base, UUIDPKMixin):
    """Doctor review decision (spec section 23)."""

    __tablename__ = "reviews"

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treatment_plan_versions.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decision: Mapped[ReviewDecision] = mapped_column(review_decision_enum, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
