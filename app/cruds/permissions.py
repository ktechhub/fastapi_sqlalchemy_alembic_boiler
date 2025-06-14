from .base import CRUDBase
from ..models.permissions import Permission
from ..schemas.permissions import (
    PermissionCreateSchema,
    PermissionUpdateSchema,
)


class CRUDPermission(
    CRUDBase[Permission, PermissionCreateSchema, PermissionUpdateSchema]
):
    pass


permission_crud = CRUDPermission(Permission)
