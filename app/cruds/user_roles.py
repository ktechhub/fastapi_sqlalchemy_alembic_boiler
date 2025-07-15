from .activity_base import ActivityCRUDBase
from ..models.user_roles import UserRole
from ..schemas.user_roles import (
    UserRoleCreateSchema,
    UserRoleUpdateSchema,
)


class CRUDUserRole(
    ActivityCRUDBase[UserRole, UserRoleCreateSchema, UserRoleUpdateSchema]
):
    pass


user_roles_crud = CRUDUserRole(UserRole)
