from typing import Union
from sqlalchemy import Integer, String, ForeignKey, Boolean, JSON, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from ..database.base_class import Base
from .base_mixins import BaseIDModelMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .users import User
else:
    User = "User"


class ActivityLog(BaseIDModelMixin, Base):
    """Activity log model."""

    __tablename__ = "activity_logs"

    user_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.uuid"), nullable=True
    )
    entity: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_data: Mapped[Union[dict, list]] = mapped_column(
        JSON, nullable=True, default={}
    )
    new_data: Mapped[Union[dict, list]] = mapped_column(JSON, nullable=True, default={})
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    delete_protection: Mapped[bool] = mapped_column(Boolean, default=True)
    user: Mapped["User"] = relationship("User", back_populates="activity_logs")

    def __str__(self) -> str:
        return f"ActivityLog(id={self.id}, entity={self.entity}, action={self.action}, user_uuid={self.user_uuid})"
