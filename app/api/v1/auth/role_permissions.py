from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.permissions import Permission
from app.utils.responses import (
    success_response,
    not_found_response,
    bad_request_response,
)
from app.deps.user import get_user_with_permission
from app.schemas.role_permissions import (
    RolePermissionCreateMultiSchema,
    RolePermissionCreateSchema,
    RolePermissionResponseSchema,
    RolePermissionTotalCountListResponseSchema,
    RolePermissionFilters,
)
from app.models.users import User
from app.models.role_permissions import RolePermission
from app.cruds.role_permissions import role_permission_crud
from app.database.get_session import get_async_session
from app.core.loggers import app_logger as logger
from app.cruds.permissions import permission_crud
from app.cruds.activity_logs import activity_log_crud
from app.schemas.activity_logs import ActivityLogCreateSchema


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
            "/",
            self.assign,
            methods=["POST"],
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/multi",
            self.assign_multi,
            methods=["POST"],
            response_model=self.response_list_model,
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
            "/{uuid}",
            self.get,
            methods=["GET"],
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/{uuid}",
            self.remove,
            methods=["DELETE"],
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )

    async def assign(
        self,
        data: RolePermissionCreateSchema,
        user: User = Depends(get_user_with_permission("can_write_role_permissions")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Creating {self.singular}: {data.__dict__} by user {user.uuid}")
        existing = await self.crud.get(
            db, role_uuid=data.role_uuid, permission_uuid=data.permission_uuid
        )
        if existing:
            logger.error(f"{self.singular} already assigned")
            return bad_request_response(f"{self.singular} already assigned")

        try:
            role_permission = await self.crud.create(
                db=db, obj_in=data, user_uuid=user.uuid
            )
            logger.info(f"{self.singular} assigned successfully")
        except Exception as e:
            logger.error(f"Error assigning {self.singular}: {str(e)}")
            return bad_request_response(str(e))

        return success_response(
            message=f"{self.singular} assigned successfully",
            data=role_permission.to_dict(),
        )

    async def assign_multi(
        self,
        permission_data: RolePermissionCreateMultiSchema,
        user: User = Depends(get_user_with_permission("can_write_permissions")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(
            f"Creating multiple {self.plural}: {permission_data.__dict__} by user {user.uuid}"
        )
        """
        Assign multiple permissions to a role.
        """
        role_permissions = []

        for permission in permission_data.permissions:
            perm: Permission = await permission_crud.get(db=db, uuid=permission)
            if not perm:
                logger.error(f"Permission with uuid {permission} not found")
                continue
            if await self.crud.get(
                db=db,
                role_uuid=permission_data.role_uuid,
                permission_uuid=perm.uuid,
            ):
                logger.error(
                    f"Permission with uuid {perm.uuid} already assigned to role {permission_data.role_uuid}"
                )
                continue
            role_permissions.append(
                RolePermissionCreateSchema(
                    role_uuid=permission_data.role_uuid, permission_uuid=perm.uuid
                )
            )

        role_permissions = await self.crud.create_multi(
            db=db, objs_in=role_permissions, user_uuid=user.uuid
        )
        logger.info(
            f"{self.plural} created successfully"
            if len(role_permissions)
            else f"{self.plural} already assigned"
        )
        return {
            "status": (
                status.HTTP_201_CREATED if len(role_permissions) else status.HTTP_200_OK
            ),
            "detail": (
                f"{self.plural} created successfully"
                if len(role_permissions)
                else f"{self.plural} already assigned"
            ),
            "total_count": len(role_permissions),
            "data": [role_permission.to_dict() for role_permission in role_permissions],
        }

    async def list(
        self,
        filters: RolePermissionFilters = Depends(),
        user: User = Depends(get_user_with_permission("can_read_role_permissions")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Fetching {self.plural} with filters: {filters.__dict__}")
        role_permissions = await self.crud.get_multi_with_cache(
            db=db,
            unique_records=True,
            **filters.model_dump(),
        )
        logger.info(f"{self.plural} fetched successfully")

        return {
            "status": status.HTTP_200_OK,
            "detail": f"{self.plural} fetched successfully",
            "total_count": role_permissions["total_count"],
            "data": role_permissions["data"],
        }

    async def get(
        self,
        uuid: str,
        # user: User = Depends(get_user_with_permission("can_read_role_permissions")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Fetching {self.singular} with uuid: {uuid}")
        role_permission = await self.crud.get_with_cache(
            db,
            identifier=uuid,
            include_relations="role,permission",
        )
        if not role_permission:
            logger.error(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")
        logger.info(f"{self.singular} fetched successfully")
        return success_response(
            message=f"{self.singular} fetched successfully",
            data=role_permission,
        )

    async def remove(
        self,
        uuid: str,
        user: User = Depends(get_user_with_permission("can_delete_role_permissions")),
        db: AsyncSession = Depends(get_async_session),
    ):
        role_permission = await self.crud.get(db, uuid=uuid)
        if not role_permission:
            logger.error(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")

        logger.critical(
            f"{self.singular} to be removed: {role_permission.to_dict()} by user {user.uuid}"
        )
        role_permission = await self.crud.remove(
            db, db_obj=role_permission, user_uuid=user.uuid
        )
        logger.critical(
            f"{self.singular} with {uuid} removed successfully by user {user.uuid}"
        )
        return success_response(
            message=f"{self.singular} removed successfully",
            data=role_permission.to_dict(),
        )
