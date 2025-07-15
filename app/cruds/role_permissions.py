from .activity_base import ActivityCRUDBase
from ..models.role_permissions import RolePermission
from ..schemas.role_permissions import (
    RolePermissionCreateSchema,
    RolePermissionUpdateSchema,
)


class CRUDRolePermission(
    ActivityCRUDBase[
        RolePermission, RolePermissionCreateSchema, RolePermissionUpdateSchema
    ]
):
    pass


role_permission_crud = CRUDRolePermission(RolePermission)
