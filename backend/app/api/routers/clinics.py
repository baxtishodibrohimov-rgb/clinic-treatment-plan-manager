import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.clinic import Clinic
from app.schemas.clinic import ClinicCreateRequest, ClinicOut, ClinicUpdateRequest
from app.security.deps import get_current_user, require_super_admin

router = APIRouter(prefix="/api/clinics", tags=["clinics"])


@router.get("", response_model=list[ClinicOut], dependencies=[Depends(get_current_user)])
def list_clinics(db: Session = Depends(get_db)) -> list[ClinicOut]:
    """Any logged-in user can list clinics — non-super-admins need this to
    render their own clinic's name; the frontend hides create/edit unless
    the caller is actually SUPER_ADMIN."""
    rows = db.execute(select(Clinic).order_by(Clinic.name)).scalars().all()
    return [ClinicOut.model_validate(r) for r in rows]


@router.post("", response_model=ClinicOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_super_admin)])
def create_clinic(payload: ClinicCreateRequest, db: Session = Depends(get_db)) -> ClinicOut:
    if payload.is_default:
        db.execute(Clinic.__table__.update().values(is_default=False))
    clinic = Clinic(name=payload.name, cliniccards_branch_code=payload.cliniccards_branch_code, is_default=payload.is_default)
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    return ClinicOut.model_validate(clinic)


@router.put("/{clinic_id}", response_model=ClinicOut, dependencies=[Depends(require_super_admin)])
def update_clinic(clinic_id: uuid.UUID, payload: ClinicUpdateRequest, db: Session = Depends(get_db)) -> ClinicOut:
    clinic = db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Klinika topilmadi")
    if payload.is_default and not clinic.is_default:
        db.execute(Clinic.__table__.update().values(is_default=False))
    clinic.name = payload.name
    clinic.is_active = payload.is_active
    clinic.is_default = payload.is_default
    clinic.cliniccards_branch_code = payload.cliniccards_branch_code
    db.commit()
    db.refresh(clinic)
    return ClinicOut.model_validate(clinic)
