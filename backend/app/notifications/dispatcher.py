"""Outbox dispatcher: sends every pending Notification over Telegram.

Producers (assignment, auto-assignment, reminders, review flow) only ever
INSERT a Notification row — this is the single place that actually talks to
Telegram, so message formatting stays in one spot and a Telegram outage just
leaves rows pending for the next run instead of losing them.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.integrations.telegram.client import TelegramNotConfigured, send_message
from app.models.case import TreatmentPlanCase
from app.models.cliniccards import CliniccardsPatientCache
from app.models.enums import NotificationStatus
from app.models.notification import Notification
from app.models.user import User
from app.notifications.templates import build_message


async def dispatch_pending(db: Session, limit: int = 30) -> dict:
    settings = get_settings()
    pending = (
        db.execute(
            select(Notification).where(Notification.status == NotificationStatus.PENDING).order_by(Notification.created_at).limit(limit)
        )
        .scalars()
        .all()
    )

    sent = 0
    failed = 0

    for n in pending:
        try:
            recipient_telegram_id = n.recipient_telegram_id
            if not recipient_telegram_id and n.recipient_user_id:
                user = db.get(User, n.recipient_user_id)
                recipient_telegram_id = user.telegram_id if user else None

            if not recipient_telegram_id:
                n.status = NotificationStatus.FAILED
                n.error = "no usable recipient"
                failed += 1
                continue

            patient_name = None
            case: TreatmentPlanCase | None = None
            if n.case_id:
                case = db.get(TreatmentPlanCase, n.case_id)
                if case:
                    patient = db.execute(
                        select(CliniccardsPatientCache).where(
                            CliniccardsPatientCache.cliniccards_patient_id == case.cliniccards_patient_id
                        )
                    ).scalar_one_or_none()
                    patient_name = patient.full_name if patient else None

            text = build_message(
                n.type,
                patient_name=patient_name,
                consultation_at=case.consultation_datetime if case else None,
                deadline_at=case.deadline if case else None,
                status=case.status.value if case else None,
            )
            button_url = f"{settings.app_base_url.rstrip('/')}/cases/{n.case_id}" if n.case_id else None

            await send_message(int(recipient_telegram_id), text, button_url=button_url, button_label="PLAN'NI OCHISH")

            n.status = NotificationStatus.SENT
            n.sent_at = datetime.now(timezone.utc)
            sent += 1
        except TelegramNotConfigured as e:
            n.status = NotificationStatus.FAILED
            n.error = str(e)
            failed += 1
        except Exception as e:  # noqa: BLE001 — one bad notification must not abort the batch
            n.status = NotificationStatus.FAILED
            n.error = str(e)
            failed += 1

    db.commit()
    return {"total": len(pending), "sent": sent, "failed": failed}
