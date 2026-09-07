import uuid

from pydantic import BaseModel

from app.models.enums import AssignmentMode, AssignmentStrategy, ReminderTriggerType


class ImageTypeCreate(BaseModel):
    code: str
    label: str
    category: str
    is_required: bool = True
    sort_order: int = 0


class ImageTypeUpdate(BaseModel):
    label: str | None = None
    category: str | None = None
    is_required: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class ReminderRuleCreate(BaseModel):
    name: str
    trigger_type: ReminderTriggerType
    offset_minutes: int | None = None
    notify_roles: list[str] = ["planner"]
    is_active: bool = True
    sort_order: int = 0


class ReminderRuleUpdate(BaseModel):
    name: str | None = None
    offset_minutes: int | None = None
    notify_roles: list[str] | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class ReminderRuleOut(BaseModel):
    id: uuid.UUID
    name: str
    trigger_type: ReminderTriggerType
    offset_minutes: int | None
    notify_roles: list[str]
    is_active: bool
    sort_order: int

    model_config = {"from_attributes": True}


class AssignmentConfigUpdate(BaseModel):
    mode: AssignmentMode
    strategy: AssignmentStrategy


class AssignmentConfigOut(BaseModel):
    mode: AssignmentMode
    strategy: AssignmentStrategy

    model_config = {"from_attributes": True}


class AppSettingOut(BaseModel):
    key: str
    value: dict | list | str | int | float | bool | None

    model_config = {"from_attributes": True}


class AppSettingUpdate(BaseModel):
    value: dict | list | str | int | float | bool | None


class SyncLogOut(BaseModel):
    id: uuid.UUID
    sync_type: str
    status: str
    records_seen: int
    cases_created: int
    error: str | None

    model_config = {"from_attributes": True}
