import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import AnswerType

answer_type_enum = PGEnum(AnswerType, name="answer_type", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])


class AnalysisTemplate(Base, UUIDPKMixin, TimestampMixin):
    """The flexible clinical template engine (spec sections 14/15). No rows
    describing actual clinical checklists are seeded — those are only ever
    entered by an admin, or imported later from the clinic's own manual."""

    __tablename__ = "analysis_templates"

    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("image_types.id", ondelete="CASCADE"), nullable=True, index=True
    )
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer_type: Mapped[AnswerType] = mapped_column(answer_type_enum, nullable=False)
    options: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    measurement_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    annotation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    severity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    clinical_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    presentation_text_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AnalysisAnswer(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "analysis_answers"

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinical_images.id", ondelete="CASCADE"), nullable=True, index=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_templates.id", ondelete="SET NULL"), nullable=True
    )
    answer_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    measurement_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ImageAnnotation(Base, UUIDPKMixin, TimestampMixin):
    """Annotation shapes (lines/points/measurements) as versioned JSON, kept
    separate from the original image (spec section 12/43)."""

    __tablename__ = "image_annotations"

    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinical_images.id", ondelete="CASCADE"), nullable=False, index=True
    )
    annotation_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
