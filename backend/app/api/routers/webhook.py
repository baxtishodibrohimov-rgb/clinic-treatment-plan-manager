"""Cliniccards webhook receiver (spec section 2). Protected by a shared
secret header rather than user auth, since the caller is Cliniccards, not a
logged-in user. Real payload shape is unknown until their API docs are
provided, so this accepts a small generic envelope and re-runs the same
idempotent sync path as the poller for just that one appointment."""
import asyncio

from fastapi import APIRouter, Header, HTTPException, status

from app.config import get_settings
from app.models.enums import SyncType
from app.services.sync_service import sync_second_consultations_blocking

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/cliniccards")
async def cliniccards_webhook(
    payload: dict,
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

    # Runs on its own thread + event loop so a webhook (which Cliniccards
    # can fire often) doesn't freeze the shared event loop — and every
    # other user's request — for however long the sync takes. See
    # sync_second_consultations_blocking's docstring.
    return await asyncio.to_thread(sync_second_consultations_blocking, SyncType.WEBHOOK, appointment_id)
