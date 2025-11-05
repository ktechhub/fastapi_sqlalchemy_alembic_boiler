from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.loggers import app_logger as logger
from app.models.users import User
from app.cruds.users import user_crud
from app.utils.password_util import verify_password
from app.database.get_session import get_async_session
from app.utils.responses import not_authorized_response
from app.utils.password_util import hash_password
from app.models.roles import Role

security = HTTPBasic()


def has_role(user: User, role_name: str) -> bool:
    """Check if the user has a specific role."""
    return any(role.name.lower() == role_name.lower() for role in user.roles)


async def get_current_docs_user(
    credentials: HTTPBasicCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_session),
) -> User:
    if settings.ENV == "local":
        return User(
            email=f"developer@{settings.DOMAIN}",
            password=hash_password("developer"),
            roles=[
                Role(
                    name="developer",
                    label="Developer",
                    description="Developer role",
                )
            ],
        )
    stmt = (
        select(User)
        .options(joinedload(User.roles))
        .where(User.email == credentials.username.lower())
    )
    user: Optional[User] = await user_crud.get(
        db=db,
        statement=stmt,
    )
    if not user:
        logger.error(f"Incorrect username or password for docs: {credentials.username}")
        return not_authorized_response(
            message="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    if not verify_password(credentials.password, user.password):
        logger.error(f"Incorrect password for docs")
        return not_authorized_response(
            message="Incorrect password",
            headers={"WWW-Authenticate": "Basic"},
        )
    if not has_role(user, "developer"):
        logger.error(f"User {user.email} does not have developer role")
        return not_authorized_response(
            message="User does not have developer role",
            headers={"WWW-Authenticate": "Basic"},
        )
    logger.info(f"Authenticated developer user: {user.email}")
    return user
