from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class Clinic(Base, UUIDPKMixin, TimestampMixin):
    """A clinic/branch (spec: multi-branch support). Every staff User and
    every TreatmentPlanCase belongs to exactly one Clinic; SUPER_ADMIN users
    have clinic_id = NULL and see/manage every clinic.

    All clinics share one Cliniccards account — there is no per-clinic API
    credential. `cliniccards_branch_code` is a best-effort key the sync
    service tries to match against the raw appointment/patient payload to
    tell clinics apart (see app/services/sync_service.py); until real
    Cliniccards API docs show what that field is actually called, unmatched
    appointments fall back to whichever clinic has `is_default=True`.
    """

    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cliniccards_branch_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
