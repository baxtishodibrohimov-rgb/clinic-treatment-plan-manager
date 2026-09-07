import uuid
from datetime import datetime

from sqlalchemy import ARRAY, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import NotificationStatus, ReminderTriggerType

notification_status_enum = PGEnum(NotificationStatus, name="notification_status", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])
reminder_trigger_enum = PGEnum(ReminderTriggerType, name="reminder_trigger_type", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])


class Notification(Base, UUIDPKMixin):
    """Outbox pattern: every notification-worthy event only ever INSERTs a
    row here (status=pending). A single Celery task is the only code that
    actually talks to Telegram, formats messages, and marks rows sent/
    failed — see app/jobs/tasks.py:dispatch_notifications. This means a
    Telegram outage never blocks the request that triggered the
    notification, and nothing is lost — it just stays pending for the next
    run."""

    __tablename__ = "notifications"

    case_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True)
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Fallback for recipients who aren't a User row (kept for parity with the
    # outbox design; unused for now since every recipient here is a User).
    recipient_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="telegram")
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[NotificationStatus] = mapped_column(notification_status_enum, nullable=False, default=NotificationStatus.PENDING, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReminderRule(Base, UUIDPKMixin, TimestampMixin):
    """Fully admin-configurable reminder schedule (spec section 7) — nothing
    about when/who to remind is hardcoded."""

    __tablename__ = "reminder_rules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_type: Mapped[ReminderTriggerType] = mapped_column(reminder_trigger_enum, nullable=False)
    offset_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notify_roles: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=lambda: ["planner"])
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ReminderSentLog(Base, UUIDPKMixin):
    """Dedup log so each rule fires at most once per case."""

    __tablename__ = "reminder_sent_log"
    __table_args__ = (UniqueConstraint("case_id", "rule_id", name="uq_reminder_sent_case_rule"),)

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reminder_rules.id", ondelete="CASCADE"), nullable=False)
