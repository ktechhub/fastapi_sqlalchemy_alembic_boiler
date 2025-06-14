import uuid
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from ..database.base_class import Base
from .base_mixins import BaseUUIDModelMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .roles import Role
    from .permissions import Permission
else:
    Role = "Role"
    Permission = "Permission"


class RolePermission(Base, BaseUUIDModelMixin):
    __tablename__ = "role_permissions"

    role_uuid: Mapped[str] = mapped_column(String(36), ForeignKey("roles.uuid"))
    permission_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("permissions.uuid")
    )

    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="role_permissions",
        overlaps="permissions, roles",
    )
    permission: Mapped["Permission"] = relationship(
        "Permission", back_populates="role_permissions", overlaps="permissions, roles"
    )

    def __str__(self) -> str:
        return f"Role ID: {self.uuid}, Permission ID: {self.permission_uuid}, Role ID: {self.role_uuid}"
