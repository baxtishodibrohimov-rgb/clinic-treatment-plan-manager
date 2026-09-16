import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.integrations.cliniccards.factory import get_cliniccards_adapter
from app.models.case import TreatmentPlanCase
from app.models.enums import ImageSource
from app.models.image import ClinicalImage
from app.models.user import User
from app.security.deps import get_current_user

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/{image_id}/file")
async def get_image_file(
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    image = db.get(ClinicalImage, image_id)
    if not image:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rasm topilmadi")

    case = db.get(TreatmentPlanCase, image.case_id)
    if not case or (not user.is_super_admin and case.clinic_id != user.clinic_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rasm topilmadi")

    if image.file_data:
        return Response(
            content=image.file_data,
            media_type=image.mime_type or "application/octet-stream",
            headers={"Cache-Control": "private, max-age=300"},
        )

    if image.source != ImageSource.CLINICCARDS or not image.external_url:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rasm fayli topilmadi")

    try:
        data, mime_type = await get_cliniccards_adapter().download_file(image.external_url)
    except (httpx.HTTPError, RuntimeError):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Cliniccards rasmini yuklab bo'lmadi") from None

    # Lazy fallback: if a periodic sync could not download this image (for
    # example because of a temporary rate limit), cache it on first view.
    image.file_data = data
    image.mime_type = mime_type
    image.original_filename = image.external_url.rsplit("/", 1)[-1][:255] or "cliniccards-image"
    db.commit()

    return Response(
        content=data,
        media_type=mime_type or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=300"},
    )
