from abc import ABC, abstractmethod

from app.integrations.cliniccards.types import (
    CliniccardsAppointment,
    CliniccardsDocument,
    CliniccardsImage,
    CliniccardsPatient,
    GetAppointmentsParams,
)


class CliniccardsAdapter(ABC):
    """Abstraction over the clinic's Cliniccards system. Concrete
    implementations:
      - MockCliniccardsAdapter — deterministic in-memory demo data (default).
      - HttpCliniccardsAdapter — real REST client, enabled once
        CLINICCARDS_API_URL + CLINICCARDS_API_KEY are configured.

    Keep this interface stable; add methods rather than changing signatures
    so callers (case sync, dashboard, future image wizard) don't need to
    change when the real API is finally wired in.
    """

    @abstractmethod
    async def get_patients(self) -> list[CliniccardsPatient]: ...

    @abstractmethod
    async def get_patient(self, patient_id: str) -> CliniccardsPatient | None: ...

    @abstractmethod
    async def get_appointments(self, params: GetAppointmentsParams | None = None) -> list[CliniccardsAppointment]: ...

    @abstractmethod
    async def get_appointment_type(self, appointment_id: str) -> dict | None: ...

    @abstractmethod
    async def get_patient_documents(self, patient_id: str) -> list[CliniccardsDocument]: ...

    @abstractmethod
    async def get_patient_images(self, patient_id: str) -> list[CliniccardsImage]: ...
