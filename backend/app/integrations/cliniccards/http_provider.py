"""Real Cliniccards REST client.

Enabled automatically once CLINICCARDS_API_URL and CLINICCARDS_API_KEY are
set (see .env.example / app/config.py). No endpoint path is hardcoded
elsewhere in the codebase — every path used here comes from a setting with a
best-guess REST default, so wiring in the real API later means editing env
vars + this file only.

IMPORTANT: the response field mapping below (`_map_patient`,
`_map_appointment`, ...) is a placeholder until Cliniccards' actual API
documentation is provided. Update these once real payload samples are
available; the rest of the app only depends on the `CliniccardsAdapter`
interface in base.py, so nothing else needs to change.
"""
from datetime import datetime
from typing import Any

import httpx

from app.config import Settings
from app.integrations.cliniccards.base import CliniccardsAdapter
from app.integrations.cliniccards.types import (
    CliniccardsAppointment,
    CliniccardsDocument,
    CliniccardsImage,
    CliniccardsPatient,
    GetAppointmentsParams,
)


def _map_patient(raw: dict[str, Any]) -> CliniccardsPatient:
    return CliniccardsPatient(
        patient_id=str(raw.get("id") or raw.get("patientId") or raw.get("patient_id")),
        full_name=str(raw.get("fullName") or raw.get("full_name") or raw.get("name") or ""),
        birth_date=raw.get("birthDate") or raw.get("birth_date"),
        phone=raw.get("phone") or raw.get("phoneNumber"),
        raw=raw,
    )


def _map_appointment(raw: dict[str, Any]) -> CliniccardsAppointment:
    return CliniccardsAppointment(
        appointment_id=str(raw.get("id") or raw.get("appointmentId") or raw.get("appointment_id")),
        patient_id=str(raw.get("patientId") or raw.get("patient_id")),
        doctor_name=raw.get("doctorName") or raw.get("doctor_name"),
        appointment_type_code=str(raw.get("typeCode") or raw.get("type_code") or raw.get("appointmentType") or ""),
        appointment_type_label=str(raw.get("typeLabel") or raw.get("type_label") or raw.get("appointmentType") or ""),
        scheduled_at=datetime.fromisoformat(str(raw.get("scheduledAt") or raw.get("scheduled_at") or raw.get("datetime"))),
        raw=raw,
    )


def _map_document(raw: dict[str, Any], patient_id: str) -> CliniccardsDocument:
    return CliniccardsDocument(
        document_id=str(raw.get("id") or raw.get("documentId")),
        patient_id=patient_id,
        kind=str(raw.get("kind") or raw.get("type") or "document"),
        title=str(raw.get("title") or raw.get("name") or "Document"),
        url=str(raw.get("url") or raw.get("fileUrl") or raw.get("file_url") or ""),
        created_at=datetime.fromisoformat(str(raw.get("createdAt") or raw.get("created_at"))) if raw.get("createdAt") or raw.get("created_at") else datetime.utcnow(),
    )


def _map_image(raw: dict[str, Any], patient_id: str) -> CliniccardsImage:
    captured = raw.get("capturedAt") or raw.get("captured_at")
    return CliniccardsImage(
        image_id=str(raw.get("id") or raw.get("imageId")),
        patient_id=patient_id,
        label_hint=raw.get("label") or raw.get("category") or raw.get("name"),
        url=str(raw.get("url") or raw.get("fileUrl") or raw.get("file_url") or ""),
        captured_at=datetime.fromisoformat(str(captured)) if captured else None,
    )


def _as_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items") or data.get("data") or []
    return []


class HttpCliniccardsAdapter(CliniccardsAdapter):
    def __init__(self, settings: Settings):
        if not settings.cliniccards_api_url or not settings.cliniccards_api_key:
            raise RuntimeError("CLINICCARDS_API_URL / CLINICCARDS_API_KEY not configured")
        self._base_url = settings.cliniccards_api_url.rstrip("/")
        self._settings = settings
        headers = {"Accept": "application/json"}
        if settings.cliniccards_api_key_header.lower() == "authorization":
            headers["Authorization"] = f"Bearer {settings.cliniccards_api_key}"
        else:
            headers[settings.cliniccards_api_key_header] = settings.cliniccards_api_key
        self._client = httpx.AsyncClient(base_url=self._base_url, headers=headers, timeout=30)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        res = await self._client.get(path, params=params)
        res.raise_for_status()
        return res.json()

    async def get_patients(self) -> list[CliniccardsPatient]:
        data = await self._get(self._settings.cliniccards_patients_path)
        return [_map_patient(r) for r in _as_list(data)]

    async def get_patient(self, patient_id: str) -> CliniccardsPatient | None:
        patients = await self.get_patients()
        return next((p for p in patients if p.patient_id == patient_id), None)

    async def get_appointments(self, params: GetAppointmentsParams | None = None) -> list[CliniccardsAppointment]:
        query: dict[str, Any] = {}
        if params:
            if params.from_:
                query["from"] = params.from_.isoformat()
            if params.to:
                query["to"] = params.to.isoformat()
            if params.appointment_type_code:
                query["type"] = params.appointment_type_code
        data = await self._get(self._settings.cliniccards_appointments_path, query)
        return [_map_appointment(r) for r in _as_list(data)]

    async def get_appointment_type(self, appointment_id: str) -> dict | None:
        path = self._settings.cliniccards_appointment_by_id_path.format(appointment_id=appointment_id)
        try:
            data = await self._get(path)
        except httpx.HTTPStatusError:
            return None
        appt = _map_appointment(data)
        return {"code": appt.appointment_type_code, "label": appt.appointment_type_label}

    async def get_patient_documents(self, patient_id: str) -> list[CliniccardsDocument]:
        path = self._settings.cliniccards_patient_documents_path.format(patient_id=patient_id)
        data = await self._get(path)
        return [_map_document(r, patient_id) for r in _as_list(data)]

    async def get_patient_images(self, patient_id: str) -> list[CliniccardsImage]:
        path = self._settings.cliniccards_patient_images_path.format(patient_id=patient_id)
        data = await self._get(path)
        return [_map_image(r, patient_id) for r in _as_list(data)]
