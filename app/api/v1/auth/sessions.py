from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.responses import not_found_response, success_response
from app.deps.user import get_current_user
from app.schemas.user_sessions import (
    UserSessionResponseSchema,
    UserSessionListResponseSchema,
    UserSessionFilters,
)
from app.models.user_sessions import UserSession
from app.models.users import User
from app.cruds.user_sessions import user_session_crud
from app.database.get_session import get_async_session
from app.core.loggers import app_logger as logger
from app.services.session_service import close_user_session


class UserSessionRouter:
    def __init__(self):
        self.router = APIRouter()
        self.crud = user_session_crud
        self.singular = "UserSession"
        self.plural = "UserSessions"
        self.response_model = UserSessionResponseSchema
        self.response_list_model = UserSessionListResponseSchema

        self.router.add_api_route(
            "/",
            self.list,
            methods=["GET"],
            response_model=self.response_list_model,
            description="Get all user sessions",
            summary="Get all user sessions",
        )
        self.router.add_api_route(
            "/{uuid}",
            self.get,
            methods=["GET"],
            response_model=self.response_model,
            description="Get a user session by UUID",
            summary="Get a user session by UUID",
        )
        self.router.add_api_route(
            "/{uuid}",
            self.revoke,
            methods=["DELETE"],
            response_model=self.response_model,
            description="Revoke a user session",
            summary="Revoke a user session",
        )

    async def list(
        self,
        filters: UserSessionFilters = Depends(),
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session),
    ):
        """List all sessions for the current user."""
        logger.info(f"Listing {self.plural} for user {user.uuid}")

        sessions = await self.crud.get_multi(
            db=db,
            user_uuid=user.uuid,
            **filters.model_dump(),
        )

        return {
            "status": status.HTTP_200_OK,
            "detail": f"Successfully fetched {self.plural}!",
            "total_count": sessions["total_count"],
            "data": sessions["data"],
        }

    async def get(
        self,
        uuid: str,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session),
    ):
        """Get a specific session by UUID (only if it belongs to current user)."""
        logger.info(f"Getting {self.singular} with UUID: {uuid} for user {user.uuid}")

        session = await self.crud.get(db=db, uuid=uuid)

        if not session:
            return not_found_response(f"{self.singular} not found!")

        # Ensure user can only access their own sessions
        if session.user_uuid != user.uuid:
            return not_found_response(f"{self.singular} not found!")

        return {
            "status": status.HTTP_200_OK,
            "detail": f"Successfully fetched {self.singular}!",
            "data": session,
        }

    async def revoke(
        self,
        uuid: str,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session),
    ):
        """Revoke a specific session (only if it belongs to current user)."""
        logger.info(f"Revoking {self.singular} with UUID: {uuid} for user {user.uuid}")

        session = await self.crud.get(db=db, uuid=uuid)

        if not session:
            return not_found_response(f"{self.singular} not found!")

        # Ensure user can only revoke their own sessions
        if session.user_uuid != user.uuid:
            return not_found_response(f"{self.singular} not found!")

        # Close the session
        await close_user_session(db, uuid)

        logger.info(f"Session {uuid} revoked successfully")
        return success_response(f"{self.singular} revoked successfully!")


user_session_router = UserSessionRouter()
