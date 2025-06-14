from .base import CRUDBase
from ..models.roles import Role
from ..schemas.roles import (
    RoleCreateSchema,
    RoleUpdateSchema,
)


class CRUDRole(CRUDBase[Role, RoleCreateSchema, RoleUpdateSchema]):
    pass


role_crud = CRUDRole(Role)
