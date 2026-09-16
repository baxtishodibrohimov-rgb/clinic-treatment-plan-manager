"""Clinical Analysis Wizard (spec Phase 5) — questionnaire answers and the
interactive dental chart. The questionnaire content itself (questions,
options) comes entirely from AnalysisTemplate rows seeded from the clinic's
own manual (see alembic/versions/970995590f0f_...) — nothing clinical is
decided in this file, which only handles storage/state-machine plumbing.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisAnswer, AnalysisTemplate
from app.models.dental import DentalChart, ToothStatus

QUADRANTS = (1, 2, 3, 4)
POSITIONS = range(1, 9)


def tooth_code(quadrant: int, position: int, dentition: str) -> str:
    """FDI notation: permanent quadrants are 1-4, primary quadrants are the
    same anatomical quadrant + 4 (5-8). Position 6-8 has no primary variant."""
    fdi_quadrant = quadrant if dentition == "permanent" else quadrant + 4
    return f"{fdi_quadrant}{position}"


def get_templates(db: Session) -> list[AnalysisTemplate]:
    return (
        db.execute(select(AnalysisTemplate).where(AnalysisTemplate.active.is_(True)).order_by(AnalysisTemplate.sort_order))
        .scalars()
        .all()
    )


def get_answers(db: Session, case_id: uuid.UUID) -> dict[uuid.UUID, AnalysisAnswer]:
    rows = db.execute(select(AnalysisAnswer).where(AnalysisAnswer.case_id == case_id)).scalars().all()
    return {a.template_id: a for a in rows if a.template_id}


def save_answer(
    db: Session,
    case_id: uuid.UUID,
    template_id: uuid.UUID,
    *,
    value,
    note: str | None,
    user_id: uuid.UUID,
) -> AnalysisAnswer:
    existing = db.execute(
        select(AnalysisAnswer).where(AnalysisAnswer.case_id == case_id, AnalysisAnswer.template_id == template_id)
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    answer_value = {"value": value} if value is not None else None
    if existing:
        existing.answer_value = answer_value
        existing.note = note
        existing.answered_by_user_id = user_id
        existing.answered_at = now
        return existing

    answer = AnalysisAnswer(
        case_id=case_id,
        template_id=template_id,
        answer_value=answer_value,
        note=note,
        answered_by_user_id=user_id,
        answered_at=now,
    )
    db.add(answer)
    db.flush()
    return answer


def get_or_create_dental_chart(db: Session, case_id: uuid.UUID) -> DentalChart:
    """Auto-creates a chart with all 32 positions defaulted to "permanent"
    the first time anyone opens the tooth chart for this case."""
    chart = db.execute(select(DentalChart).where(DentalChart.case_id == case_id)).scalar_one_or_none()
    if chart:
        return chart

    chart = DentalChart(case_id=case_id, numbering_system="FDI")
    db.add(chart)
    db.flush()
    for quadrant in QUADRANTS:
        for position in POSITIONS:
            db.add(ToothStatus(dental_chart_id=chart.id, quadrant=quadrant, position=position, dentition="permanent"))
    db.flush()
    return chart


def reset_dental_chart(db: Session, chart: DentalChart, dentition: str) -> None:
    """Bulk "Sut tish" / "Doimiy tish" button: sets the whole chart back to
    one default (position 6-8 has no primary variant, so it goes empty)."""
    teeth = db.execute(select(ToothStatus).where(ToothStatus.dental_chart_id == chart.id)).scalars().all()
    for tooth in teeth:
        if dentition == "primary" and tooth.position > 5:
            tooth.dentition = None
        else:
            tooth.dentition = dentition


def click_tooth(db: Session, chart: DentalChart, quadrant: int, position: int, click_type: str) -> ToothStatus:
    tooth = db.execute(
        select(ToothStatus).where(
            ToothStatus.dental_chart_id == chart.id, ToothStatus.quadrant == quadrant, ToothStatus.position == position
        )
    ).scalar_one()

    if click_type == "single":
        tooth.dentition = None
    else:  # "double"
        if position <= 5:
            tooth.dentition = "primary" if tooth.dentition == "permanent" else "permanent"
        else:
            # No primary variant exists for position 6-8 — a permanent-only
            # slot toggles between empty (unerupted) and permanent (erupted).
            tooth.dentition = None if tooth.dentition == "permanent" else "permanent"
    return tooth
