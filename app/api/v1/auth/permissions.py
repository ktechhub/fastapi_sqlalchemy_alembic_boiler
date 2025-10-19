from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.responses import (
    success_response,
    not_found_response,
    bad_request_response,
)
from app.deps.user import get_user_with_permission
from app.schemas.permissions import (
    PermissionCreateSchema,
    PermissionUpdateSchema,
    PermissionResponseSchema,
    PermissionTotalCountListResponseSchema,
    PermissionFiltersSchema,
)
from app.schemas.validate_uuid import UUIDStr
from app.models.users import User
from app.cruds.permissions import permission_crud
from app.database.get_session import get_async_session
from app.core.loggers import app_logger as logger


def get_internal_label(label: Optional[str] = Query(None, include_in_schema=False)):  # type: ignore
    return label


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
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/",
            self.list,
            methods=["GET"],
            response_model=self.response_list_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/groups/permissions",
            self.list_grouped_permissions,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            summary=f"Get all {self.plural} grouped by action",
            response_model=dict,
        )
        self.router.add_api_route(
            "/{uuid}",
            self.get,
            methods=["GET"],
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/{uuid}",
            self.update,
            methods=["PUT"],
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/{uuid}",
            self.delete,
            methods=["DELETE"],
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )

    async def create(
        self,
        data: PermissionCreateSchema,
        user: User = Depends(get_user_with_permission("can_write_permissions")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Creating {self.singular}: {data.__dict__}")
        data.name = data.name.lower()
        # Check if permission already exists
        permission = await self.crud.get(db=db, name=data.name)
        if permission:
            logger.warning(f"{self.singular} {data.name} already exists")
            return bad_request_response(f"{self.singular} already exists")
        try:
            permission = await self.crud.create(db=db, obj_in=data, user_uuid=user.uuid)
        except Exception as e:
            logger.error(f"Error creating {self.singular}: {str(e)}")
            return bad_request_response(str(e))

        logger.info(f"{self.singular} {data.name} created successfully")
        return success_response(
            message=f"{self.singular} created successfully", data=permission
        )

    async def list(
        self,
        filters: PermissionFiltersSchema = Depends(),
        extra_label: Optional[str] = Depends(get_internal_label),
        user: User = Depends(get_user_with_permission("can_read_permissions")),
        db: AsyncSession = Depends(get_async_session),
    ):
        permissions = await self.crud.get_multi_with_cache(
            db=db,
            **filters.model_dump(),
        )
        logger.info(f"Fetched {len(permissions['data'])} {self.plural}")
        return {
            "status": status.HTTP_200_OK,
            "detail": f"{self.plural} fetched successfully",
            "data": permissions["data"],
            "total_count": permissions["total_count"],
        }

    async def list_grouped_permissions(
        self,
        user: User = Depends(get_user_with_permission("can_read_permissions")),
        db: AsyncSession = Depends(get_async_session),
    ):

        permissions = await self.crud.get_grouped_permissions(db=db)
        logger.info(f"Fetched {len(permissions)} {self.plural}")
        return {
            "status": status.HTTP_200_OK,
            "detail": f"{self.plural} retrieved successfully",
            "data": permissions,
        }

    async def get(
        self,
        uuid: UUIDStr,
        filters: PermissionFiltersSchema = Depends(),
        user: User = Depends(get_user_with_permission("can_read_permissions")),
        db: AsyncSession = Depends(get_async_session),
    ):
        permission = await self.crud.get_with_cache(
            db=db,
            identifier=uuid,
            **filters.model_dump(),
        )
        if not permission:
            logger.warning(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")
        logger.info(f"{self.singular} with uuid {uuid} fetched successfully")
        return success_response(
            message=f"{self.singular} fetched successfully", data=permission
        )

    async def update(
        self,
        uuid: UUIDStr,
        data: PermissionUpdateSchema,
        user: User = Depends(get_user_with_permission("can_write_permissions")),
        db: AsyncSession = Depends(get_async_session),
    ):
        permission = await self.crud.get(db=db, uuid=uuid)
        if not permission:
            logger.warning(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")

        try:
            previous_permission = permission.to_dict()
            new_permission = await self.crud.update(
                db=db, db_obj=permission, obj_in=data, user_uuid=user.uuid
            )
            logger.info(
                f"User {user.uuid} updated role from {previous_permission} to {new_permission.to_dict()}"
            )
        except Exception as e:
            logger.error(f"Error updating {self.singular}: {str(e)}")
            return bad_request_response(str(e))
        return success_response(
            message=f"{self.singular} updated successfully", data=permission
        )

    async def delete(
        self,
        uuid: UUIDStr,
        user: User = Depends(get_user_with_permission("can_delete_permissions")),
        db: AsyncSession = Depends(get_async_session),
    ):
        permission = await self.crud.get(db, uuid=uuid)
        if not permission:
            logger.warning(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")

        logger.critical(
            f"{self.singular} to be deleted: {permission.to_dict()} by user {user.uuid}"
        )
        permission = await self.crud.remove(db, db_obj=permission, user_uuid=user.uuid)

        logger.critical(
            f"{self.singular} {uuid} deleted successfully by user {user.uuid}"
        )
        return success_response(
            message=f"{self.singular} deleted successfully", data=permission
        )
