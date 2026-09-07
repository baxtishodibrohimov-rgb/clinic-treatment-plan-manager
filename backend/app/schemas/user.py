import uuid

from pydantic import BaseModel, EmailStr

from app.models.enums import Role


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    telegram_id: int | None = None
    roles: list[Role] = []
    max_workload: int | None = None


class UserUpdateRolesRequest(BaseModel):
    roles: list[Role]
    max_workload: int | None = None


class UserListItem(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    telegram_id: int | None
    is_active: bool
    max_workload: int | None
    roles: list[Role]
