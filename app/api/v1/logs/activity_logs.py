from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.responses import not_found_response
from app.deps.user import get_user_with_permission
from app.schemas.activity_logs import (
    ActivityLogResponseSchema,
    ActivityLogTotalCountListResponseSchema,
    ActivityLogFilters,
)
from app.models.activity_logs import ActivityLog
from app.cruds.activity_logs import activity_log_crud
from app.models.users import User
from app.database.get_session import get_async_session
from app.core.loggers import app_logger as logger


class ActivityLogRouter:
    def __init__(self):
        self.router = APIRouter()
        self.crud = activity_log_crud
        self.singular = "ActivityLog"
        self.plural = "ActivityLogs"
        self.response_model = ActivityLogResponseSchema
        self.response_list_model = ActivityLogTotalCountListResponseSchema

        self.router.add_api_route(
            "/",
            self.list,
            methods=["GET"],
            response_model=self.response_list_model,
            description="Get all activity logs",
            summary="Get all activity logs",
        )
        self.router.add_api_route(
            "/{id}",
            self.get,
            methods=["GET"],
            response_model=self.response_model,
            description="Get an activity log by ID",
            summary="Get an activity log by ID",
        )

    async def list(
        self,
        filters: ActivityLogFilters = Depends(),
        user: User = Depends(get_user_with_permission("can_read_logs")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(
            f"Listing {self.plural} with filters: {filters} and user: {user.uuid}"
        )

        main_filters = {}
        query_filters = []

        if filters.user_uuid:
            main_filters["user_uuid"] = filters.user_uuid

        if filters.action:
            main_filters["action"] = filters.action

        if filters.exclude_actions:
            query_filters.append(
                ActivityLog.action.not_in(filters.exclude_actions.split(","))
            )

        if filters.include_actions:
            main_filters["action"] = filters.include_actions.split(",")
            query_filters.append(
                ActivityLog.action.in_(filters.include_actions.split(","))
            )

        if filters.entity:
            main_filters["entity"] = filters.entity

        if filters.start_date:
            main_filters["created_at"] = {"gte": filters.start_date}

        if filters.end_date:
            main_filters["created_at"] = {"lte": filters.end_date}

        if filters.search:
            main_filters["search"] = filters.search

        activity_logs = await self.crud.get_multi(
            db=db,
            skip=filters.skip,
            limit=filters.limit,
            sort=filters.sort,
            eager_load=[ActivityLog.user],
            query_filters=query_filters,
            **main_filters,
        )

        return {
            "status": status.HTTP_200_OK,
            "detail": f"Successfully fetched {self.plural}!",
            "total_count": activity_logs["total_count"],
            "data": activity_logs["data"],
        }

    async def get(
        self,
        id: int,
        user: User = Depends(get_user_with_permission("can_read_logs")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"Getting {self.singular} with ID: {id} and user: {user.uuid}")

        activity_log = await self.crud.get(db=db, id=id)

        if not activity_log:
            return not_found_response(f"{self.singular} not found!")

        return {
            "status": status.HTTP_200_OK,
            "detail": f"Successfully fetched {self.singular}!",
            "data": activity_log,
        }
