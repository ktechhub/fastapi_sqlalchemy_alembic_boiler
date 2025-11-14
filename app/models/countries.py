from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base_class import Base
from .base_mixins import BaseIDSlugModelMixin

if TYPE_CHECKING:
    from .users import User
else:
    User = "User"


class Country(Base, BaseIDSlugModelMixin):
    __tablename__ = "countries"

    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Display name
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="country", viewonly=True
    )

    def __str__(self) -> str:
        return f"Country(uuid={self.uuid}, name={self.name}, slug={self.slug})"
