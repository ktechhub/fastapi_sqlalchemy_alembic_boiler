from .base import CRUDBase
from ..models.user_roles import UserRole
from ..schemas.user_roles import (
    UserRoleCreateSchema,
    UserRoleUpdateSchema,
)


class CRUDUserRole(CRUDBase[UserRole, UserRoleCreateSchema, UserRoleUpdateSchema]):
    pass


user_roles_crud = CRUDUserRole(UserRole)
