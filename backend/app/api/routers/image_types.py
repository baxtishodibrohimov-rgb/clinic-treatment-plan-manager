import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import ImageCategory
from app.models.image import ImageType
from app.schemas.config import ImageTypeCreate, ImageTypeUpdate
from app.security.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/image-types", tags=["image-types"])


@router.get("", dependencies=[Depends(get_current_user)])
def list_image_types(db: Session = Depends(get_db)) -> list[dict]:
    types = db.execute(select(ImageType).order_by(ImageType.sort_order)).scalars().all()
    return [
        {
            "id": t.id,
            "code": t.code,
            "label": t.label,
            "category": t.category.value,
            "is_required": t.is_required,
            "is_active": t.is_active,
            "sort_order": t.sort_order,
        }
        for t in types
    ]


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_image_type(payload: ImageTypeCreate, db: Session = Depends(get_db)) -> dict:
    try:
        category = ImageCategory(payload.category)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "category noto'g'ri (extraoral/intraoral/radiology)") from None
    row = ImageType(
        code=payload.code,
        label=payload.label,
        category=category,
        is_required=payload.is_required,
        sort_order=payload.sort_order,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "code": row.code}


@router.patch("/{image_type_id}", dependencies=[Depends(require_admin)])
def update_image_type(image_type_id: uuid.UUID, payload: ImageTypeUpdate, db: Session = Depends(get_db)) -> dict:
    row = db.get(ImageType, image_type_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topilmadi")
    data = payload.model_dump(exclude_unset=True)
    if "category" in data and data["category"] is not None:
        try:
            data["category"] = ImageCategory(data["category"])
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "category noto'g'ri") from None
    for field, value in data.items():
        setattr(row, field, value)
    db.commit()
    return {"ok": True}
