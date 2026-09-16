"""Deterministic mock Cliniccards provider.

Used whenever CLINICCARDS_API_URL / CLINICCARDS_API_KEY are not configured
(the default in every environment until real credentials + API docs are
provided — see ARCHITECTURE.md Phase 11). Scheduling times are computed
relative to "now" each call so demo appointments stay in the near future no
matter when this runs.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.integrations.cliniccards.base import CliniccardsAdapter
from app.integrations.cliniccards.types import (
    CliniccardsAppointment,
    CliniccardsDocument,
    CliniccardsImage,
    CliniccardsPatient,
    GetAppointmentsParams,
)

IMAGE_LABELS = [
    "Face frontal",
    "Face frontal smile",
    "Face profile right",
    "Face profile left",
    "3/4 view",
    "Intraoral frontal",
    "Right buccal",
    "Left buccal",
    "Upper occlusal",
    "Lower occlusal",
    "OPG / panoramic",
    "Lateral cephalogram",
]


@dataclass
class _PatientSeed:
    patient_id: str
    full_name: str
    birth_date: str
    phone: str
    days_until_consultation: float
    doctor_name: str


PATIENT_SEEDS: list[_PatientSeed] = [
    _PatientSeed("CC-1001", "Dilnoza Yusupova", "2005-03-12", "+998901234501", 1, "Dr. Aziz Karimov"),
    _PatientSeed("CC-1002", "Sardor Toshev", "1998-11-02", "+998901234502", 2, "Dr. Aziz Karimov"),
    _PatientSeed("CC-1003", "Madina Alieva", "2010-07-19", "+998901234503", 0.3, "Dr. Nilufar Rashidova"),
    _PatientSeed("CC-1004", "Jasur Nematov", "1995-01-27", "+998901234504", 4, "Dr. Nilufar Rashidova"),
    _PatientSeed("CC-1005", "Ozoda Karimova", "2003-09-08", "+998901234505", -1, "Dr. Aziz Karimov"),
]


def _appointment_id(patient_id: str) -> str:
    return f"{patient_id}-APT-2CONS"


def _first_visit_appointment_id(patient_id: str) -> str:
    return f"{patient_id}-APT-1CONS"


def _to_patient(seed: _PatientSeed) -> CliniccardsPatient:
    return CliniccardsPatient(
        patient_id=seed.patient_id,
        full_name=seed.full_name,
        birth_date=date.fromisoformat(seed.birth_date),
        phone=seed.phone,
        created_at=datetime.now(timezone.utc),
        raw={"mock": True},
    )


def _to_first_visit(seed: _PatientSeed) -> CliniccardsAppointment:
    # A patient's actual 1st visit, weeks before their upcoming 2nd —
    # exists so the "is this the 2nd visit in history" check has a real
    # history to compare against, same as the real Cliniccards data.
    scheduled_at = datetime.now(timezone.utc) + timedelta(days=seed.days_until_consultation) - timedelta(days=21)
    return CliniccardsAppointment(
        appointment_id=_first_visit_appointment_id(seed.patient_id),
        patient_id=seed.patient_id,
        doctor_name=seed.doctor_name,
        appointment_type_code="consultation_1",
        appointment_type_label="1-konsultatsiya",
        scheduled_at=scheduled_at,
        note="1st visit",
        raw={"mock": True},
    )


def _to_appointment(seed: _PatientSeed) -> CliniccardsAppointment:
    scheduled_at = datetime.now(timezone.utc) + timedelta(days=seed.days_until_consultation)
    return CliniccardsAppointment(
        appointment_id=_appointment_id(seed.patient_id),
        patient_id=seed.patient_id,
        doctor_name=seed.doctor_name,
        appointment_type_code="consultation_2",
        appointment_type_label="2-konsultatsiya",
        scheduled_at=scheduled_at,
        note="2and cons",
        raw={"mock": True},
    )


class MockCliniccardsAdapter(CliniccardsAdapter):
    async def get_patients(self) -> list[CliniccardsPatient]:
        return [_to_patient(s) for s in PATIENT_SEEDS]

    async def get_patient(self, patient_id: str) -> CliniccardsPatient | None:
        seed = next((s for s in PATIENT_SEEDS if s.patient_id == patient_id), None)
        return _to_patient(seed) if seed else None

    async def get_appointments(self, params: GetAppointmentsParams | None = None) -> list[CliniccardsAppointment]:
        # Every visit, not pre-labeled by ordinal position — same as the
        # real /visits endpoint. Whether one of these is a patient's 2nd
        # visit ever is worked out from history, not from a type/label here.
        appts = [a for s in PATIENT_SEEDS for a in (_to_first_visit(s), _to_appointment(s))]
        if params:
            if params.patient_id:
                appts = [a for a in appts if a.patient_id == params.patient_id]
            if params.appointment_type_code:
                appts = [a for a in appts if a.appointment_type_code == params.appointment_type_code]
            if params.from_:
                appts = [a for a in appts if a.scheduled_at >= params.from_]
            if params.to:
                appts = [a for a in appts if a.scheduled_at < params.to]
        return appts

    async def get_appointment_type(self, appointment_id: str) -> dict | None:
        seed = next((s for s in PATIENT_SEEDS if _appointment_id(s.patient_id) == appointment_id), None)
        if not seed:
            return None
        return {"code": "consultation_2", "label": "2-konsultatsiya"}

    async def get_patient_documents(self, patient_id: str) -> list[CliniccardsDocument]:
        seed = next((s for s in PATIENT_SEEDS if s.patient_id == patient_id), None)
        if not seed:
            return []
        return [
            CliniccardsDocument(
                document_id=f"{patient_id}-DOC-1",
                patient_id=patient_id,
                kind="consent",
                title="Consultation consent form",
                url=f"https://mock-cliniccards.local/documents/{patient_id}/consent.pdf",
                created_at=datetime.now(timezone.utc),
            )
        ]

    async def get_patient_images(self, patient_id: str) -> list[CliniccardsImage]:
        seed = next((s for s in PATIENT_SEEDS if s.patient_id == patient_id), None)
        if not seed:
            return []
        return [
            CliniccardsImage(
                image_id=f"{patient_id}-IMG-{idx + 1}",
                patient_id=patient_id,
                label_hint=label,
                url=f"https://mock-cliniccards.local/images/{patient_id}/{idx + 1}.jpg",
                captured_at=datetime.now(timezone.utc) - timedelta(days=3),
            )
            for idx, label in enumerate(IMAGE_LABELS)
        ]

    async def download_file(self, name: str) -> tuple[bytes, str]:
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480"><rect width="100%" height="100%" fill="#e5e7eb"/><text x="50%" y="50%" text-anchor="middle" fill="#6b7280">Mock Cliniccards image</text></svg>'
        return svg, "image/svg+xml"
