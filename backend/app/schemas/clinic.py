import uuid

from pydantic import BaseModel


class ClinicOut(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    is_default: bool
    cliniccards_branch_code: str | None

    model_config = {"from_attributes": True}


class ClinicCreateRequest(BaseModel):
    name: str
    cliniccards_branch_code: str | None = None
    is_default: bool = False


class ClinicUpdateRequest(BaseModel):
    name: str
    is_active: bool
    is_default: bool
    cliniccards_branch_code: str | None = None
