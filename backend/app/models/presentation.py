import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDPKMixin
from app.models.enums import PresentationFormat

presentation_format_enum = PGEnum(PresentationFormat, name="presentation_format", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])


class Presentation(Base, UUIDPKMixin):
    """Generated PPTX/PDF record (spec sections 24-25). The generator itself
    (python-pptx) is not implemented yet — see ARCHITECTURE.md Phase 10."""

    __tablename__ = "presentations"

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    format: Mapped[PresentationFormat] = mapped_column(presentation_format_enum, nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    template_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generated_by: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
