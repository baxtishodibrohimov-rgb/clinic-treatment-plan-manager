from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import Role
from app.models.user import User
from app.security.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessiya tugagan yoki noto'g'ri token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Faqat admin uchun ruxsat")
    return user


def require_role(*roles: Role):
    """Dependency factory: allow SUPER_ADMIN/ADMIN always, plus anyone
    holding at least one of the given roles."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.is_admin or any(user.has_role(r) for r in roles):
            return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ruxsat yo'q")

    return _checker
