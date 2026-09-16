import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
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
    """One row per anatomical tooth position (FDI quadrant 1-4 x position
    1-8 = 32 positions per chart, auto-created when a case's dental chart is
    first opened — see app/services/analysis_service.py).

    `dentition` is the ONLY state a position holds:
      - "permanent" — showing the permanent-tooth number (any position 1-8)
      - "primary"   — showing the primary/baby-tooth number (position 1-5 only;
                       primary teeth never occupy position 6-8)
      - NULL        — empty/missing, nothing shown

    A single click always sets this to NULL. A double click toggles it:
    position <= 5 toggles primary <-> permanent; position 6-8 toggles
    NULL <-> permanent (there is no primary variant to toggle to there).
    This lets one chart represent mixed dentition (a child with some baby
    teeth still in place and some already replaced by permanent teeth).
    """

    __tablename__ = "tooth_status"
    __table_args__ = (UniqueConstraint("dental_chart_id", "quadrant", "position", name="uq_tooth_status_chart_quadrant_position"),)

    dental_chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dental_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quadrant: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=upper-right 2=upper-left 3=lower-left 4=lower-right (FDI permanent quadrant numbering)
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-8, counted from the midline outward
    dentition: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "permanent" | "primary" | NULL
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
