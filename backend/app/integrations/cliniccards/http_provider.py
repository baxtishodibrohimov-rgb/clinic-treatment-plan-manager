"""Cliniccards REST client mapped to the official public API."""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
from urllib.parse import quote
import httpx
from app.config import Settings
from app.integrations.cliniccards.base import CliniccardsAdapter
from app.integrations.cliniccards.types import CliniccardsAppointment, CliniccardsDocument, CliniccardsImage, CliniccardsPatient, GetAppointmentsParams

def _dt(value: Any) -> datetime | None:
    if not value: return None
    try: parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError: return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None

def _as_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list): return payload
    if isinstance(payload, dict):
        data = payload.get("data", payload.get("items", []))
        return data if isinstance(data, list) else []
    return []

def _limited(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    return str(value)[:limit]

def _stable_id(value: Any) -> str:
    text = str(value or "")
    return text if len(text) <= 255 else sha256(text.encode("utf-8")).hexdigest()

def _map_patient(raw: dict[str, Any]) -> CliniccardsPatient:
    name = " ".join(str(raw.get(k) or "").strip() for k in ("lastname", "firstname", "middlename")).strip()
    return CliniccardsPatient(
        str(raw.get("patient_id") or raw.get("id") or ""),
        _limited(name or raw.get("name") or "", 255) or "",
        _date(raw.get("birthday") or raw.get("birth_date")),
        _limited(raw.get("phone"), 64),
        _dt(raw.get("date_created")),
        raw,
    )

def _map_appointment(raw: dict[str, Any]) -> CliniccardsAppointment:
    scheduled = _dt(raw.get("visit_start"))
    if not scheduled: raise ValueError("Cliniccards visit_start is missing or invalid")
    note = raw.get("note")
    return CliniccardsAppointment(
        str(raw.get("visit_id") or raw.get("id") or ""),
        str(raw.get("patient_id") or ""),
        _limited(raw.get("doctor"), 255),
        "visit",
        _limited(note or "Visit", 255) or "Visit",
        scheduled,
        str(note) if note is not None else None,
        raw,
    )

def _map_file(raw: dict[str, Any], patient_id: str) -> CliniccardsImage:
    name = str(raw.get("file") or raw.get("original") or "")
    return CliniccardsImage(
        _stable_id(raw.get("file_id") or raw.get("id") or name),
        patient_id,
        _limited(raw.get("stage") or raw.get("comments") or raw.get("original"), 255),
        name[:1024],
        _dt(raw.get("date_uploaded")),
    )

class HttpCliniccardsAdapter(CliniccardsAdapter):
    def __init__(self, settings: Settings):
        if not settings.cliniccards_api_url or not settings.cliniccards_api_key: raise RuntimeError("CLINICCARDS_API_URL / CLINICCARDS_API_KEY not configured")
        self._settings = settings
        self._client = httpx.AsyncClient(base_url=settings.cliniccards_api_url.rstrip("/"), headers={"Accept":"application/json", "Content-Type":"application/json", settings.cliniccards_api_key_header:settings.cliniccards_api_key}, timeout=45)

    async def _get(self, path: str, params: dict[str, Any] | None = None, json_response: bool = True) -> Any:
        response = await self._client.get(path, params=params); response.raise_for_status()
        if not json_response: return response
        payload = response.json()
        if isinstance(payload, dict) and payload.get("result") == "fail": raise RuntimeError(str(payload.get("error") or "Cliniccards API error"))
        return payload

    async def get_patients(self) -> list[CliniccardsPatient]:
        return [_map_patient(row) for row in _as_list(await self._get(self._settings.cliniccards_patients_path))]

    async def get_patient(self, patient_id: str) -> CliniccardsPatient | None:
        try: payload = await self._get(f"{self._settings.cliniccards_patients_path}/{quote(patient_id, safe='')}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404: return None
            raise
        rows = _as_list(payload); raw = rows[0] if rows else payload.get("data") if isinstance(payload, dict) else None
        return _map_patient(raw) if isinstance(raw, dict) else None

    async def get_appointments(self, params: GetAppointmentsParams | None = None) -> list[CliniccardsAppointment]:
        now = datetime.now(timezone.utc)
        if params and params.patient_id:
            # Pulling one patient's full visit history (to work out visit
            # order), not the periodic sync's narrow recent window.
            start = params.from_ or now - timedelta(days=self._settings.cliniccards_history_days_back)
            end = params.to or now
        else:
            start = params.from_ if params and params.from_ else now - timedelta(days=self._settings.cliniccards_sync_days_back)
            end = params.to if params and params.to else now + timedelta(days=self._settings.cliniccards_sync_days_ahead)
        query: dict[str, Any] = {"from": start.date().isoformat(), "to": end.date().isoformat()}
        if params and params.patient_id:
            query["patient_id"] = params.patient_id
        rows = _as_list(await self._get(self._settings.cliniccards_appointments_path, query))
        appts = [_map_appointment(row) for row in rows]
        # Filter client-side too, in case the API ignores an unrecognized
        # patient_id param and just returns everything in the date range.
        if params and params.patient_id:
            appts = [a for a in appts if a.patient_id == params.patient_id]
        return appts

    async def get_appointment_type(self, appointment_id: str) -> dict | None: return None
    async def get_patient_documents(self, patient_id: str) -> list[CliniccardsDocument]: return []
    async def get_patient_images(self, patient_id: str) -> list[CliniccardsImage]:
        path = self._settings.cliniccards_patient_images_path.format(patient_id=quote(patient_id, safe=""))
        return [_map_file(row, patient_id) for row in _as_list(await self._get(path)) if str(row.get("is_image", "1")).lower() not in ("0", "false")]
    async def download_file(self, name: str) -> tuple[bytes, str]:
        response = await self._get(self._settings.cliniccards_file_path, {"name":name}, False)
        return response.content, response.headers.get("content-type", "application/octet-stream")
