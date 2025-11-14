from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from ..database.base_class import Base
from .base_mixins import BaseUUIDModelMixin

if TYPE_CHECKING:
    from .users import User
else:
    User = "User"


class UserSession(Base, BaseUUIDModelMixin):
    """User session model for tracking user login sessions."""

    __tablename__ = "user_sessions"

    user_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.uuid"), nullable=False, index=True
    )
    token_jti: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    browser_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    os: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    os_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    location_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_country: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    location_country_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    last_active: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    closed_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="user_sessions")

    def __str__(self) -> str:
        return f"UserSession(uuid={self.uuid}, user_uuid={self.user_uuid}, is_active={self.is_active})"
