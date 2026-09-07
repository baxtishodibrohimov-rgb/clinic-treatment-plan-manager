from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.integrations.cliniccards.factory import get_cliniccards_adapter
from app.models.enums import SyncType
from app.models.settings import AppSetting, AssignmentConfig
from app.models.sync_log import IntegrationSyncLog
from app.schemas.config import (
    AppSettingOut,
    AppSettingUpdate,
    AssignmentConfigOut,
    AssignmentConfigUpdate,
    SyncLogOut,
)
from app.security.deps import require_admin
from app.services.sync_service import sync_second_consultations

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_admin)])


@router.get("/assignment-config", response_model=AssignmentConfigOut)
def get_assignment_config(db: Session = Depends(get_db)) -> AssignmentConfigOut:
    row = db.get(AssignmentConfig, 1)
    if not row:
        row = AssignmentConfig(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return AssignmentConfigOut.model_validate(row)


@router.put("/assignment-config", response_model=AssignmentConfigOut)
def update_assignment_config(payload: AssignmentConfigUpdate, db: Session = Depends(get_db)) -> AssignmentConfigOut:
    row = db.get(AssignmentConfig, 1)
    if not row:
        row = AssignmentConfig(id=1)
        db.add(row)
    row.mode = payload.mode
    row.strategy = payload.strategy
    db.commit()
    db.refresh(row)
    return AssignmentConfigOut.model_validate(row)


@router.get("/app-settings", response_model=list[AppSettingOut])
def list_app_settings(db: Session = Depends(get_db)) -> list[AppSettingOut]:
    rows = db.execute(select(AppSetting).order_by(AppSetting.key)).scalars().all()
    return [AppSettingOut.model_validate(r) for r in rows]


@router.put("/app-settings/{key}", response_model=AppSettingOut)
def update_app_setting(key: str, payload: AppSettingUpdate, db: Session = Depends(get_db)) -> AppSettingOut:
    row = db.get(AppSetting, key)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sozlama topilmadi")
    row.value = payload.value
    db.commit()
    db.refresh(row)
    return AppSettingOut.model_validate(row)


@router.get("/sync-log", response_model=list[SyncLogOut])
def sync_log(db: Session = Depends(get_db)) -> list[SyncLogOut]:
    rows = db.execute(select(IntegrationSyncLog).order_by(IntegrationSyncLog.created_at.desc()).limit(20)).scalars().all()
    return [SyncLogOut(id=r.id, sync_type=r.sync_type.value, status=r.status.value, records_seen=r.records_seen, cases_created=r.cases_created, error=r.error) for r in rows]


@router.post("/sync-now")
async def sync_now(db: Session = Depends(get_db)) -> dict:
    adapter = get_cliniccards_adapter()
    return await sync_second_consultations(db, adapter, SyncType.MANUAL)
