"""Minimal Telegram Bot API client — this is a fresh project so it talks to
Telegram directly (api.telegram.org) with TELEGRAM_BOT_TOKEN, rather than
through any third-party gateway."""
from html import escape

import httpx

from app.config import get_settings


class TelegramNotConfigured(RuntimeError):
    pass


async def send_message(chat_id: int, text: str, button_url: str | None = None, button_label: str = "Ochish") -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise TelegramNotConfigured("TELEGRAM_BOT_TOKEN not configured")

    payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if button_url:
        payload["reply_markup"] = {"inline_keyboard": [[{"text": button_label, "url": button_url}]]}

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(url, json=payload)
        res.raise_for_status()


def escape_html(text: str) -> str:
    return escape(text, quote=False)
