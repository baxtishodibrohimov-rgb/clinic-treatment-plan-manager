from datetime import datetime

from app.integrations.telegram.client import escape_html


def _fmt(dt: datetime | None) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")


def build_message(notification_type: str, *, patient_name: str | None, consultation_at: datetime | None, deadline_at: datetime | None, status: str | None) -> str:
    name = escape_html(patient_name or "Noma'lum bemor")
    consultation = _fmt(consultation_at)
    deadline = _fmt(deadline_at)

    if notification_type == "case_assigned":
        return (
            "🦷 <b>Yangi treatment plan sizga biriktirildi.</b>\n\n"
            f"Bemor: <b>{name}</b>\n"
            f"2-konsultatsiya: <b>{consultation}</b>\n"
            f"Deadline: <b>{deadline}</b>\n\n"
            "Treatment plan va prezentatsiyani konsultatsiyagacha tayyorlang."
        )
    if notification_type == "reminder_before_consultation":
        return (
            "⏰ <b>Eslatma</b>\n\n"
            f"Bemor: <b>{name}</b>\n"
            f"2-konsultatsiya: <b>{consultation}</b>\n"
            f"Joriy status: <b>{status or '—'}</b>\n\n"
            "Treatment plan hali READY emas — konsultatsiyagacha tayyorlang."
        )
    if notification_type == "case_overdue":
        return (
            "🔴 <b>OVERDUE — deadline o'tdi</b>\n\n"
            f"Bemor: <b>{name}</b>\n"
            f"2-konsultatsiya: <b>{consultation}</b>\n"
            f"Deadline: <b>{deadline}</b>\n"
            f"Joriy status: <b>{status or '—'}</b>"
        )
    if notification_type == "review_requested":
        return f"📋 <b>Treatment plan review uchun tayyor.</b>\n\nBemor: <b>{name}</b>\n2-konsultatsiya: <b>{consultation}</b>"
    return f"{escape_html(notification_type)} — {name}"
