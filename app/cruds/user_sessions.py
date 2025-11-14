from sqlalchemy.ext.asyncio import AsyncSession
from .base import CRUDBase
from ..models.user_sessions import UserSession
from ..schemas.user_sessions import (
    UserSessionCreateSchema,
    UserSessionUpdateSchema,
)
from ..core.loggers import db_logger as logger


class CRUDUserSession(
    CRUDBase[UserSession, UserSessionCreateSchema, UserSessionUpdateSchema]
):
    pass


user_session_crud = CRUDUserSession(UserSession)
