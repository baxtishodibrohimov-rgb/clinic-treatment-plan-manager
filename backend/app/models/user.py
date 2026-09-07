import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import Role

role_enum = PGEnum(Role, name="role", create_type=True, values_callable=lambda enum_cls: [member.value for member in enum_cls])


class User(Base, UUIDPKMixin, TimestampMixin):
    """A single user table for everyone who can log into the admin app —
    unlike the earlier Supabase-based build, there's no legacy admins/staff
    split to preserve here, so SUPER_ADMIN/ADMIN/PLANNER/DOCTOR/CONSULTANT
    are all just `User` + zero-or-more `UserRole` rows.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_workload: Mapped[int | None] = mapped_column(Integer, nullable=True)

    roles: Mapped[list["UserRole"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def role_names(self) -> set[Role]:
        return {r.role for r in self.roles}

    def has_role(self, role: Role) -> bool:
        if Role.SUPER_ADMIN in self.role_names or Role.ADMIN in self.role_names:
            return True
        return role in self.role_names

    @property
    def is_admin(self) -> bool:
        return Role.SUPER_ADMIN in self.role_names or Role.ADMIN in self.role_names

    @property
    def is_super_admin(self) -> bool:
        return Role.SUPER_ADMIN in self.role_names


class UserRole(Base, UUIDPKMixin):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_roles_user_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[Role] = mapped_column(role_enum, nullable=False)

    user: Mapped[User] = relationship(back_populates="roles")
