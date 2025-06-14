from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import UUID4, BaseModel
from .base_schema import (
    BaseUUIDSchema,
    BaseResponseSchema,
    BaseTotalCountResponseSchema,
)
from .permissions import PermissionSchema
from .roles import RoleSchema
from .base_filters import BaseFilters

"""RolePermission Schema"""


class RolePermissionBaseSchema(BaseModel):
    role_uuid: UUID4 | str
    permission_uuid: UUID4 | str


class RolePermissionCreateSchema(RolePermissionBaseSchema):
    pass


class RolePermissionUpdateSchema(RolePermissionBaseSchema):
    pass


class RolePermissionSchema(RolePermissionBaseSchema, BaseUUIDSchema):
    role: Optional[Union[RoleSchema, Dict, Any]] = None
    permission: Optional[Union[PermissionSchema, Dict, Any]] = None


class RolePermissionFilter(BaseModel):
    role_uuid: Optional[UUID4 | str] = None
    permission_uuid: Optional[UUID4 | str] = None


class RolePermissionResponseSchema(BaseResponseSchema):
    data: Optional[RolePermissionSchema] = None


class RolePermissionListResponseSchema(BaseResponseSchema):
    data: Optional[List[RolePermissionSchema]] = None


class RolePermissionTotalCountListResponseSchema(BaseTotalCountResponseSchema):
    data: Optional[List[RolePermissionSchema]] = None


class RolePermissionFilters(BaseFilters):
    role_uuid: Optional[UUID4 | str] = None
    permission_uuid: Optional[UUID4 | str] = None
