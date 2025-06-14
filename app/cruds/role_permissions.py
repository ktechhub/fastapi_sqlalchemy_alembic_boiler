from .base import CRUDBase
from ..models.role_permissions import RolePermission
from ..schemas.role_permissions import (
    RolePermissionCreateSchema,
    RolePermissionUpdateSchema,
)


class CRUDRolePermission(
    CRUDBase[RolePermission, RolePermissionCreateSchema, RolePermissionUpdateSchema]
):
    pass


role_permission_crud = CRUDRolePermission(RolePermission)
