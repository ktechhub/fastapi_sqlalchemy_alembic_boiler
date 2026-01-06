from typing import Optional
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from datetime import datetime
from .validate_uuid import UUIDStr


class BaseSchema(BaseModel):
    """
    BaseSchema provides common fields for entities using an integer primary key (ID).
    Includes fields for tracking views and timestamps for creation and updates.
    """

    id: Optional[int] = Field(
        default=None, description="Unique integer identifier of the entity."
    )
    views: Optional[int] = Field(
        default=None, description="Number of times this entity has been viewed."
    )
    created_at: Optional[datetime] = Field(
        default=None, description="Timestamp indicating when the entity was created."
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp indicating when the entity was last updated.",
    )

    model_config = ConfigDict(from_attributes=True)


class BaseUUIDSchema(BaseModel):
    """
    BaseUUIDSchema provides common fields for entities using UUID as the primary identifier.
    Includes fields for tracking views and timestamps for creation and updates.
    """

    uuid: Optional[UUIDStr] = Field(
        default=None, description="Unique UUID identifier of the entity."
    )
    views: Optional[int] = Field(
        default=None, description="Number of times this entity has been viewed."
    )
    created_at: Optional[datetime] = Field(
        default=None, description="Timestamp indicating when the entity was created."
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp indicating when the entity was last updated.",
    )
    delete_protection: Optional[bool] = Field(
        default=False,
        description="Flag indicating whether the entity is protected from deletion.",
    )

    model_config = ConfigDict(from_attributes=True)


class BaseSlugSchema(BaseSchema):
    """
    BaseSlugSchema extends BaseSchema by adding a slug field.
    Suitable for models where a human-readable unique identifier (slug) is needed.
    """

    slug: Optional[str] = Field(
        default=None,
        description="Unique human-readable identifier for the entity, often used in URLs.",
    )

    model_config = ConfigDict(from_attributes=True)


class BaseSlugUUIDSchema(BaseUUIDSchema):
    """
    BaseSlugUUIDSchema extends BaseUUIDSchema by adding a slug field.
    Suitable for models where a human-readable unique identifier (slug) is needed.
    """

    slug: Optional[str] = Field(
        default=None,
        description="Unique human-readable identifier for the entity, often used in URLs.",
    )

class BaseResponseSchema(BaseModel):
    """
    BaseResponseSchema represents a standard response containing a status code and a message.
    Can be used as a base for API responses.
    """

    status: int = Field(
        description="HTTP status code indicating the result of the operation."
    )
    detail: str = Field(
        description="A detailed message or description of the response."
    )

    model_config = ConfigDict(from_attributes=True)


class BaseTotalCountResponseSchema(BaseModel):
    """
    BaseTotalCountResponseSchema extends BaseResponseSchema by including a total count field.
    Useful for responses involving paginated or counted resources.
    """

    status: int = Field(
        description="HTTP status code indicating the result of the operation."
    )
    detail: str = Field(
        description="A detailed message or description of the response."
    )
    total_count: int = Field(
        description="The total count of items relevant to the response."
    )

    model_config = ConfigDict(from_attributes=True)
