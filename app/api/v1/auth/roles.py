from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.permissions import Permission
from app.models.role_permissions import RolePermission
from app.models.roles import Role
from app.schemas.role_permissions import RolePermissionCreateSchema
from app.utils.responses import (
    success_response,
    not_found_response,
    bad_request_response,
)
from app.deps.user import get_user_with_permission
from app.schemas.roles import (
    RoleCreateSchema,
    RoleUpdateSchema,
    RoleResponseSchema,
    RoleTotalCountListResponseSchema,
    RoleFilters,
    RoleWithPermissionsSchema,
    RoleWithPermissionsUpdateSchema,
)
from app.models.users import User
from app.cruds.roles import role_crud
from app.cruds.role_permissions import role_permission_crud
from app.cruds.permissions import permission_crud

from app.database.get_session import get_async_session
from app.core.loggers import app_logger as logger
from app.cruds.activity_logs import activity_log_crud
from app.schemas.activity_logs import ActivityLogCreateSchema
from app.core.defaults import default_roles
from app.schemas.validate_uuid import UUIDStr


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
            response_model_exclude_unset=True,
        )

        self.router.add_api_route(
            "/with-permissions",
            self.create_role_with_permissions,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Creating {self.singular} with permissions",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/with-permissions/{uuid}",
            self.update_role_with_permissions,
            methods=["PUT"],
            status_code=status.HTTP_200_OK,
            summary=f"Update {self.singular} with permissions",
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
        data: RoleCreateSchema,
        user: User = Depends(get_user_with_permission("can_write_roles")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Creating {self.singular}: {data.__dict__}")
        data.name = data.name.lower()
        # check if role already exists
        db_role = await self.crud.get(db=db, name=data.name)
        if db_role:
            logger.error(f"{self.singular} already exists")
            return bad_request_response(f"{self.singular} already exists")
        try:
            role = await self.crud.create(db=db, obj_in=data)
        except Exception as e:
            logger.error(f"Error creating {self.singular}: {str(e)}")
            return bad_request_response(str(e))
        await activity_log_crud.create(
            db=db,
            obj_in=ActivityLogCreateSchema(
                user_uuid=user.uuid,
                entity=self.singular,
                action="create",
                previous_data={},
                new_data=role.to_dict(),
                description=f"{self.singular} created successfully",
            ),
        )
        logger.info(f" {role.name} {self.singular} created successfully")
        return success_response(
            message=f"{self.singular} created successfully", data=role.to_dict()
        )

    async def create_role_with_permissions(
        self,
        data: RoleWithPermissionsSchema,
        db: AsyncSession = Depends(get_async_session),
        user: User = Depends(get_user_with_permission("can_write_roles")),
    ):
        logger.info(
            f"Creating {self.singular} with permissions: {data.__dict__} by user {user.uuid}"
        )
        data.name = data.name.lower()
        # check if role already exists
        db_role = await self.crud.get(db=db, name=data.name)
        if db_role:
            logger.error(f"{self.singular} already exists")
            return bad_request_response(f"{self.singular} already exists")
        try:
            permissions = data.permissions
            del data.permissions
            role = await self.crud.create(db=db, obj_in=data)
            role_permissions = []
            for permission_uuid in permissions:

                perm: Permission = await permission_crud.get(
                    db=db, uuid=permission_uuid
                )
                if not perm:
                    logger.error(
                        f"Permission with uuid {permission_uuid} not found, skipping assignment"
                    )
                    continue

                role_permissions.append(
                    RolePermissionCreateSchema(
                        role_uuid=role.uuid, permission_uuid=permission_uuid
                    )
                )

            await role_permission_crud.create_multi(db=db, objs_in=role_permissions)
            logger.info(
                f"{self.singular} created successfully with {len(role_permissions)} permissions"
            )
        except Exception as e:
            logger.error(f"Error creating {self.singular}: {str(e)}")
            return bad_request_response(str(e))
        stmt = (
            select(Role)
            .options(joinedload(Role.permissions))
            .where(Role.uuid == role.uuid)
        )
        role = await self.crud.get(
            db=db,
            statement=stmt,
        )
        await activity_log_crud.create(
            db=db,
            obj_in=ActivityLogCreateSchema(
                user_uuid=user.uuid,
                entity=self.singular,
                action="create",
                previous_data={},
                new_data=role.to_dict(),
                description=f"{self.singular} created successfully with permissions",
            ),
        )
        return success_response(
            message=f"{self.singular} created successfully with permissions", data=role
        )

    async def list(
        self,
        filters: RoleFilters = Depends(),
        # user: User = Depends(get_user_with_permission("can_read_roles")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Fetching {self.plural} with filters: {filters.__dict__}")
        query_filters = []
        if filters.exclude is not None:
            query_filters.append(Role.name.not_in(filters.exclude.split(",")))

        # Use cached version for better performance
        roles = await self.crud.get_multi_with_cache(
            db=db,
            unique_records=True,
            query_filters=query_filters,
            **filters.model_dump(),
        )
        logger.info(f"Fetched {len(roles['data'])} {self.plural}")
        return {
            "status": status.HTTP_200_OK,
            "detail": f"{self.plural} fetched successfully",
            "data": roles["data"],
            "total_count": roles["total_count"],
        }

    async def get(
        self,
        uuid: UUIDStr,
        filters: RoleFilters = Depends(),
        user: User = Depends(get_user_with_permission("can_read_roles")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Fetching {self.singular} with uuid: {uuid}")

        # Use cached version for better performance
        role = await self.crud.get_with_cache(
            db=db,
            identifier=uuid,
            **filters.model_dump(),
        )

        if not role:
            logger.error(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")
        logger.info(f"{self.singular} fetched successfully")

        return success_response(
            message=f"{self.singular} fetched successfully", data=role
        )

    async def update(
        self,
        uuid: UUIDStr,
        data: RoleUpdateSchema,
        user: User = Depends(get_user_with_permission("can_write_roles")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Updating {self.singular} with uuid: {uuid}")
        role = await self.crud.get(db, uuid=uuid)
        if not role:
            logger.error(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")

        try:
            previous_role = role.to_dict()
            role = await self.crud.update(db, db_obj=role, obj_in=data)
            logger.info(
                f"User {user.uuid} updated {self.singular} from {previous_role} to {role.to_dict()}"
            )

        except Exception as e:
            logger.error(f"Error updating {self.singular}: {str(e)}")
            return bad_request_response(str(e))
        logger.info(f"{self.singular} updated successfully")
        stmt = (
            select(Role).options(joinedload(Role.permissions)).where(Role.uuid == uuid)
        )
        prev_data = role.to_dict()
        updated_role = await self.crud.get(db, statement=stmt)
        await activity_log_crud.create(
            db=db,
            obj_in=ActivityLogCreateSchema(
                user_uuid=user.uuid,
                entity=self.singular,
                action="update",
                previous_data=prev_data,
                new_data=updated_role.to_dict(),
                description=f"{self.singular} updated successfully",
            ),
        )
        return success_response(
            message=f"{self.singular} updated successfully", data=updated_role
        )

    async def update_role_with_permissions(
        self,
        uuid: UUIDStr,
        data: RoleWithPermissionsUpdateSchema,
        user: User = Depends(get_user_with_permission("can_write_roles")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Updating {self.singular} with uuid: {uuid}")
        role = await self.crud.get(db, uuid=uuid)
        if not role:
            logger.error(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")
        premissions_uuids = data.permissions
        try:
            previous_role = role.to_dict()
            del data.permissions
            role = await self.crud.update(db, db_obj=role, obj_in=data)
            logger.info(
                f"User {user.uuid} updated {self.singular} from {previous_role} to {role.to_dict()}"
            )
            if premissions_uuids is not None:
                # Remove existing role permissions
                await role_permission_crud.remove_multi(db, role_uuid=role.uuid)
                logger.info(
                    f"Existing permissions removed for {self.singular} with uuid {uuid}"
                )
                role_permissions = []
                for permission_uuid in premissions_uuids:
                    perm: Permission = await permission_crud.get(
                        db=db, uuid=permission_uuid
                    )
                    if not perm:
                        logger.error(
                            f"Permission with uuid {permission_uuid} not found, skipping assignment"
                        )
                        continue

                    role_permissions.append(
                        RolePermissionCreateSchema(
                            role_uuid=role.uuid, permission_uuid=permission_uuid
                        )
                    )

                await role_permission_crud.create_multi(db=db, objs_in=role_permissions)
                logger.info(
                    f"{self.singular} updated successfully with {len(role_permissions)} permissions"
                )
        except Exception as e:
            logger.error(f"Error updating {self.singular}: {str(e)}")
            return bad_request_response(str(e))
        logger.info(f"{self.singular} updated successfully")
        stmt = (
            select(Role).options(joinedload(Role.permissions)).where(Role.uuid == uuid)
        )
        prev_data = role.to_dict()
        updated_role = await self.crud.get(db, statement=stmt)
        await activity_log_crud.create(
            db=db,
            obj_in=ActivityLogCreateSchema(
                user_uuid=user.uuid,
                entity=self.singular,
                action="update",
                previous_data=prev_data,
                new_data=updated_role.to_dict(),
                description=f"{self.singular} updated successfully",
            ),
        )
        return success_response(
            message=f"{self.singular} updated successfully", data=updated_role
        )

    async def delete(
        self,
        uuid: UUIDStr,
        user: User = Depends(get_user_with_permission("can_delete_roles")),
        db: AsyncSession = Depends(get_async_session),
    ):

        role: Role = await self.crud.get(db, uuid=uuid)
        if not role:
            logger.error(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")
        logger.critical(
            f"{self.singular} to be deleted: {role.to_dict()} by user {user.uuid}"
        )
        if role.delete_protection:
            logger.critical(
                f"{self.singular} with uuid {uuid} has delete protection enabled"
            )
            return bad_request_response(
                f"This {self.singular} cannot be deleted! Remove the delete protection first."
            )

        if role.name in [item["name"] for item in default_roles]:
            logger.critical(
                f"{self.singular} with uuid {uuid} is a default role and cannot be deleted"
            )
            return bad_request_response(f"{self.singular} cannot be deleted")
        await role_permission_crud.remove_multi(db, role_uuid=role.uuid)
        logger.critical("Role Permissions successfully removed for role")
        await self.crud.remove(db, db_obj=role, user_uuid=user.uuid)
        logger.critical(
            f"{self.singular} {uuid} deleted successfully by user {user.uuid}"
        )
        return success_response(message=f"{self.singular} deleted successfully")
