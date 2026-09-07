import uuid

from pydantic import BaseModel, EmailStr

from app.models.enums import Role
from app.schemas.clinic import ClinicOut


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    telegram_id: int | None = None
    roles: list[Role] = []
    max_workload: int | None = None
    # Required unless `roles` includes SUPER_ADMIN (who has no clinic).
    # Non-super-admin callers (a clinic's own ADMIN) may omit this — the
    # router fills in their own clinic automatically.
    clinic_id: uuid.UUID | None = None


class UserUpdateRolesRequest(BaseModel):
    roles: list[Role]
    max_workload: int | None = None
    clinic_id: uuid.UUID | None = None


class UserListItem(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    telegram_id: int | None
    is_active: bool
    max_workload: int | None
    roles: list[Role]
    clinic: ClinicOut | None = None
