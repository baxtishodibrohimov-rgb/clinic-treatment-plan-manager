import uuid

from pydantic import BaseModel, EmailStr

from app.models.enums import Role
from app.schemas.clinic import ClinicOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    telegram_id: int | None
    is_active: bool
    max_workload: int | None
    roles: list[Role]
    clinic: ClinicOut | None = None

    model_config = {"from_attributes": True}
