import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import ImageCategory, ImageSource

image_category_enum = PGEnum(ImageCategory, name="image_category", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])
image_source_enum = PGEnum(ImageSource, name="image_source", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])


class ImageType(Base, UUIDPKMixin, TimestampMixin):
    """Configurable required-image-type catalog (spec section 10) — admin
    can add new types later; nothing here is hardcoded into application
    logic beyond the seeded defaults."""

    __tablename__ = "image_types"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[ImageCategory] = mapped_column(image_category_enum, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ClinicalImage(Base, UUIDPKMixin):
    __tablename__ = "clinical_images"
    __table_args__ = (UniqueConstraint("case_id", "cliniccards_document_id", name="uq_clinical_images_case_doc"),)

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    image_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("image_types.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[ImageSource] = mapped_column(image_source_enum, nullable=False, default=ImageSource.CLINICCARDS)
    cliniccards_document_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
