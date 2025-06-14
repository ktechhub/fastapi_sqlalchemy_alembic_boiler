from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from .base_schema import (
    BaseUUIDSchema,
    BaseResponseSchema,
    BaseSchema,
    BaseTotalCountResponseSchema,
)
from .base_filters import BaseFilters

"""Permission Schema"""


class PermissionBaseSchema(BaseModel):
    name: str = Field(
        ...,
        description="The unique name of the permission (e.g., 'create_user', 'delete_property')",
    )
    label: Optional[str] = Field(
        None, description="A human-readable label for the permission"
    )
    description: Optional[str] = Field(
        None, description="Optional description of the permission"
    )


class PermissionCreateSchema(PermissionBaseSchema):
    pass  # All fields from the base schema are required by default


class PermissionUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, description="The unique name of the permission")
    label: Optional[str] = Field(
        None, description="A human-readable label for the permission"
    )
    description: Optional[str] = Field(
        None, description="Optional description of the permission"
    )


class PermissionSchema(PermissionBaseSchema, BaseUUIDSchema):
    pass


class PermissionResponseSchema(BaseResponseSchema):
    data: Optional[PermissionSchema] = None


class PermissionListResponseSchema(BaseResponseSchema):
    data: Optional[List[PermissionSchema]] = None


class PermissionTotalCountListResponseSchema(BaseTotalCountResponseSchema):
    data: Optional[List[PermissionSchema]] = None


class PermissionFiltersSchema(BaseFilters, PermissionSchema):
    name: Optional[str] = Field(
        None, description="Filter by the name of the permission"
    )
    label: Optional[str] = Field(None, description="Filter by the permission label")
    description: Optional[str] = Field(
        None, description="Filter by the permission description"
    )
