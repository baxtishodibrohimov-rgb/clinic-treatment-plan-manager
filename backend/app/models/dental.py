import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class DentalChart(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "dental_charts"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    numbering_system: Mapped[str] = mapped_column(String(20), nullable=False, default="FDI")


class ToothStatus(Base, UUIDPKMixin, TimestampMixin):
    """Per-tooth status (present/missing/permanent/deciduous/unerupted/
    impacted/...) kept as free text per spec section 18 — the exact
    vocabulary comes from the clinical manual, not hardcoded here."""

    __tablename__ = "tooth_status"
    __table_args__ = (UniqueConstraint("dental_chart_id", "tooth_code", name="uq_tooth_status_chart_tooth"),)

    dental_chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dental_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tooth_code: Mapped[str] = mapped_column(String(10), nullable=False)  # FDI numbering, e.g. "11", "48"
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
