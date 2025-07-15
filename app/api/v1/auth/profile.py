from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.user import get_current_user
from app.models.users import User
from app.utils.password_util import verify_password, hash_password
from app.utils.responses import bad_request_response, success_response
from app.cruds.users import user_crud
from app.schemas.users import (
    UserResponseSchema,
    UserUpdateNewPasswordSchema,
    UserUpdateWithPasswordSchema,
    userUpdateProfileSchema,
    UserUpdateSchema,
)
from app.utils.object_storage import save_file_to_s3
from app.database.get_session import get_async_session
from app.core.constants import ALLOWED_IMAGE_EXTENSIONS
from app.core.loggers import app_logger as logger
from app.cruds.activity_logs import activity_log_crud
from app.schemas.activity_logs import ActivityLogCreateSchema


class UserProfileRouter:
    def __init__(self):
        self.router = APIRouter()
        self.singular = "User"
        self.plural = "Users"
        self.crud = user_crud
        self.response_model = UserResponseSchema
        self.router.add_api_route(
            "/me/",
            self.get_me,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            summary=f"Get details of currently logged in user",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/update-password/",
            self.update_password,
            methods=["PUT"],
            status_code=status.HTTP_200_OK,
            summary=f"Update a current user's password",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/update-profile/",
            self.update_profile,
            methods=["PUT"],
            status_code=status.HTTP_200_OK,
            summary=f"Update a current user's profile",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/change-avatar/",
            self.change_avatar,
            methods=["PUT"],
            status_code=status.HTTP_200_OK,
            summary=f"Update a current user's avatar",
            response_model=dict,
            response_model_exclude_unset=True,
        )

    async def get_me(
        self,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Fetching user details for the current user {user.email}")
        stmt = (
            select(User).options(joinedload(User.roles)).where(User.uuid == user.uuid)
        )

        data = await self.crud.get(db, statement=stmt)
        logger.info(f"User details fetched successfully for {user.email}")
        return {
            "status": status.HTTP_200_OK,
            "detail": "success",
            "data": data.to_dict(),
        }

    async def update_password(
        self,
        data: UserUpdateNewPasswordSchema,
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(get_current_user),
    ):
        """
        Update user's password.
        """
        logger.info(f"Updating password for user {user.email}")
        stmt = (
            select(User).options(joinedload(User.roles)).where(User.uuid == user.uuid)
        )
        db_user: User = await self.crud.get(db=session, statement=stmt)

        if not verify_password(data.old_password, db_user.password):
            logger.warning(f"Old password is incorrect for user {db_user.email}")
            return bad_request_response("Old password is incorrect.")
        try:
            updated_user = await self.crud.update(
                db=session,
                db_obj=db_user,
                obj_in=UserUpdateWithPasswordSchema(
                    password=hash_password(data.new_password)
                ),
                user_uuid=user.uuid,
            )

        except Exception as e:
            logger.error(f"Error updating user password: {str(e)}")
            return bad_request_response(f"Error updating user password: {str(e)}")
        logger.info(f"Password updated successfully for user {updated_user.email}")
        return success_response("Password updated successfully.", db_user.to_dict())

    async def update_profile(
        self,
        data: userUpdateProfileSchema,
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(get_current_user),
    ):
        """
        Update user's profile.
        """
        stmt = (
            select(User).options(joinedload(User.roles)).where(User.uuid == user.uuid)
        )

        db_user: User = await self.crud.get(session, statement=stmt)

        if not db_user:
            logger.error(f"User {user.email} not found")
            return bad_request_response("User not found.")

        try:
            updated_user = await self.crud.update(
                db=session,
                db_obj=db_user,
                obj_in=data,
                user_uuid=user.uuid,
            )
            logger.info(f"Profile updated successfully for user {user.email}")
        except Exception as e:
            logger.error(f"Error updating profile for user {user.email}: {e}")
            return bad_request_response("Error updating profile.")

        return {
            "status": status.HTTP_200_OK,
            "detail": "Profile updated successfully.",
            "data": updated_user.to_dict(),
        }

    async def change_avatar(
        self,
        avatar: UploadFile = File(
            ...,
            description=f"User avatar file, we accept image files only. We accept {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
        ),
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(get_current_user),
    ):
        """
        Update user's profile.
        """
        logger.info(f"Updating avatar for user {user.email}")
        avatar_extension = avatar.filename.split(".")[-1]
        if avatar_extension not in ALLOWED_IMAGE_EXTENSIONS:
            logger.warning(
                f"File extension {avatar_extension} is not allowed for user {user.email}"
            )
            return bad_request_response(
                f"File extension {avatar_extension} is not allowed. We only accept {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )

        avatar_url = await save_file_to_s3(
            file_object=avatar,
            extension=f".{str(avatar_extension)}",
            folder="users/avatars",
            access_type="public",
        )
        logger.info(
            f"Avatar URL {avatar_url} generated successfully for user {user.email}"
        )
        stmt = (
            select(User).options(joinedload(User.roles)).where(User.uuid == user.uuid)
        )
        db_user: User = await self.crud.get(session, statement=stmt)

        await self.crud.update(
            db=session,
            db_obj=db_user,
            obj_in=UserUpdateSchema(avatar=avatar_url),
            user_uuid=user.uuid,
        )
        logger.info(f"Avatar updated successfully for user {user.email}")
        return success_response(
            "Avatar updated successfully.", data={"avatar": avatar_url}
        )
