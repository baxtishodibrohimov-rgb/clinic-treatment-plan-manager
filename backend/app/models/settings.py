from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import AssignmentMode, AssignmentStrategy

assignment_mode_enum = PGEnum(AssignmentMode, name="assignment_mode", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])
assignment_strategy_enum = PGEnum(AssignmentStrategy, name="assignment_strategy", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])


class AssignmentConfig(Base):
    """Singleton row (id=1) — the assignment algorithm itself lives in code
    (app/services/assignment.py) so it stays easy to extend; this table only
    holds the admin-configurable knobs (spec section 5)."""

    __tablename__ = "assignment_config"
    __table_args__ = (CheckConstraint("id = 1", name="ck_assignment_config_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    mode: Mapped[AssignmentMode] = mapped_column(assignment_mode_enum, nullable=False, default=AssignmentMode.MANUAL)
    strategy: Mapped[AssignmentStrategy] = mapped_column(
        assignment_strategy_enum, nullable=False, default=AssignmentStrategy.LEAST_WORKLOAD
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AppSetting(Base):
    """Free-form non-secret settings (which Cliniccards appointment-type
    code(s) count as "2nd consultation", presentation branding, ...).
    Secrets never live here — only in real environment variables (see
    app/config.py + .env.example)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
