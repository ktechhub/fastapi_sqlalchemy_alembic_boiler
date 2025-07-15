from typing import Type
from .activity_base import ActivityCRUDBase
from ..models.roles import Role
from ..schemas.roles import (
    RoleCreateSchema,
    RoleUpdateSchema,
)
from ..core.config import settings


class CRUDRole(ActivityCRUDBase[Role, RoleCreateSchema, RoleUpdateSchema]):
    def __init__(self, model: Type[Role], ttl: int = settings.CACHE_TTL_LONG):
        super().__init__(model, ttl=ttl)


role_crud = CRUDRole(Role)
