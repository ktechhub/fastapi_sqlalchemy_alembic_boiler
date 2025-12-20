from fastapi import APIRouter, Depends, HTTPException, status
from meilisearch.errors import MeilisearchApiError
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.responses import (
    success_response,
    not_found_response,
    bad_request_response,
)
from app.deps.user import get_user_with_permission
from app.schemas.logs import (
    LogSchema,
    LogResponseSchema,
    LogTotalCountListResponseSchema,
    LogFilters,
)
from app.services.meili_search import MeiliSearchService
from app.services.logs_service import LogService
from app.models.users import User
from app.database.get_session import get_async_session
from app.core.loggers import app_logger as logger
from app.core.config import settings


class SystemLogRouter:
    def __init__(self):
        self.router = APIRouter()
        self.singular = "Log"
        self.plural = "Logs"
        self.response_model = LogResponseSchema
        self.response_list_model = LogTotalCountListResponseSchema

        # Use MeiliSearch if configured, otherwise fallback to LogService
        if settings.MEILI_SEARCH_URL and settings.MEILI_SEARCH_API_KEY:
            try:
                self.logs_service = MeiliSearchService(index_name="logs")
                self.use_meilisearch = True
            except Exception:
                logger.warning(
                    "MeiliSearch initialization failed, falling back to LogService"
                )
                self.logs_service = LogService()
                self.use_meilisearch = False
        else:
            logger.info("MeiliSearch not configured, using LogService")
            self.logs_service = LogService()
            self.use_meilisearch = False

        self.router.add_api_route(
            "/",
            self.list,
            methods=["GET"],
            response_model=self.response_list_model,
            description="Get all logs",
            summary="Get all logs",
        )
        self.router.add_api_route(
            "/{id}",
            self.get,
            methods=["GET"],
            response_model=self.response_model,
            description="Get a log by ID",
            summary="Get a log by ID",
        )
        self.router.add_api_route(
            "/{id}",
            self.delete,
            methods=["DELETE"],
            response_model=self.response_model,
            description="Delete a log by ID",
            summary="Delete a log by ID",
        )

    async def list(
        self,
        filters: LogFilters = Depends(),
        user: User = Depends(get_user_with_permission("can_read_logs")),
        db: AsyncSession = Depends(get_async_session),
    ):
        try:
            conditions = []
            sort_param = []

            if filters.sort:
                try:
                    sort = filters.sort.split(",")
                    for s in sort:
                        field, direction = s.split(":")
                        if direction not in ["asc", "desc"]:
                            raise ValueError("Invalid sort direction")
                        sort_param.append(f"{field}:{direction}")
                except ValueError:
                    return bad_request_response(
                        message="Invalid sort format. Use 'field:asc' or 'field:desc'."
                    )

            # Date range filters
            if filters.start_date:
                conditions.append(f"timestamp >= {int(filters.start_date.timestamp())}")
            if filters.end_date:
                conditions.append(f"timestamp <= {int(filters.end_date.timestamp())}")

            # Exact match filters
            if filters.message:
                conditions.append(f"message = '{filters.message}'")
            if filters.level:
                conditions.append(f"level = '{filters.level}'")
            if filters.service:
                conditions.append(f"service = '{filters.service}'")
            if filters.logger_name:
                conditions.append(f"logger_name = '{filters.logger_name}'")

            if filters.id:
                id_list = filters.id.split(",")
                # Format for MeiliSearch: id IN ['id1', 'id2']
                # Format for LogService: id IN ['id1', 'id2']
                id_list_str = ", ".join([f"'{id.strip()}'" for id in id_list])
                conditions.append(f"id IN [{id_list_str}]")

            # Combine all filters
            main_filters = " AND ".join(conditions) if conditions else None
            if main_filters:
                logger.info(f"Main log filters: {main_filters}")
            result = self.logs_service.search(
                query=filters.search or "",
                offset=filters.skip,
                limit=filters.limit,
                filters=main_filters,
                sort=sort_param,
            )
            logger.info(f"Logs fetched successfully by user {user.uuid}")
            return {
                "status": status.HTTP_200_OK,
                "detail": f"{self.plural} fetched successfully",
                "total_count": result["estimatedTotalHits"],
                "data": result["hits"],
            }
        except MeilisearchApiError as e:
            logger.error(f"Error fetching logs from MeiliSearch: {e}")
            return bad_request_response(message="Error fetching logs")
        except Exception as e:
            logger.error(f"Error fetching logs: {e}")
            return bad_request_response(message="Error fetching logs")

    async def get(
        self,
        id: str,
        user: User = Depends(get_user_with_permission("can_read_logs")),
        db: AsyncSession = Depends(get_async_session),
    ):
        logger.info(f"User {user.uuid} is fetching log with ID {id}")
        try:
            log = self.logs_service.get_one(id)
            if not log:
                return not_found_response(
                    message=f"{self.singular} with ID {id} not found"
                )
            logger.info(f"Log {id} fetched successfully by user {user.uuid}")
            # Handle both dict (LogService) and object (MeiliSearch) responses
            log_data = log if isinstance(log, dict) else log.__dict__
            return success_response(
                data=log_data, message=f"{self.singular} fetched successfully"
            )
        except MeilisearchApiError as e:
            logger.error(f"Error fetching log from MeiliSearch: {e}")
            return bad_request_response(message="Error fetching log")
        except Exception as e:
            logger.error(f"Error fetching log: {e}")
            return bad_request_response(message="Error fetching log")

    async def delete(
        self,
        id: str,
        user: User = Depends(get_user_with_permission("can_delete_logs")),
        db: AsyncSession = Depends(get_async_session),
    ):
        try:
            log = self.logs_service.get_one(id)

            if not log:
                return not_found_response(
                    detail=f"{self.singular} with ID {id} not found"
                )

            # Handle both dict (LogService) and object (MeiliSearch) responses
            log_data = log if isinstance(log, dict) else log.__dict__
            logger.critical(f"Log to be deleted: {log_data} by user {user.uuid}")
            self.logs_service.delete_one(id)

            logger.critical(f"Log {id} deleted successfully by user {user.uuid}")

            return success_response(
                data=log_data, message=f"{self.singular} deleted successfully"
            )
        except MeilisearchApiError as e:
            logger.error(f"Error deleting log from MeiliSearch: {e}")
            return bad_request_response(message="Error deleting log")
        except Exception as e:
            logger.error(f"Error deleting log: {e}")
            return bad_request_response(message="Error deleting log")
