from typing import List, Optional
from pydantic import BaseModel, Field
from .base_schema import (
    BaseUUIDSchema,
    BaseResponseSchema,
    BaseTotalCountResponseSchema,
)
from .base_filters import BaseFilters
from .permissions import PermissionSchema

"""Role Schema"""


class RoleBaseSchema(BaseModel):
    name: str = Field(
        ...,
        description="The unique name of the role (e.g., 'admin', 'user', 'moderator')",
    )
    label: Optional[str] = Field(
        None, description="A human-readable label for the role (e.g., 'Administrator')"
    )
    description: Optional[str] = Field(
        None, description="Optional description of the role and its purpose"
    )
    has_dashboard_access: Optional[bool] = Field(
        False, description="Whether the role has access to the dashboard"
    )


class RoleCreateSchema(RoleBaseSchema):
    pass  # All fields from the base schema are required for creation


class RoleUpdateSchema(RoleBaseSchema):
    name: Optional[str] = Field(None, description="The unique name of the role")
    label: Optional[str] = Field(
        None, description="A human-readable label for the role"
    )
    description: Optional[str] = Field(
        None, description="Optional description of the role and its purpose"
    )
    has_dashboard_access: Optional[bool] = Field(
        None, description="Whether the role has access to the dashboard"
    )


class RoleSchema(RoleBaseSchema, BaseUUIDSchema):
    permissions: Optional[List[PermissionSchema]] = None


class RoleResponseSchema(BaseResponseSchema):
    data: Optional[RoleSchema] = None


class RoleListResponseSchema(BaseResponseSchema):
    data: Optional[List[RoleSchema]] = None


class RoleTotalCountListResponseSchema(BaseTotalCountResponseSchema):
    data: Optional[List[RoleSchema]] = None


class RoleFilters(BaseFilters, RoleBaseSchema, BaseUUIDSchema):
    name: Optional[str] = Field(None, description="Filter by the role name")
    label: Optional[str] = Field(None, description="Filter by the role label")
    description: Optional[str] = Field(
        None, description="Filter by the role description"
    )
    has_dashboard_access: Optional[bool] = Field(
        None, description="Whether the role has access to the dashboard"
    )
    exclude: Optional[str] = Field(
        None,
        description="Comma-separated list of role names to exclude from the results",
    )
