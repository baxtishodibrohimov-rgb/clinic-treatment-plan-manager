"""Cliniccards webhook receiver (spec section 2). Protected by a shared
secret header rather than user auth, since the caller is Cliniccards, not a
logged-in user. Real payload shape is unknown until their API docs are
provided, so this accepts a small generic envelope and re-runs the same
idempotent sync path as the poller for just that one appointment."""
from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.orm import Session
from fastapi import Depends

from app.config import get_settings
from app.database import get_db
from app.integrations.cliniccards.factory import get_cliniccards_adapter
from app.models.enums import SyncType
from app.services.sync_service import sync_second_consultations

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/cliniccards")
async def cliniccards_webhook(
    payload: dict,
    db: Session = Depends(get_db),
    x_cliniccards_signature: str | None = Header(default=None),
) -> dict:
    settings = get_settings()
    if settings.cliniccards_webhook_secret and x_cliniccards_signature != settings.cliniccards_webhook_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")

    appointment_id = (
        payload.get("appointmentId")
        or payload.get("appointment_id")
        or (payload.get("appointment") or {}).get("id")
        or (payload.get("appointment") or {}).get("appointmentId")
    )
    if not appointment_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "appointmentId missing in payload")

    adapter = get_cliniccards_adapter()
    return await sync_second_consultations(db, adapter, SyncType.WEBHOOK, appointment_id)
