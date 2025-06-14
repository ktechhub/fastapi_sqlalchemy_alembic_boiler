from datetime import datetime, timedelta, timezone
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database.base_class import Base
from app.utils.code import generate_verification_code
from .base_mixins import BaseModelMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .users import User
else:
    User = "User"


class VerificationCode(BaseModelMixin, Base):
    """Verification code model."""

    __tablename__ = "verification_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(
        String(8), nullable=False, default=generate_verification_code
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(tz=timezone.utc) + timedelta(hours=12),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="confirm_email"
    )
    user_uuid: Mapped[str] = mapped_column(String(36), ForeignKey("users.uuid"))

    user: Mapped["User"] = relationship("User", back_populates="verification_codes")

    def __str__(self) -> str:
        return f"VerificationCode(id={self.id}, code={self.code}, expires_at={self.expires_at}, user_uuid={self.user_uuid})"
