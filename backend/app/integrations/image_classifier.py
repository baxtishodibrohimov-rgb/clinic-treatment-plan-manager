"""Automatic image-type recognition for the "bulut" (pool) upload flow, via
Google Gemini's vision API.

Optional: if GEMINI_API_KEY isn't configured, classify_image_type() always
returns None and every caller falls back to its original behavior (leave
the image in the pool for staff to sort by hand) — nothing breaks without
this configured, same pattern as TELEGRAM_BOT_TOKEN being optional.

Calls Gemini's REST API directly over httpx.AsyncClient rather than
Google's official (synchronous) SDK, so this never blocks the shared event
loop — see sync_service.sync_second_consultations_blocking's docstring for
why a blocking call anywhere in this app is a real, previously-confirmed
bug, not just a style preference.

Never invents or guesses at clinical categories: the candidate list this
asks Gemini to choose from is always exactly the clinic's own
`image_types` catalog (admin-configured, seen in Sozlamalar), never
anything made up here.
"""
import base64
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_PROMPT_TEMPLATE = (
    "Bu stomatologik klinikada olingan tibbiy rasm (bemorning tishi, yuzi yoki "
    "rentgeni). Quyidagi ro'yxatdan aynan shu rasmga eng mos keladigan bitta "
    "turni tanlang va FAQAT uning kodini yozing, boshqa hech qanday matn "
    "yozmang. Agar hech biriga ishonchli mos kelmasa, faqat NONE deb yozing.\n\n"
    "{options}"
)


async def classify_image_type(image_bytes: bytes, mime_type: str, candidates: list[tuple[str, str]]) -> str | None:
    """candidates: (code, label) pairs for every active image type in the
    clinic's own catalog. Returns the matching code, or None if Gemini
    isn't configured, the call fails, or nothing is a confident match."""
    settings = get_settings()
    if not settings.gemini_api_key or not candidates:
        return None

    options = "\n".join(f"- {code}: {label}" for code, label in candidates)
    prompt = _PROMPT_TEMPLATE.format(options=options)
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode("ascii")}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 20},
    }
    url = GEMINI_API_URL.format(model=settings.gemini_model)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, params={"key": settings.gemini_api_key}, json=body)
            response.raise_for_status()
            data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:  # noqa: BLE001 — classification is best-effort, never fatal to the upload
        logger.exception("Gemini image classification failed")
        return None

    code = text.strip().strip('"').strip("'")
    valid_codes = {c for c, _ in candidates}
    return code if code in valid_codes else None
