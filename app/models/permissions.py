import uuid
from sqlalchemy import String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from ..database.base_class import Base
from .base_mixins import BaseUUIDModelMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .role_permissions import RolePermission
else:
    RolePermission = "RolePermission"


class Permission(Base, BaseUUIDModelMixin):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    type: Mapped[str] = mapped_column(
        String(2), default="I"
    )  # Global (G), Resource (R), Internal (I), External (E)

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="permission"
    )
    roles = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        overlaps="role_permissions",
    )

    def __str__(self) -> str:
        return f"ID: {self.uuid}, Name: {self.name}"
