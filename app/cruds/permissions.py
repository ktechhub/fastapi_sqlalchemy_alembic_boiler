from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict
from sqlalchemy import select
from ..core.defaults import default_actions
from .activity_base import ActivityCRUDBase
from ..models.permissions import Permission
from ..schemas.permissions import (
    PermissionCreateSchema,
    PermissionUpdateSchema,
)


class CRUDPermission(
    ActivityCRUDBase[Permission, PermissionCreateSchema, PermissionUpdateSchema]
):
    async def get_grouped_permissions(self, db: AsyncSession) -> list[dict]:
        grouped_permissions = defaultdict(list)

        result = await db.execute(select(Permission))
        all_permissions = result.scalars().all()

        for perm in all_permissions:
            for action in default_actions:
                if perm.name.endswith(f"_{action}"):
                    grouped_permissions[action].append(
                        {
                            "uuid": perm.uuid,
                            "name": perm.name,
                            "label": perm.label,
                            "description": perm.description,
                        }
                    )
                    break

        return dict(grouped_permissions)


permission_crud = CRUDPermission(Permission)
