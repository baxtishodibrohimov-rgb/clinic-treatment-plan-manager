from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class CliniccardsPatientCache(Base, UUIDPKMixin, TimestampMixin):
    """Thin, denormalized cache of whatever Cliniccards returns — populated
    and overwritten by the sync job. Images/documents are referenced by URL,
    never copied, per the spec."""

    __tablename__ = "cliniccards_patients"

    cliniccards_patient_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CliniccardsAppointmentCache(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "cliniccards_appointments"

    cliniccards_appointment_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    cliniccards_patient_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("cliniccards_patients.cliniccards_patient_id", ondelete="CASCADE"), nullable=False
    )
    appointment_type_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    appointment_type_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
