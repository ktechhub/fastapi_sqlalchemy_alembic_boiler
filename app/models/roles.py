import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from ..database.base_class import Base
from .base_mixins import BaseUUIDModelMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .role_permissions import RolePermission
    from .user_roles import UserRole
    from .users import User
else:
    RolePermission = "RolePermission"
    UserRole = "UserRole"
    User = "User"


class Role(Base, BaseUUIDModelMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    has_dashboard_access: Mapped[bool] = mapped_column(
        Boolean, nullable=True, default=False
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role"
    )
    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        overlaps="role_permissions",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", overlaps="users"
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_roles",
        primaryjoin="Role.uuid == UserRole.role_uuid",
        secondaryjoin="UserRole.user_uuid == User.uuid",
        overlaps="user_roles",
        viewonly=True,
    )

    def __str__(self) -> str:
        return f"Role ID: {self.uuid}, Name: {self.name}"
