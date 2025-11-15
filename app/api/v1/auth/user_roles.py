from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.responses import (
    success_response,
    not_found_response,
    bad_request_response,
)
from app.deps.user import get_user_with_permission
from app.schemas.user_roles import (
    UserRoleCreateSchema,
    UserRoleResponseSchema,
    UserRoleTotalCountListResponseSchema,
)
from app.cruds.user_roles import user_roles_crud
from app.database.get_session import get_async_session
from app.core.loggers import app_logger as logger
from app.schemas.validate_uuid import UUIDStr
from app.schemas.user_deps import UserDepSchema


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
            "/",
            self.assign,
            methods=["POST"],
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
        data: List[UserRoleCreateSchema],
        user: UserDepSchema = Depends(get_user_with_permission("can_write_user_roles")),
        db: AsyncSession = Depends(get_async_session),
    ):
        for item in data:
            logger.info(f"Creating {self.singular}: {item.model_dump()}")
            existing = await self.crud.get(
                db, role_uuid=item.role_uuid, user_uuid=item.user_uuid
            )
            if existing:
                logger.error(f"{self.singular} already assigned")
                return bad_request_response(f"{self.singular} already assigned")

            try:
                await self.crud.create(db=db, obj_in=item, user_uuid=user.uuid)
            except Exception as e:
                logger.error(f"Error creating {self.singular}: {e}")
                return bad_request_response(str(e))
            logger.info(f"{self.singular} assigned successfully")
        return success_response(message=f"{self.singular} assigned successfully")

    async def remove(
        self,
        uuid: UUIDStr,
        user: UserDepSchema = Depends(
            get_user_with_permission("can_delete_user_roles")
        ),
        db: AsyncSession = Depends(get_async_session),
    ):

        user_role = await self.crud.get(db=db, uuid=uuid)

        if not user_role:
            logger.critical(f"{self.singular} to be deleted with uuid: {uuid}")
            return not_found_response(f"{self.singular} not found")
        if user_role.user_uuid == user.uuid:
            logger.critical(
                f"{self.singular} to be deleted: You cannot delete your own role. Role: {user_role.role_uuid} User: {user.uuid}"
            )
            return bad_request_response(f"You cannot delete your own role")

        logger.critical(
            f"{self.singular} to be deleted: {user_role.to_dict()} by user: {user.uuid}"
        )
        await self.crud.remove(db, db_obj=user_role, user_uuid=user.uuid)
        logger.critical(
            f"{self.singular} with uuid {uuid} removed successfully by user: {user.uuid}"
        )
        return success_response(message=f"{self.singular} removed successfully")
