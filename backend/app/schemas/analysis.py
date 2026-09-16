import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AnswerType


class AnalysisTemplateOut(BaseModel):
    id: uuid.UUID
    image_type_id: uuid.UUID | None
    image_type_code: str | None
    category: str | None
    question: str
    answer_type: AnswerType
    options: list
    sort_order: int

    model_config = {"from_attributes": True}


class AnalysisAnswerOut(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    answer_value: dict | None
    note: str | None
    answered_by_user_id: uuid.UUID | None
    answered_at: datetime | None

    model_config = {"from_attributes": True}


class AnalysisQuestionOut(BaseModel):
    """A template merged with the case's current answer (if any) — one call
    for the wizard to render everything in a single render pass."""

    template: AnalysisTemplateOut
    answer: AnalysisAnswerOut | None


class AnalysisAnswerUpsert(BaseModel):
    # Free-form so it fits single_choice (str), boolean (bool), text (str),
    # multi_choice (list[str]) without needing a separate field per type.
    value: str | bool | list[str] | None = None
    note: str | None = None


class ToothStatusOut(BaseModel):
    quadrant: int
    position: int
    dentition: str | None
    tooth_code: str
    notes: str | None

    model_config = {"from_attributes": True}


class DentalChartOut(BaseModel):
    id: uuid.UUID
    numbering_system: str
    teeth: list[ToothStatusOut]

    model_config = {"from_attributes": True}


class ToothClickRequest(BaseModel):
    quadrant: int
    position: int
    click_type: str  # "single" | "double"
