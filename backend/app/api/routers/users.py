import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import Role
from app.models.user import User, UserRole
from app.schemas.clinic import ClinicOut
from app.schemas.user import UserCreateRequest, UserListItem, UserUpdateRolesRequest
from app.security.deps import clinic_scope, require_admin
from app.security.passwords import hash_password

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin)])


def _to_list_item(user: User) -> UserListItem:
    return UserListItem(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        telegram_id=user.telegram_id,
        is_active=user.is_active,
        max_workload=user.max_workload,
        roles=sorted({r.role for r in user.roles}, key=lambda r: r.value),
        clinic=ClinicOut.model_validate(user.clinic) if user.clinic else None,
    )


@router.get("", response_model=list[UserListItem])
def list_users(db: Session = Depends(get_db), scope_clinic_id: uuid.UUID | None = Depends(clinic_scope)) -> list[UserListItem]:
    query = select(User).order_by(User.full_name)
    if scope_clinic_id is not None:
        query = query.where(User.clinic_id == scope_clinic_id)
    users = db.execute(query).scalars().unique().all()
    return [_to_list_item(u) for u in users]


@router.get("/planners", response_model=list[UserListItem])
def list_planners(db: Session = Depends(get_db), scope_clinic_id: uuid.UUID | None = Depends(clinic_scope)) -> list[UserListItem]:
    """Roster used by the case-assignment dropdown."""
    query = select(User).join(UserRole, UserRole.user_id == User.id).where(UserRole.role == Role.PLANNER, User.is_active.is_(True))
    if scope_clinic_id is not None:
        query = query.where(User.clinic_id == scope_clinic_id)
    users = db.execute(query).scalars().unique().all()
    return [_to_list_item(u) for u in users]


@router.post("", response_model=UserListItem, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> UserListItem:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bu email allaqachon ro'yxatdan o'tgan")

    roles = set(payload.roles)
    if Role.SUPER_ADMIN in roles and not admin.is_super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Faqat bosh administrator SUPER_ADMIN rolini bera oladi")

    # A clinic's own ADMIN can only create staff inside their own clinic —
    # any clinic_id they pass is ignored. SUPER_ADMIN must specify one
    # (unless the new user is itself a SUPER_ADMIN, which has no clinic).
    if admin.is_super_admin:
        clinic_id = None if Role.SUPER_ADMIN in roles else payload.clinic_id
        if clinic_id is None and Role.SUPER_ADMIN not in roles:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "clinic_id majburiy")
    else:
        clinic_id = admin.clinic_id

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        telegram_id=payload.telegram_id,
        max_workload=payload.max_workload,
        clinic_id=clinic_id,
    )
    db.add(user)
    db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role=role))
    db.commit()
    db.refresh(user)
    return _to_list_item(user)


@router.patch("/{user_id}/roles", response_model=UserListItem)
def update_roles(user_id: uuid.UUID, payload: UserUpdateRolesRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> UserListItem:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foydalanuvchi topilmadi")
    if not admin.is_super_admin and user.clinic_id != admin.clinic_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Boshqa klinika xodimini tahrirlash mumkin emas")

    wanted_roles = set(payload.roles)
    if Role.SUPER_ADMIN in wanted_roles and not admin.is_super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Faqat bosh administrator SUPER_ADMIN rolini bera oladi")

    user.max_workload = payload.max_workload
    if admin.is_super_admin:
        user.clinic_id = None if Role.SUPER_ADMIN in wanted_roles else (payload.clinic_id or user.clinic_id)

    existing_roles = {r.role for r in user.roles}
    for role in wanted_roles - existing_roles:
        db.add(UserRole(user_id=user.id, role=role))
    for ur in list(user.roles):
        if ur.role not in wanted_roles:
            db.delete(ur)

    db.commit()
    db.refresh(user)
    return _to_list_item(user)
