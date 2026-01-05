from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, UploadFile, status, Header
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from app.deps.user import get_current_user, reuseable_oauth
from app.models.users import User
from app.models.roles import Role
from app.models.role_permissions import RolePermission
from app.core.config import settings
from app.utils.password_util import verify_password, hash_password
from app.utils.responses import bad_request_response, success_response
from app.utils.security_util import (
    create_access_token_from_refresh_token,
    invalidate_user_tokens,
    is_token_valid,
    decode_access_token,
    decode_refresh_token,
)
from app.utils.encryption_util import hash_token
from app.cruds.users import user_crud
from app.cruds.activity_logs import activity_log_crud
from app.schemas.users import (
    UserResponseSchema,
    UserUpdateNewPasswordSchema,
    UserUpdateWithPasswordSchema,
    UserUpdateProfileSchema,
    UserUpdateSchema,
)
from app.schemas.activity_logs import ActivityLogCreateSchema
from app.utils.object_storage import save_file_to_s3
from app.database.get_session import get_async_session
from app.core.constants import ALLOWED_IMAGE_EXTENSIONS
from app.core.loggers import app_logger as logger
from app.services.redis_base import client as redis_client


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
        self.router.add_api_route(
            "/refresh-token/",
            self.generate_refresh_token,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Generate access token from refresh token",
            response_model=dict,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/logout/",
            self.logout,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Logout the current user",
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
            select(User)
            .options(
                joinedload(User.roles)
                .joinedload(Role.role_permissions)
                .joinedload(RolePermission.permission),
                joinedload(User.country),
            )
            .where(User.uuid == user.uuid)
        )

        data = await self.crud.get(db, statement=stmt)
        logger.info(f"User details fetched successfully for {user.email}")
        return success_response("User details fetched successfully.", data=data)

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
        db_user: User = await self.crud.get(
            db=session, uuid=user.uuid, include_relations="roles"
        )

        if not verify_password(data.old_password, db_user.password):
            logger.warning(f"Old password is incorrect for user {db_user.email}")
            return bad_request_response("Old password is incorrect.")
        try:
            await self.crud.update(
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
        logger.info(f"Password updated successfully for user {user.email}")
        return success_response("Password updated successfully.")

    async def update_profile(
        self,
        data: UserUpdateProfileSchema,
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(get_current_user),
    ):
        """
        Update user's profile.
        """
        db_user: User = await self.crud.get(
            session, uuid=user.uuid, include_relations="roles"
        )

        if not db_user:
            logger.error(f"User {user.email} not found")
            return bad_request_response("User not found.")

        try:
            await self.crud.update(
                db=session,
                db_obj=db_user,
                obj_in=data,
                user_uuid=user.uuid,
            )
            logger.info(f"Profile updated successfully for user {user.email}")
        except Exception as e:
            logger.error(f"Error updating profile for user {user.email}: {e}")
            return bad_request_response("Error updating profile.")

        return success_response("Profile updated successfully.")

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
            access_type="private",
        )
        logger.info(
            f"Avatar URL {avatar_url} generated successfully for user {user.email}"
        )
        db_user: User = await self.crud.get(
            session, uuid=user.uuid, include_relations="roles"
        )

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

    async def generate_refresh_token(self, refresh_token: str = Header(...)):
        """Generate access token from refresh token."""
        logger.info("Generating access token from refresh token")

        try:
            # Decode refresh token (validates expiration, nbf, issuer, audience)
            payload = decode_refresh_token(refresh_token)
            user_uuid = payload.get("sub")

            # Check if token was revoked (pass payload to avoid double decode)
            if not is_token_valid(
                refresh_token, user_uuid, token_type="refresh", payload=payload
            ):
                logger.warning(
                    f"Attempted to use revoked refresh token for user {user_uuid}"
                )
                return bad_request_response("Refresh token has been revoked")

            access_token, _ = create_access_token_from_refresh_token(refresh_token)
        except jwt.ExpiredSignatureError:
            return bad_request_response("Refresh token expired")
        except Exception as e:
            logger.error(f"Error generating access token: {e}")
            return bad_request_response("Invalid refresh token")

        return success_response(
            "Access token generated successfully", data={"access_token": access_token}
        )

    async def logout(
        self,
        token: str = Depends(reuseable_oauth),
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
    ):
        """
        Logout the current user.
        Invalidates ALL tokens (access and refresh) by setting a logout timestamp.
        Closes the current user session.
        Memory-efficient: only one Redis entry per user.
        """
        logger.info(f"Logging out user {user.email}")

        try:
            # Get token jti to find and close session
            payload = decode_access_token(token)
            token_jti = payload.get("jti")

            # Close session if found
            if token_jti:
                from app.services.session_service import (
                    get_session_by_jti,
                    close_user_session,
                )

                user_session = await get_session_by_jti(session, token_jti)
                if user_session:
                    await close_user_session(session, str(user_session.uuid))

            invalidate_user_tokens(str(user.uuid))
            # Cleanup cache using hashed token key
            token_hash = hash_token(token)
            redis_client.delete(f"token:{token_hash}")

            # Get user data for activity log (if needed)
            db_user = await self.crud.get(
                db=session, uuid=user.uuid, include_relations="roles"
            )

            await activity_log_crud.create(
                db=session,
                obj_in=ActivityLogCreateSchema(
                    user_uuid=user.uuid,
                    entity=self.singular,
                    action="logout",
                    previous_data=db_user.to_dict() if db_user else {},
                    new_data={},
                    description="Logged out successfully. All tokens invalidated.",
                ),
            )

            logger.info(f"User {user.email} logged out successfully")
            return success_response(
                "Logged out successfully. All tokens have been revoked."
            )
        except Exception as e:
            logger.error(f"Error during logout for user {user.email}: {e}")
            return success_response("Logged out successfully.")
