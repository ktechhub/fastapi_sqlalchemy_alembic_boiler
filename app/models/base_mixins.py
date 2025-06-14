from typing import Any, Dict, Optional
import uuid
from sqlalchemy import DateTime, String, BigInteger, text
from sqlalchemy.sql.sqltypes import Boolean
from sqlalchemy.orm import mapped_column, Mapped
from app.core.config import settings


class BaseModelMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    views: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), index=True
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        index=True,
    )
    delete_protection: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self) -> Dict[str, Any]:
        """Converts model to dictionary, excluding relationship attributes."""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    def to_dict_with_relations(self) -> dict[str, Any]:  # Remove async
        """
        Converts model to dictionary including loaded relationships.
        Only includes relationships that are already loaded.
        """
        # Get base column data
        result = self.to_dict()

        # Add loaded relationships
        for rel in self.__mapper__.relationships:
            # Only include if relationship is already loaded
            if rel.key in self.__dict__:
                value = getattr(self, rel.key)

                if value is None:
                    result[rel.key] = None
                elif isinstance(value, list):
                    # Handle one-to-many/many-to-many
                    result[rel.key] = [
                        item.to_dict() if hasattr(item, "to_dict") else str(item)
                        for item in value
                    ]
                else:
                    # Handle many-to-one/one-to-one
                    result[rel.key] = (
                        value.to_dict() if hasattr(value, "to_dict") else str(value)
                    )

        return result


class SlugBaseModelMixin(BaseModelMixin):
    slug: Mapped[str] = mapped_column(String, index=True, unique=True, nullable=False)


class BaseIDModelMixin(BaseModelMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)


class BaseIDSlugModelMixin(BaseIDModelMixin, SlugBaseModelMixin):
    pass


class BaseUUIDModelMixin(BaseModelMixin):
    if settings.DB_ENGINE == "postgresql":
        # For PostgreSQL, use native UUID type
        uuid: Mapped[str] = mapped_column(
            String(36),
            primary_key=True,
            server_default=text(
                "gen_random_uuid()"
            ),  # PostgreSQL 13+ built-in function
            nullable=False,
        )
    elif settings.DB_ENGINE == "mysql":
        # For MySQL, use UUID() function
        uuid: Mapped[str] = mapped_column(
            String(36),
            primary_key=True,
            server_default=text("(UUID())"),
            nullable=False,
        )
    else:
        # For SQLite or other databases, use Python's uuid4
        uuid: Mapped[str] = mapped_column(
            String(36),
            primary_key=True,
            default=lambda: str(uuid.uuid4()),
            nullable=False,
        )


class BaseUUIDSlugModelMixin(BaseUUIDModelMixin, SlugBaseModelMixin):
    pass


class SoftDeleteMixin:
    soft_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    soft_deleted_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
