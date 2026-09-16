import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.case import TreatmentPlanCase
from app.models.image import ClinicalImage
from app.models.user import User
from app.security.deps import get_current_user

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/{image_id}/file")
def get_image_file(image_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    image = db.get(ClinicalImage, image_id)
    if not image or not image.file_data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rasm topilmadi")

    case = db.get(TreatmentPlanCase, image.case_id)
    if not case or (not user.is_super_admin and case.clinic_id != user.clinic_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rasm topilmadi")

    return Response(content=image.file_data, media_type=image.mime_type or "application/octet-stream")
