"""Cliniccards integration layer — types.

This is the ONLY place that should know the shape of Cliniccards data.
Nothing outside `integrations/cliniccards` should assume a particular field
name or endpoint path from the real Cliniccards API — everything else in
this project talks to `CliniccardsAdapter`, never to Cliniccards directly.

Real API docs have not been provided yet (see ARCHITECTURE.md, Phase 11).
Until then `get_cliniccards_adapter()` returns `MockCliniccardsAdapter`,
which returns deterministic fake data shaped exactly like these types so the
rest of the app (case sync, dashboard, image gallery) can be built and
tested now.
"""
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class CliniccardsPatient:
    patient_id: str
    full_name: str
    birth_date: date | None
    phone: str | None
    created_at: datetime | None
    raw: dict


@dataclass
class CliniccardsAppointment:
    appointment_id: str
    patient_id: str
    doctor_name: str | None
    appointment_type_code: str
    appointment_type_label: str
    scheduled_at: datetime
    note: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class CliniccardsDocument:
    document_id: str
    patient_id: str
    kind: str
    title: str
    url: str
    created_at: datetime


@dataclass
class CliniccardsImage:
    image_id: str
    patient_id: str
    # Best-effort hint at what kind of clinical photo/x-ray this is, as
    # labeled in Cliniccards. Mapping this free-text label onto our own
    # ImageType is done by the sync service, not by the adapter.
    label_hint: str | None
    url: str
    captured_at: datetime | None


@dataclass
class GetAppointmentsParams:
    from_: datetime | None = None
    to: datetime | None = None
    appointment_type_code: str | None = None
