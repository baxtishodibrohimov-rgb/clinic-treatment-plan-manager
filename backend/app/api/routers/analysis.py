import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis import AnalysisTemplate
from app.models.case import TreatmentPlanCase
from app.models.dental import ToothStatus
from app.models.image import ImageType
from app.models.user import User
from app.schemas.analysis import (
    AnalysisAnswerOut,
    AnalysisAnswerUpsert,
    AnalysisQuestionOut,
    AnalysisTemplateOut,
    DentalChartOut,
    ToothClickRequest,
    ToothStatusOut,
)
from app.security.deps import get_current_user
from app.services import analysis_service, findings_service
from app.services.analysis_service import tooth_code

router = APIRouter(prefix="/api/cases/{case_id}", tags=["analysis"])


def _get_case_or_404(db: Session, case_id: uuid.UUID, user: User) -> TreatmentPlanCase:
    case = db.get(TreatmentPlanCase, case_id)
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case topilmadi")
    if not user.is_super_admin and case.clinic_id != user.clinic_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case topilmadi")
    return case


def _tooth_out(t: ToothStatus) -> ToothStatusOut:
    return ToothStatusOut(
        quadrant=t.quadrant,
        position=t.position,
        dentition=t.dentition,
        tooth_code=tooth_code(t.quadrant, t.position, t.dentition) if t.dentition else "",
        notes=t.notes,
    )


def _chart_out(db: Session, chart) -> DentalChartOut:
    teeth = db.execute(
        select(ToothStatus).where(ToothStatus.dental_chart_id == chart.id).order_by(ToothStatus.quadrant, ToothStatus.position)
    ).scalars().all()
    return DentalChartOut(id=chart.id, numbering_system=chart.numbering_system, teeth=[_tooth_out(t) for t in teeth])


@router.get("/analysis-questions", response_model=list[AnalysisQuestionOut])
def list_analysis_questions(case_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[AnalysisQuestionOut]:
    _get_case_or_404(db, case_id, user)
    templates = analysis_service.get_templates(db)
    answers = analysis_service.get_answers(db, case_id)
    image_type_codes = {it.id: it.code for it in db.query(ImageType).all()}

    return [
        AnalysisQuestionOut(
            template=AnalysisTemplateOut(
                id=t.id,
                image_type_id=t.image_type_id,
                image_type_code=image_type_codes.get(t.image_type_id),
                category=t.category,
                question=t.question,
                answer_type=t.answer_type,
                options=t.options,
                sort_order=t.sort_order,
            ),
            answer=AnalysisAnswerOut.model_validate(answers[t.id]) if t.id in answers else None,
        )
        for t in templates
    ]


@router.put("/analysis-answers/{template_id}", response_model=AnalysisAnswerOut)
def upsert_analysis_answer(
    case_id: uuid.UUID,
    template_id: uuid.UUID,
    payload: AnalysisAnswerUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisAnswerOut:
    _get_case_or_404(db, case_id, user)
    answer = analysis_service.save_answer(db, case_id, template_id, value=payload.value, note=payload.note, user_id=user.id)
    template = db.get(AnalysisTemplate, template_id)
    if template:
        findings_service.sync_finding_for_answer(db, case_id, template, answer)
    db.commit()
    db.refresh(answer)
    return AnalysisAnswerOut.model_validate(answer)


@router.get("/dental-chart", response_model=DentalChartOut)
def get_dental_chart(case_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DentalChartOut:
    _get_case_or_404(db, case_id, user)
    chart = analysis_service.get_or_create_dental_chart(db, case_id)
    db.commit()
    return _chart_out(db, chart)


@router.post("/dental-chart/click", response_model=ToothStatusOut)
def click_dental_chart(
    case_id: uuid.UUID, payload: ToothClickRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ToothStatusOut:
    _get_case_or_404(db, case_id, user)
    if payload.quadrant not in (1, 2, 3, 4) or not (1 <= payload.position <= 8):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Noto'g'ri quadrant/position")
    if payload.click_type not in ("single", "double"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "click_type 'single' yoki 'double' bo'lishi kerak")

    chart = analysis_service.get_or_create_dental_chart(db, case_id)
    tooth = analysis_service.click_tooth(db, chart, payload.quadrant, payload.position, payload.click_type)
    db.commit()
    db.refresh(tooth)
    return _tooth_out(tooth)


@router.post("/dental-chart/reset", response_model=DentalChartOut)
def reset_dental_chart_endpoint(
    case_id: uuid.UUID, dentition: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DentalChartOut:
    """dentition: 'permanent' (default, doimiy tish) or 'primary' (sut tish)."""
    _get_case_or_404(db, case_id, user)
    if dentition not in ("permanent", "primary"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "dentition 'permanent' yoki 'primary' bo'lishi kerak")

    chart = analysis_service.get_or_create_dental_chart(db, case_id)
    analysis_service.reset_dental_chart(db, chart, dentition)
    db.commit()
    return _chart_out(db, chart)
