import uuid
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from ..database.base_class import Base
from .base_mixins import BaseUUIDModelMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .users import User
    from .roles import Role
else:
    Role = "Role"
    User = "User"


class UserRole(Base, BaseUUIDModelMixin):
    __tablename__ = "user_roles"

    role_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.uuid"), index=True
    )
    user_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.uuid"), index=True
    )

    role: Mapped["Role"] = relationship(
        "Role", back_populates="user_roles", overlaps="users"
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="user_roles", overlaps="roles"
    )

    def __str__(self) -> str:
        return f"User ID: {self.user_uuid}, Role ID: {self.role}"
