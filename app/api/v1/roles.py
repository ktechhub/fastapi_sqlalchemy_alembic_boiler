from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.permissions import Permission
from app.models.role_permissions import RolePermission
from app.models.roles import Role
from app.utils.responses import (
    success_response,
    not_found_response,
    bad_request_response,
)
from app.deps.user import get_user_with_role
from app.schemas.roles import (
    RoleCreateSchema,
    RoleUpdateSchema,
    RoleResponseSchema,
    RoleTotalCountListResponseSchema,
    RoleFilters,
)
from app.models.users import User
from app.cruds.roles import role_crud
from app.database.database import get_async_session


class RoleRouter:
    def __init__(self):
        self.router = APIRouter()
        self.singular = "Role"
        self.plural = "Roles"
        self.crud = role_crud
        self.response_model = RoleResponseSchema
        self.response_list_model = RoleTotalCountListResponseSchema

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
        data: RoleCreateSchema,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        data.name = data.name.lower()
        # check if role already exists
        db_role = await self.crud.get(db, name=data.name)
        if db_role:
            return bad_request_response(f"{self.singular} already exists")
        try:
            role = await self.crud.create(db, data)
        except Exception as e:
            return bad_request_response(str(e))
        return success_response(
            message=f"{self.singular} created successfully", data=role
        )

    async def list(
        self,
        filters: RoleFilters = Depends(),
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        roles = await self.crud.get_multi(
            db=db,
            skip=filters.skip,
            limit=filters.limit,
            sort=filters.sort,
            eager_load=[Role.permissions],
        )
        return {
            "status": status.HTTP_200_OK,
            "detail": f"{self.plural} fetched successfully",
            "data": roles["data"],
            "total_count": roles["total_count"],
        }

    async def get(
        self,
        uuid: str,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        role = await self.crud.get(db, uuid=uuid)
        if not role:
            return not_found_response(f"{self.singular} not found")
        return success_response(
            message=f"{self.singular} fetched successfully", data=role
        )

    async def update(
        self,
        uuid: str,
        data: RoleUpdateSchema,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        role = await self.crud.get(db, uuid=uuid)
        if not role:
            return not_found_response(f"{self.singular} not found")

        try:
            role = await self.crud.update(db, role, data)
        except Exception as e:
            return bad_request_response(str(e))

        return success_response(
            message=f"{self.singular} updated successfully", data=role
        )

    async def delete(
        self,
        uuid: str,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        role = await self.crud.get(db, uuid=uuid)
        if not role:
            return not_found_response(f"{self.singular} not found")

        if role.name in [
            "admin",
            "company",
            "zone_manager",
            "agent",
            "auditor",
            "user",
        ]:
            return bad_request_response(f"{self.singular} cannot be deleted")

        role = await self.crud.remove(db, uuid=uuid)
        return success_response(
            message=f"{self.singular} deleted successfully", data=role
        )
