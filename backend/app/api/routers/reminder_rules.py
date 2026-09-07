import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notification import ReminderRule
from app.schemas.config import ReminderRuleCreate, ReminderRuleOut, ReminderRuleUpdate
from app.security.deps import require_admin

router = APIRouter(prefix="/api/reminder-rules", tags=["reminder-rules"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[ReminderRuleOut])
def list_rules(db: Session = Depends(get_db)) -> list[ReminderRuleOut]:
    rules = db.execute(select(ReminderRule).order_by(ReminderRule.sort_order)).scalars().all()
    return [ReminderRuleOut.model_validate(r) for r in rules]


@router.post("", response_model=ReminderRuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(payload: ReminderRuleCreate, db: Session = Depends(get_db)) -> ReminderRuleOut:
    row = ReminderRule(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ReminderRuleOut.model_validate(row)


@router.patch("/{rule_id}", response_model=ReminderRuleOut)
def update_rule(rule_id: uuid.UUID, payload: ReminderRuleUpdate, db: Session = Depends(get_db)) -> ReminderRuleOut:
    row = db.get(ReminderRule, rule_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topilmadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return ReminderRuleOut.model_validate(row)
