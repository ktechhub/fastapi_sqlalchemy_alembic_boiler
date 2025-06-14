from typing import TYPE_CHECKING, Optional
from datetime import timezone, date
from sqlalchemy import Boolean, DateTime, String, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from .base_mixins import BaseUUIDModelMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from .codes import VerificationCode
    from .user_roles import UserRole
    from .roles import Role
else:
    VerificationCode = "VerificationCode"
    UserRole = "UserRole"
    Role = "Role"


class User(Base, BaseUUIDModelMixin, SoftDeleteMixin):
    __tablename__ = "users"

    first_name: Mapped[str] = mapped_column(String(130), nullable=False)
    last_name: Mapped[str] = mapped_column(String(130), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=True)

    # other info
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    national_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=timezone.utc), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    verification_codes: Mapped["VerificationCode"] = relationship(
        "VerificationCode", back_populates="user"
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="user", overlaps="roles"
    )
    roles: Mapped[list["Role"]] = relationship("Role", secondary="user_roles")

    def to_schema_dict(self) -> dict:
        """Convert User model to a dictionary matching UserSchema structure"""
        base_dict = self.to_dict()  # Converts User fields to a dictionary
        # Make sure user_roles is preloaded and add roles to the response
        base_dict["roles"] = [role.to_dict() for role in self.roles]
        return base_dict
