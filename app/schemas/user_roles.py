from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import UUID4, BaseModel
from .base_schema import (
    BaseUUIDSchema,
    BaseResponseSchema,
    BaseTotalCountResponseSchema,
)
from .users import UserSchema
from .roles import RoleSchema
from .base_filters import BaseFilters

"""UserRole Schema"""


class UserRoleBaseSchema(BaseModel):
    role_uuid: UUID4 | str
    user_uuid: UUID4 | str


class UserRoleCreateSchema(UserRoleBaseSchema):
    pass


class UserRoleUpdateSchema(UserRoleBaseSchema):
    pass


class UserRoleSchema(UserRoleBaseSchema, BaseUUIDSchema):
    user: Optional[Union[UserSchema, Dict, Any]] = None
    role: Optional[Union[RoleSchema, Dict, Any]] = None


class UserRoleFilter(BaseModel):
    role_uuid: Optional[UUID4 | str] = None
    user_uuid: Optional[UUID4 | str] = None


class UserRoleResponseSchema(BaseResponseSchema):
    data: Optional[UserRoleSchema] = None


class UserRoleListResponseSchema(BaseResponseSchema):
    data: Optional[List[UserRoleSchema]] = None


class UserRoleTotalCountListResponseSchema(BaseTotalCountResponseSchema):
    data: Optional[List[UserRoleSchema]] = None


class UserRoleFilters(BaseFilters):
    role_uuid: Optional[UUID4 | str] = None
    user_uuid: Optional[UUID4 | str] = None
