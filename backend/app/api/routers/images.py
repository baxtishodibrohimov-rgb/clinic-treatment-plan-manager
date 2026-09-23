import asyncio
import io
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.integrations.cliniccards.factory import get_cliniccards_adapter
from app.models.analysis import ImageAnnotation
from app.models.case import TreatmentPlanCase
from app.models.enums import ImageSource
from app.models.image import ClinicalImage
from app.models.user import User
from app.schemas.analysis import ImageAnnotationIn, ImageAnnotationOut
from app.security.deps import get_current_user

router = APIRouter(prefix="/api/images", tags=["images"])


def _get_image_or_404(db: Session, image_id: uuid.UUID, user: User) -> ClinicalImage:
    image = db.get(ClinicalImage, image_id)
    if not image:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rasm topilmadi")
    case = db.get(TreatmentPlanCase, image.case_id)
    if not case or (not user.is_super_admin and case.clinic_id != user.clinic_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rasm topilmadi")
    return image


def _get_image_file_blocking(image_id: uuid.UUID, user: User) -> tuple[bytes, str]:
    """Runs on its own thread + DB session, never on the shared event loop.
    Every image on every page (dashboard cards, case detail's 13-22 slots,
    the wizard, the presentation deck) goes through this endpoint, so the
    previous `async def` — which called db.get()/db.commit() directly on
    the coroutine — froze the whole app for every user on every image
    load: confirmed empirically, 20 concurrent image requests stalled a
    concurrent 5ms heartbeat to as much as 90ms per tick. Same fix as
    sync_second_consultations_blocking, applied to the hottest path in the
    app instead of a periodic job."""
    db = SessionLocal()
    try:
        image = _get_image_or_404(db, image_id, user)

        if image.file_data:
            return image.file_data, image.mime_type or "application/octet-stream"

        if image.source != ImageSource.CLINICCARDS or not image.external_url:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Rasm fayli topilmadi")

        try:
            data, mime_type = asyncio.run(get_cliniccards_adapter().download_file(image.external_url))
        except (httpx.HTTPError, RuntimeError):
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Cliniccards rasmini yuklab bo'lmadi") from None

        # Lazy fallback: if a periodic sync could not download this image (for
        # example because of a temporary rate limit), cache it on first view.
        image.file_data = data
        image.mime_type = mime_type
        image.original_filename = image.external_url.rsplit("/", 1)[-1][:255] or "cliniccards-image"
        db.commit()
        return data, mime_type or "application/octet-stream"
    finally:
        db.close()


def _make_thumbnail(data: bytes) -> bytes:
    """Build a compact, correctly-oriented gallery image.

    The original remains untouched for fullscreen review and presentation
    export. 480px is deliberately larger than today's 104px tile so it also
    stays crisp on high-DPI displays.
    """
    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.thumbnail((480, 480), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, format="WEBP", quality=82, method=6)
        return output.getvalue()


def _get_image_thumbnail_blocking(image_id: uuid.UUID, user: User) -> tuple[bytes, str]:
    db = SessionLocal()
    try:
        image = _get_image_or_404(db, image_id, user)
        if image.thumbnail_data:
            return image.thumbnail_data, image.thumbnail_mime_type or "image/webp"

        data = image.file_data
        if data is None and image.source == ImageSource.CLINICCARDS and image.external_url:
            try:
                data, mime_type = asyncio.run(get_cliniccards_adapter().download_file(image.external_url))
            except (httpx.HTTPError, RuntimeError):
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Cliniccards rasmini yuklab bo'lmadi") from None
            image.file_data = data
            image.mime_type = mime_type
            image.original_filename = image.external_url.rsplit("/", 1)[-1][:255] or "cliniccards-image"

        if not data:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Rasm fayli topilmadi")

        try:
            thumbnail = _make_thumbnail(data)
        except (OSError, ValueError):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Rasm formatini ochib bo'lmadi") from None
        image.thumbnail_data = thumbnail
        image.thumbnail_mime_type = "image/webp"
        db.commit()
        return thumbnail, "image/webp"
    finally:
        db.close()


@router.get("/{image_id}/file")
async def get_image_file(
    image_id: uuid.UUID,
    user: User = Depends(get_current_user),
) -> Response:
    data, mime_type = await asyncio.to_thread(_get_image_file_blocking, image_id, user)
    return Response(content=data, media_type=mime_type, headers={"Cache-Control": "private, max-age=300"})


@router.get("/{image_id}/thumbnail")
async def get_image_thumbnail(
    image_id: uuid.UUID,
    user: User = Depends(get_current_user),
) -> Response:
    data, mime_type = await asyncio.to_thread(_get_image_thumbnail_blocking, image_id, user)
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Cache-Control": "private, max-age=86400, stale-while-revalidate=604800"},
    )


@router.get("/{image_id}/annotations", response_model=ImageAnnotationOut | None)
def get_image_annotations(
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImageAnnotationOut | None:
    """The wizard's drawing toolbar (line/arrow/oval/rect over a photo) —
    one shape list per image, versioned (spec section 12/43). Returns the
    latest version, or null if nothing has been drawn on this image yet."""
    _get_image_or_404(db, image_id, user)
    row = db.execute(
        select(ImageAnnotation)
        .where(ImageAnnotation.image_id == image_id)
        .order_by(ImageAnnotation.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    return ImageAnnotationOut.model_validate(row) if row else None


@router.put("/{image_id}/annotations", response_model=ImageAnnotationOut)
def put_image_annotations(
    image_id: uuid.UUID,
    payload: ImageAnnotationIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImageAnnotationOut:
    """Replaces the image's shape list with a new version — each save is a
    new row (spec's "versioned JSON"), never an in-place overwrite, so an
    earlier state is never silently lost."""
    _get_image_or_404(db, image_id, user)
    prev_version = db.execute(
        select(ImageAnnotation.version)
        .where(ImageAnnotation.image_id == image_id)
        .order_by(ImageAnnotation.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    row = ImageAnnotation(
        image_id=image_id,
        annotation_json=payload.annotation_json,
        version=(prev_version or 0) + 1,
        created_by_user_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ImageAnnotationOut.model_validate(row)
