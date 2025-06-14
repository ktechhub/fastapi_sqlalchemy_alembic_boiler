from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.responses import (
    success_response,
    not_found_response,
    bad_request_response,
)
from app.deps.user import get_user_with_role
from app.schemas.user_roles import (
    UserRoleCreateSchema,
    UserRoleResponseSchema,
    UserRoleTotalCountListResponseSchema,
    UserRoleFilters,
)
from app.models.users import User
from app.models.user_roles import UserRole
from app.cruds.user_roles import user_roles_crud
from app.database.database import get_async_session


class UserRoleRouter:
    def __init__(self):
        self.router = APIRouter()
        self.singular = "User Role"
        self.plural = "User Roles"
        self.crud = user_roles_crud
        self.response_model = UserRoleResponseSchema
        self.response_list_model = UserRoleTotalCountListResponseSchema

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
        data: UserRoleCreateSchema,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        existing = await self.crud.get(
            db, role_uuid=data.role_uuid, user_uuid=data.user_uuid
        )
        if existing:
            return bad_request_response(f"{self.singular} already assigned")

        try:
            user_role = await self.crud.create(db, data)
        except Exception as e:
            return bad_request_response(str(e))
        return success_response(
            message=f"{self.singular} assigned successfully", data=user_role
        )

    async def list(
        self,
        filters: UserRoleFilters = Depends(),
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        main_filters = {}
        if filters.user_uuid:
            main_filters["user_uuid"] = filters.user_uuid.split(",")
        if filters.role_uuid:
            main_filters["role_uuid"] = filters.role_uuid.split(",")
        user_roles = await self.crud.get_multi(
            db,
            skip=filters.skip,
            limit=filters.limit,
            sort=filters.sort,
            eager_load=[UserRole.user, UserRole.role],
            **main_filters,
        )
        return {
            "status": status.HTTP_200_OK,
            "detail": f"{self.plural} fetched successfully",
            "data": user_roles["data"],
            "total_count": user_roles["total_count"],
        }

    async def get(
        self,
        uuid: str,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        user_role = await self.crud.get(
            db, uuid=uuid, eager_load=[UserRole.user, UserRole.role]
        )
        if not user_role:
            return not_found_response(f"{self.singular} not found")
        return success_response(
            message=f"{self.singular} fetched successfully", data=user_role
        )

    async def remove(
        self,
        uuid: str,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        user_role = await self.crud.get(db, uuid=uuid)
        if not user_role:
            return not_found_response(f"{self.singular} not found")

        user_role = await self.crud.remove(db, uuid=uuid)
        return success_response(
            message=f"{self.singular} removed successfully", data=user_role
        )
