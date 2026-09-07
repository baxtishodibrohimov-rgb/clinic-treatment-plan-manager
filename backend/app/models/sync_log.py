from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDPKMixin
from app.models.enums import SyncStatus, SyncType

sync_type_enum = PGEnum(SyncType, name="sync_type", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])
sync_status_enum = PGEnum(SyncStatus, name="sync_status", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])


class IntegrationSyncLog(Base, UUIDPKMixin):
    __tablename__ = "integration_sync_log"

    source: Mapped[str] = mapped_column(String(50), nullable=False, default="cliniccards")
    sync_type: Mapped[SyncType] = mapped_column(sync_type_enum, nullable=False)
    status: Mapped[SyncStatus] = mapped_column(sync_status_enum, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cases_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
