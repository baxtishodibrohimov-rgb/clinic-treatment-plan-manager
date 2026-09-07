import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import Role
from app.models.user import User, UserRole
from app.schemas.user import UserCreateRequest, UserListItem, UserUpdateRolesRequest
from app.security.deps import require_admin
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
    )


@router.get("", response_model=list[UserListItem])
def list_users(db: Session = Depends(get_db)) -> list[UserListItem]:
    users = db.execute(select(User).order_by(User.full_name)).scalars().unique().all()
    return [_to_list_item(u) for u in users]


@router.get("/planners", response_model=list[UserListItem])
def list_planners(db: Session = Depends(get_db)) -> list[UserListItem]:
    """Roster used by the case-assignment dropdown."""
    users = (
        db.execute(select(User).join(UserRole, UserRole.user_id == User.id).where(UserRole.role == Role.PLANNER, User.is_active.is_(True)))
        .scalars()
        .unique()
        .all()
    )
    return [_to_list_item(u) for u in users]


@router.post("", response_model=UserListItem, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateRequest, db: Session = Depends(get_db)) -> UserListItem:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bu email allaqachon ro'yxatdan o'tgan")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        telegram_id=payload.telegram_id,
        max_workload=payload.max_workload,
    )
    db.add(user)
    db.flush()
    for role in set(payload.roles):
        db.add(UserRole(user_id=user.id, role=role))
    db.commit()
    db.refresh(user)
    return _to_list_item(user)


@router.patch("/{user_id}/roles", response_model=UserListItem)
def update_roles(user_id: uuid.UUID, payload: UserUpdateRolesRequest, db: Session = Depends(get_db)) -> UserListItem:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foydalanuvchi topilmadi")

    user.max_workload = payload.max_workload
    existing_roles = {r.role for r in user.roles}
    wanted_roles = set(payload.roles)

    for role in wanted_roles - existing_roles:
        db.add(UserRole(user_id=user.id, role=role))
    for ur in list(user.roles):
        if ur.role not in wanted_roles:
            db.delete(ur)

    db.commit()
    db.refresh(user)
    return _to_list_item(user)
