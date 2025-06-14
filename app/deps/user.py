from typing import Callable
from datetime import datetime
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt
from pydantic import ValidationError

from ..core.config import settings
from ..schemas.tokens import TokenPayloadSchema
from ..database.database import get_async_session
from ..cruds.users import user_crud
from ..cruds.user_roles import user_roles_crud
from ..cruds.role_permissions import role_permission_crud
from ..cruds.permissions import permission_crud
from ..models.users import User
from ..models.user_roles import UserRole
from ..models.role_permissions import RolePermission
from ..utils.responses import not_authorized_response, forbidden_response

reuseable_oauth = OAuth2PasswordBearer(
    tokenUrl=(
        "/api/v1/login"
        if settings.SERVICE_NAME == "auth"
        else "https://dev.ktechhub.com/api/v1/login/"
    ),
    scheme_name="JWT",
)


async def get_current_user(
    token: str = Depends(reuseable_oauth), session: Session = Depends(get_async_session)
):
    try:
        # Decode JWT
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayloadSchema(**payload)

        # Check if token is expired
        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            return forbidden_response("Token expired")
    except (jwt.JWTError, ValidationError):
        return not_authorized_response("Could not validate credentials")

    # Retrieve user from database
    user = await user_crud.get(db=session, uuid=token_data.sub, eager_load=[User.roles])
    if user is None:
        return not_authorized_response("Could not validate credentials")

    # if not user.email.endswith("@ktechhub.com"):
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Hey my friend, you are not allowed here... :) Contact support team support@ktechhub.com",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )

    return user


def get_user_with_role(required_role: str) -> Callable:
    async def role_dependency(
        user=Depends(get_current_user),
        session: Session = Depends(get_async_session),
    ):
        role_names = required_role.split(",")

        # data = user.to_schema_dict()
        # Check if the user has the required role
        for role in user.roles:
            if role.name in role_names:
                return user

        return not_authorized_response(
            f"{required_role.capitalize()} privileges required"
        )

    return role_dependency


def get_user_with_permission(required_permission: str) -> Callable:
    async def permission_dependency(
        user=Depends(get_current_user),
        session: Session = Depends(get_async_session),
    ):
        permission_names = required_permission.split(",")
        # Retrieve the user's roles
        user_roles = await user_roles_crud.get_multi(
            db=session, limit=-1, user_uuid=user.uuid, eager_load=[UserRole.role]
        )

        role_permissions = await role_permission_crud.get_multi(
            db=session,
            limit=-1,
            role_uuid=[role.uuid for role in user_roles["data"]],
            eager_load=[RolePermission.permission],
        )
        # Check if the user has the required role
        for user_permission in role_permissions["data"]:
            if user_permission.permission.name in permission_names:
                return user

        return not_authorized_response(
            f"{required_permission.capitalize()} permissions required"
        )

    return permission_dependency
