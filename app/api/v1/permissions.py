from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.responses import (
    success_response,
    not_found_response,
    bad_request_response,
)
from app.deps.user import get_user_with_role
from app.schemas.permissions import (
    PermissionCreateSchema,
    PermissionUpdateSchema,
    PermissionResponseSchema,
    PermissionTotalCountListResponseSchema,
    PermissionFiltersSchema,
)
from app.models.users import User
from app.cruds.permissions import permission_crud
from app.database.database import get_async_session


class PermissionRouter:
    def __init__(self):
        self.router = APIRouter()
        self.singular = "Permission"
        self.plural = "Permissions"
        self.crud = permission_crud
        self.response_model = PermissionResponseSchema
        self.response_list_model = PermissionTotalCountListResponseSchema

        self.router.add_api_route(
            "/",
            self.create,
            methods=["POST"],
            response_model=self.response_model,
        )
        self.router.add_api_route(
            "/",
            self.list,
            methods=["GET"],
            response_model=self.response_list_model,
        )
        self.router.add_api_route(
            "/{uuid}",
            self.get,
            methods=["GET"],
            response_model=self.response_model,
        )
        self.router.add_api_route(
            "/{uuid}",
            self.update,
            methods=["PUT"],
            response_model=self.response_model,
        )
        self.router.add_api_route(
            "/{uuid}",
            self.delete,
            methods=["DELETE"],
            response_model=self.response_model,
        )

    async def create(
        self,
        data: PermissionCreateSchema,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        data.name = data.name.lower()
        # Check if permission already exists
        permission = await self.crud.get(db, name=data.name)
        if permission:
            return bad_request_response(f"{self.singular} already exists")
        try:
            permission = await self.crud.create(db, data)
        except Exception as e:
            return bad_request_response(str(e))
        return success_response(
            message=f"{self.singular} created successfully", data=permission
        )

    async def list(
        self,
        filters: PermissionFiltersSchema = Depends(),
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        permissions = await self.crud.get_multi(
            db, skip=filters.skip, limit=filters.limit, sort=filters.sort
        )
        return {
            "status": status.HTTP_200_OK,
            "detail": f"{self.plural} fetched successfully",
            "data": permissions["data"],
            "total_count": permissions["total_count"],
        }

    async def get(
        self,
        uuid: str,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        permission = await self.crud.get(db, uuid=uuid)
        if not permission:
            return not_found_response(f"{self.singular} not found")
        return success_response(
            message=f"{self.singular} fetched successfully", data=permission
        )

    async def update(
        self,
        uuid: str,
        data: PermissionUpdateSchema,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        permission = await self.crud.get(db, uuid=uuid)
        if not permission:
            return not_found_response(f"{self.singular} not found")

        try:
            permission = await self.crud.update(db, permission, data)
        except Exception as e:
            return bad_request_response(str(e))

        return success_response(
            message=f"{self.singular} updated successfully", data=permission
        )

    async def delete(
        self,
        uuid: str,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        permission = await self.crud.get(db, uuid=uuid)
        if not permission:
            return not_found_response(f"{self.singular} not found")

        permission = await self.crud.remove(db, uuid=uuid)
        return success_response(
            message=f"{self.singular} deleted successfully", data=permission
        )
