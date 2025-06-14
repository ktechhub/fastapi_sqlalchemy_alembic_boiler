from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps.user import get_current_user
from app.models.permissions import Permission
from app.models.role_permissions import RolePermission
from app.models.roles import Role
from app.models.users import User
from app.utils.password_util import verify_password, hash_password
from app.utils.responses import (
    bad_request_response,
    conflict_response,
    not_found_response,
    success_response,
)
from app.cruds.users import user_crud
from app.schemas.users import (
    UserPermissionSchema,
    UserResponseSchema,
    UserUpdatePasswordSchema,
    UserUpdateNewPasswordSchema,
    userUpdateProfileSchema,
    UserUpdateSchema,
    UserMeResponseSchema,
)
from app.utils.object_storage import save_file_to_s3
from app.database.database import get_async_session
from app.core.constants import ALLOWED_IMAGE_EXTENSIONS


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
            response_model=UserMeResponseSchema,
        )
        self.router.add_api_route(
            "/update-password/",
            self.update_password,
            methods=["PUT"],
            status_code=status.HTTP_200_OK,
            summary=f"Update a current user's password",
            response_model=self.response_model,
        )
        self.router.add_api_route(
            "/update-profile/",
            self.update_profile,
            methods=["PUT"],
            status_code=status.HTTP_200_OK,
            summary=f"Update a current user's profile",
            response_model=self.response_model,
        )
        self.router.add_api_route(
            "/change-avatar/",
            self.change_avatar,
            methods=["PUT"],
            status_code=status.HTTP_200_OK,
            summary=f"Update a current user's avatar",
            response_model=self.response_model,
        )

    async def get_me(
        self,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session),
    ):
        permissions = await self.get_user_permissions(user, db)
        return {
            "status": status.HTTP_200_OK,
            "detail": "success",
            "data": {**user.to_schema_dict(), "permissions": permissions},
        }

    async def get_user_permissions(self, user: User, db: AsyncSession):
        """Fetch permissions for all roles associated with the user."""
        query = (
            select(Permission)
            .join(RolePermission, RolePermission.permission_uuid == Permission.uuid)
            .join(Role, Role.uuid == RolePermission.role_uuid)
            .join(User, User.roles.any(Role.uuid == Role.uuid))
            .where(User.uuid == user.uuid)
            .distinct(Permission.uuid)
        )
        result = await db.execute(query)
        permissions = result.scalars().all()
        return permissions

    async def update_password(
        self,
        data: UserUpdateNewPasswordSchema,
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(get_current_user),
    ):
        """
        Update user's password.
        """
        if not verify_password(data.old_password, user.password):
            return bad_request_response("Old password is incorrect.")

        updated_user = await self.crud.update(
            db=session,
            db_obj=user,
            obj_in=UserUpdatePasswordSchema(password=hash_password(data.new_password)),
        )
        return success_response("Password updated successfully.", updated_user)

    async def update_profile(
        self,
        data: userUpdateProfileSchema,
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(get_current_user),
    ):
        """
        Update user's profile.
        """
        updated_user = await self.crud.update(
            db=session,
            db_obj=user,
            obj_in=data,
        )
        return success_response("Profile updated successfully.", updated_user)

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
        avatar_extension = avatar.filename.split(".")[-1]
        if avatar_extension not in ALLOWED_IMAGE_EXTENSIONS:
            return bad_request_response(
                f"File extension {avatar_extension} is not allowed. We only accept {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )

        avatar_url = await save_file_to_s3(
            file_object=avatar,
            extension=f".{str(avatar_extension)}",
            folder="users/avatars",
            access_type="public",
        )

        updated_user = await self.crud.update(
            db=session,
            db_obj=user,
            obj_in=UserUpdateSchema(avatar=avatar_url),
        )
        return success_response("Avatar updated successfully.", updated_user)
