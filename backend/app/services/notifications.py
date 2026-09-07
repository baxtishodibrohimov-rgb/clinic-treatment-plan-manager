import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.notification import Notification


def queue_notification(
    db: Session,
    *,
    case_id: uuid.UUID | None,
    type: str,
    recipient_user_id: uuid.UUID | None = None,
    recipient_telegram_id: int | None = None,
    payload: dict | None = None,
) -> None:
    """Outbox insert — see app/models/notification.py for why nothing here
    talks to Telegram directly."""
    db.add(
        Notification(
            case_id=case_id,
            recipient_user_id=recipient_user_id,
            recipient_telegram_id=recipient_telegram_id,
            channel="telegram",
            type=type,
            payload=payload or {},
            created_at=datetime.now(timezone.utc),
        )
    )
