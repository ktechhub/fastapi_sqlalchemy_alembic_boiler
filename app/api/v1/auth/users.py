from typing import List
import urllib.parse
from fastapi import APIRouter, Depends, status
from sqlalchemy import and_, not_, or_, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.roles import Role
from app.utils.responses import (
    success_response,
    not_found_response,
    bad_request_response,
)
from app.deps.user import get_user_with_permission
from app.schemas.users import (
    AdminUserCreateSchema,
    UserResponseWithoutRoutesSchema,
    UserTotalCountListResponseSchema,
    UserFilters,
    AdminUpdateUserSchema,
    AdminSendEmailSchema,
)
from app.schemas.user_roles import UserRoleCreateSchema
from app.models.users import User
from app.cruds.users import user_crud
from app.cruds.roles import role_crud
from app.cruds.user_roles import user_roles_crud
from app.database.get_session import get_async_session
from app.core.config import settings
from app.core.loggers import app_logger as logger
from app.services.redis_push import redis_lpush
from app.cruds.activity_logs import activity_log_crud
from app.schemas.activity_logs import ActivityLogCreateSchema
from app.schemas.validate_uuid import UUIDStr


class UserRouter:
    def __init__(self):
        self.router = APIRouter()
        self.singular = "User"
        self.plural = "Users"
        self.crud = user_crud
        self.response_model = UserResponseWithoutRoutesSchema
        self.response_list_model = UserTotalCountListResponseSchema

        # CRUD Endpoints
        self.router.add_api_route(
            "/", self.create, methods=["POST"], response_model=self.response_model
        )
        self.router.add_api_route(
            "/resend-initialization-email/",
            self.resend_initialization_email,
            methods=["POST"],
            response_model=self.response_model,
            summary="Resend initialization email to a user",
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
        self.router.add_api_route(
            "/{user_uuid}/roles/{role_uuid}",
            self.remove_user_roles,
            methods=["DELETE"],
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )

    async def create(
        self,
        data: List[AdminUserCreateSchema],
        user: User = Depends(get_user_with_permission("can_write_users")),
        db: AsyncSession = Depends(get_async_session),
    ):

        if len(data) > 5:
            logger.error("You can only create 5 users at a time")
            return bad_request_response("You can only create 5 users at a time")

        logger.info(f"Creating {len(data)} {self.plural} by user {user.uuid}")
        activity_logs = []
        for user_data in data:
            user_data.email = user_data.email.lower()
            # check if user already exists
            db_user = await self.crud.get(db, email=user_data.email, soft_deleted=False)
            if db_user:
                logger.error(f"{self.singular} already exists")
                return bad_request_response(f"{self.singular} already exists")

            soft_deleted_user = await self.crud.get(
                db, email=user_data.email, soft_deleted=True
            )
            if soft_deleted_user:
                logger.info(
                    f"User {soft_deleted_user.email} already exists but soft deleted"
                )
                # restore the user
                prev_user_data = soft_deleted_user.to_dict()
                new_user = await self.crud.restore(
                    db,
                    db_obj=soft_deleted_user,
                    fields={
                        "is_active": True,
                        "soft_deleted": False,
                        "soft_deleted_at": None,
                        "is_verified": False,
                        "verified_at": None,
                        "password": None,
                    },
                )
                activity_logs.append(
                    ActivityLogCreateSchema(
                        user_uuid=user.uuid,
                        entity=self.singular,
                        action="update",
                        previous_data=prev_user_data,
                        new_data=new_user.to_dict(),
                        description=f"User {soft_deleted_user.email} restored successfully",
                    )
                )
                logger.info(f"User {soft_deleted_user.email} restored by {user.email}")
            # check for all the roles to be assigned
            roles = await role_crud.get_multi(
                db, limit=-1, uuid=user_data.role_uuid.split(",")
            )

            if len(roles["data"]) != len(user_data.role_uuid.split(",")):
                logger.error(f"All roles not found for {user_data.email}")
                return bad_request_response(
                    f"All roles not found for {user_data.email}"
                )

            # Create the user in the database
            try:
                del user_data.role_uuid
                if not soft_deleted_user:
                    logger.info(f"Creating new user {user_data.email}")
                    new_user = await self.crud.create(
                        db, obj_in=user_data, user_uuid=user.uuid
                    )
                    logger.info(f"User {user_data.email} created successfully")
                # Assign roles to the user
                for role in roles["data"]:
                    await user_roles_crud.create(
                        db=db,
                        obj_in=UserRoleCreateSchema(
                            user_uuid=new_user.uuid, role_uuid=role.uuid
                        ),
                        user_uuid=user.uuid,
                    )
                    logger.info(f"Role {role.name} assigned to user {new_user.email}")

                stmt = (
                    select(User)
                    .options(joinedload(User.roles))
                    .where(User.uuid == user.uuid)
                )

                db_user: User = await self.crud.get(db=db, statement=stmt)
            except Exception as e:
                logger.error(f"Error creating {self.singular}: {str(e)}")
                return bad_request_response(str(e))

            # Send an initialization email
            initialize_url = f"{settings.FRONTEND_URL}/auth/initialize-account?email={urllib.parse.quote(new_user.email)}"
            redis_lpush(
                {
                    "queue_name": "notifications",
                    "operation": "send_email",
                    "data": {
                        "to": new_user.email,
                        "subject": "Initialize your account",
                        "salutation": f"Hi,",
                        "body": f"""
                            <p>Welcome! Click the link below to initialize your account and set your password:</p>
                            <p><a href="{initialize_url}">Initialize Account</a></p>
                            <p>If you didn’t request this, you can safely ignore this email.</p>
                        """,
                        "queue_name": "notifications",
                    },
                }
            )
            logger.info(f"Initialization email sent to {new_user.email}")
        logger.info(f"{len(data)} {self.singular} created successfully")

        return success_response(
            message=f"{len(data)} {self.plural} created successfully and initialization email sent",
        )

    async def resend_initialization_email(
        self,
        data: AdminSendEmailSchema,
        user: User = Depends(get_user_with_permission("can_write_users")),
        db: AsyncSession = Depends(get_async_session),
    ):
        email = data.email.lower()
        db_user = await self.crud.get(db, email=email)
        if not db_user:
            logger.error(f"{self.singular} with email {email} not found")
            logger.error(f"{self.singular} not found")
            return not_found_response(f"{self.singular} not found")
        if db_user.is_verified:
            logger.error(f"{self.singular} is already verified")
            return bad_request_response(f"{self.singular} is already verified")
        initialize_url = (
            f"{settings.FRONTEND_URL}/initialize?email={urllib.parse.quote(email)}"
        )

        redis_lpush(
            {
                "queue_name": "notifications",
                "operation": "send_email",
                "data": {
                    "to": db_user.email,
                    "subject": "Initialize your account",
                    "salutation": f"Hi,",
                    "body": f"""
                    <p>Welcome! Click the link below to initialize your account and set your password:</p>
                    <p><a href="{initialize_url}">Initialize Account</a></p>
                    <p>If you didn’t request this, you can safely ignore this email.</p>
                """,
                    "queue_name": "notifications",
                },
            }
        )
        logger.info(f"Initialization email sent to {db_user.email}")

        return success_response(
            message=f"Initialization email sent to {self.singular} successfully",
        )

    async def list(
        self,
        filters: UserFilters = Depends(),
        user: User = Depends(get_user_with_permission("can_read_users")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Fetching {self.plural} with filters: {filters.__dict__}")

        query_filters = []
        if filters.user_type is not None:
            query_filters.append(
                User.roles.any(
                    Role.name.in_(
                        [role.strip() for role in filters.user_type.split(",")]
                    )
                )
            )

        if filters.exclude_user_types is not None:
            query_filters.append(
                User.roles.any(
                    Role.name.not_in(
                        [role.strip() for role in filters.exclude_user_types.split(",")]
                    )
                )
            )
        if filters.has_dashboard_access is not None:
            query_filters.append(
                User.roles.any(
                    Role.has_dashboard_access == filters.has_dashboard_access
                )
            )

        users = await self.crud.get_multi_with_cache(
            db,
            unique_records=True,
            query_filters=query_filters,
            **filters.model_dump(),
        )
        logger.info(f"Fetched {len(users['data'])} {self.plural}")
        return {
            "status": status.HTTP_200_OK,
            "detail": "Users fetched successfully",
            "total_count": users["total_count"],
            "data": users["data"],
        }

    async def get(
        self,
        uuid: UUIDStr,
        user: User = Depends(get_user_with_permission("can_read_users")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Fetching {self.singular} with uuid: {uuid}")
        stmt = select(User).options(joinedload(User.roles)).where(User.uuid == uuid)
        db_user = await self.crud.get(db, statement=stmt)
        if not db_user:
            logger.error(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")
        logger.info(f"{self.singular} with uuid {uuid} fetched successfully")
        return success_response(
            message=f"{self.singular} fetched successfully",
            data=db_user,
        )

    async def update(
        self,
        uuid: UUIDStr,
        data: AdminUpdateUserSchema,
        user: User = Depends(get_user_with_permission("can_write_users")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Updating {self.singular} with uuid: {uuid}")
        stmt = select(User).options(joinedload(User.roles)).where(User.uuid == uuid)
        db_user: User = await self.crud.get(db, statement=stmt)
        if not db_user:
            logger.error(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")

        if db_user.uuid == user.uuid:
            logger.error("User tried to update their own roles")
            return bad_request_response(
                "Why do you want to update your own roles? Let another admin do that!"
            )
        prev_user_data = db_user.to_dict()
        if data.role_uuid is not None:
            role_uuid = data.role_uuid.strip()
            role = await role_crud.get(db, uuid=role_uuid)
            if not role:
                logger.error(f"Role {role_uuid} not found")
                return bad_request_response(f"Role {role_uuid} not found!")

            if role.name == "user":
                logger.error("Cannot assign user role to a user")
                return bad_request_response("Cannot assign user role to a user")

            check_user_role = await user_roles_crud.get(
                db, user_uuid=db_user.uuid, role_uuid=role.uuid
            )

            if not check_user_role:

                check_user_role = await user_roles_crud.create(
                    db,
                    obj_in=UserRoleCreateSchema(
                        user_uuid=db_user.uuid, role_uuid=role.uuid
                    ),
                    user_uuid=user.uuid,
                )
                logger.info(f"Role {role.name} assigned to user {db_user.email}")
            roles_to_remove = [
                role.uuid
                for role in db_user.roles
                if role.name != "user" and role.uuid != check_user_role.role_uuid
            ]
            if roles_to_remove:
                await user_roles_crud.remove_multi(
                    db, user_uuid=uuid, role_uuid=roles_to_remove
                )

                await db.refresh(db_user)
                logger.info(
                    f"Removed roles {roles_to_remove} from user {db_user.email}"
                )
        try:
            del data.role_uuid
            updated_user = await self.crud.update(
                db=db, db_obj=db_user, obj_in=data, user_uuid=user.uuid
            )
        except Exception as e:
            logger.error(f"Error updating {self.singular}: {str(e)}")
            return bad_request_response(str(e))
        logger.info(f"{self.singular} with uuid {uuid} updated successfully")
        user_updated = await self.crud.get(
            db,
            statement=select(User)
            .options(joinedload(User.roles))
            .where(User.uuid == updated_user.uuid),
        )
        return success_response(
            message=f"{self.singular} updated successfully", data=user_updated
        )

    async def delete(
        self,
        uuid: UUIDStr,
        user: User = Depends(get_user_with_permission("can_delete_users")),
        db: AsyncSession = Depends(get_async_session),
    ):
        stmt = (
            select(User)
            .options(joinedload(User.roles))
            .where(and_(User.uuid == uuid, User.soft_deleted == False))
        )
        db_user: User = await self.crud.get(db, statement=stmt)

        if not db_user:
            logger.error(f"{self.singular} with uuid {uuid} not found")
            return not_found_response(f"{self.singular} not found")

        prev_data = db_user.to_dict()
        prev_data.pop("password", None)
        logger.critical(f"{self.singular} to be deleted: {db_user} by user {user.uuid}")
        if db_user.delete_protection:
            logger.error(
                f"This {self.singular} cannot be deleted! Remove the delete protection first."
            )
            return bad_request_response(
                f"This {self.singular} cannot be deleted! Remove the delete protection first."
            )

        if db_user.uuid == user.uuid:
            logger.error("User tried to delete their own account: self termination")
            return bad_request_response(
                "Why do you want to delete yourself? Let another admin do that!"
            )

        # Delete user roles
        await user_roles_crud.remove_multi(db, user_uuid=uuid)
        await db.refresh(db_user)
        await self.crud.soft_delete(
            db,
            db_obj=db_user,
            extra_fields={"is_verified": False, "verified_at": None, "password": None},
        )

        logger.critical(
            f"{self.singular} {uuid} deleted successfully by user {user.uuid}"
        )

        await activity_log_crud.create(
            db=db,
            obj_in=ActivityLogCreateSchema(
                user_uuid=user.uuid,
                entity=self.singular,
                action="delete",
                previous_data=prev_data,
                new_data={},
                description=f"{self.singular} deleted successfully",
            ),
        )
        return success_response(message=f"{self.singular} deleted successfully")

    async def remove_user_roles(
        self,
        user_uuid: UUIDStr,
        role_uuid: UUIDStr,
        user: User = Depends(get_user_with_permission("can_delete_users")),
        db: AsyncSession = Depends(get_async_session),
    ):
        role_uuid = [role.strip() for role in role_uuid.split(",")]
        stmt = (
            select(User).options(joinedload(User.roles)).where(User.uuid == user_uuid)
        )

        db_user: User = await self.crud.get(db, statement=stmt)

        if not db_user:
            logger.error(f"{self.singular} with uuid {user_uuid} not found")
            return not_found_response(f"{self.singular} not found")

        logger.critical(
            f"{self.singular} roles to be removed: {db_user} by user {user.uuid}"
        )
        for role in db_user.roles:
            if role.name != "user" and role.uuid in role_uuid:
                user_role = await user_roles_crud.get(
                    db, user_uuid=user_uuid, role_uuid=role.uuid
                )
                if user_role.user_uuid == user.uuid:
                    logger.critical(
                        f"{self.singular} role to be removed: You cannot remove your own role. Role: {role.uuid} User: {user.uuid}"
                    )
                    return bad_request_response(
                        f"You cannot remove your own role. Role: {role.uuid} User: {user.uuid}"
                    )
                await user_roles_crud.remove(db, db_obj=user_role, user_uuid=user.uuid)

        logger.critical(
            f"{self.singular} roles {role_uuid} removed successfully by user {user.uuid}"
        )
        return success_response(message="User roles removed successfully")
