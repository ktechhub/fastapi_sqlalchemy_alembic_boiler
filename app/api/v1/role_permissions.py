from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.responses import (
    success_response,
    not_found_response,
    bad_request_response,
)
from app.deps.user import get_user_with_role
from app.schemas.role_permissions import (
    RolePermissionCreateSchema,
    RolePermissionResponseSchema,
    RolePermissionTotalCountListResponseSchema,
    RolePermissionFilters,
)
from app.models.users import User
from app.models.role_permissions import RolePermission
from app.cruds.role_permissions import role_permission_crud
from app.database.database import get_async_session


class RolePermissionRouter:
    def __init__(self):
        self.router = APIRouter()
        self.singular = "Role Permission"
        self.plural = "Role Permissions"
        self.crud = role_permission_crud
        self.response_model = RolePermissionResponseSchema
        self.response_list_model = RolePermissionTotalCountListResponseSchema

        # CRUD Endpoints
        self.router.add_api_route(
            "/", self.assign, methods=["POST"], response_model=self.response_model
        )
        self.router.add_api_route(
            "/", self.list, methods=["GET"], response_model=self.response_list_model
        )
        self.router.add_api_route(
            "/{uuid}", self.get, methods=["GET"], response_model=self.response_model
        )
        self.router.add_api_route(
            "/{uuid}",
            self.remove,
            methods=["DELETE"],
            response_model=self.response_model,
        )

    async def assign(
        self,
        data: RolePermissionCreateSchema,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        existing = await self.crud.get(
            db, role_uuid=data.role_uuid, permission_uuid=data.permission_uuid
        )
        if existing:
            return bad_request_response(f"{self.singular} already assigned")

        try:
            role_permission = await self.crud.create(db, data)
        except Exception as e:
            return bad_request_response(str(e))
        return success_response(
            message=f"{self.singular} assigned successfully", data=role_permission
        )

    async def list(
        self,
        filters: RolePermissionFilters = Depends(),
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        role_permissions = await self.crud.get_multi(
            db=db,
            skip=filters.skip,
            limit=filters.limit,
            sort=filters.sort,
            eager_load=[RolePermission.role, RolePermission.permission],
        )
        return {
            "status": status.HTTP_200_OK,
            "detail": f"{self.plural} fetched successfully",
            "total_count": role_permissions["total_count"],
            "data": role_permissions["data"],
        }

    async def get(
        self,
        uuid: str,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        role_permission = await self.crud.get(
            db,
            uuid=uuid,
            eager_load=[RolePermission.role, RolePermission.permission],
        )
        if not role_permission:
            return not_found_response(f"{self.singular} not found")
        return success_response(
            message=f"{self.singular} fetched successfully", data=role_permission
        )

    async def remove(
        self,
        uuid: str,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        role_permission = await self.crud.get(db, uuid=uuid)
        if not role_permission:
            return not_found_response(f"{self.singular} not found")

        role_permission = await self.crud.remove(db, uuid=uuid)
        return success_response(
            message=f"{self.singular} removed successfully", data=role_permission
        )
