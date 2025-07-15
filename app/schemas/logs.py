from typing import List, Optional, Union, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from .base_schema import (
    BaseResponseSchema,
    BaseTotalCountResponseSchema,
)
from .base_filters import BaseFilters


class LogBaseSchema(BaseModel):
    id: Optional[str] = Field(None, description="The id of the log")
    timestamp: Optional[int] = Field(None, description="The timestamp of the log")
    timestamp_readable: Optional[str] = Field(
        None, description="Human-readable timestamp"
    )
    level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = Field(
        None, description="The level of the log"
    )
    message: Optional[Union[str, dict, list, Any]] = Field(
        None, description="The message of the log"
    )
    service: Optional[
        Literal[
            "auth",
            "logs",
            "analytics",
            "messaging_layer",
            "ktechhub",
        ]
    ] = Field(None, description="The service that generated the log")
    logger_name: Optional[
        Literal[
            "app_logger",
            "db_logger",
            "security_logger",
            "scheduler_logger",
            "redis_logger",
        ]
    ] = Field(None, description="The name of the logger")

    @model_validator(mode="before")
    def add_human_readable_timestamp(cls, values):
        ts = values.get("timestamp")
        if ts:
            values["timestamp_readable"] = datetime.utcfromtimestamp(ts).isoformat()
        return values


class LogSchema(LogBaseSchema):
    pass


class LogResponseSchema(BaseResponseSchema):
    data: Optional[LogSchema] = None


class LogListResponseSchema(BaseResponseSchema):
    data: Optional[List[LogSchema]] = None


class LogTotalCountListResponseSchema(BaseTotalCountResponseSchema):
    data: Optional[List[LogSchema]] = None


class LogFilters(BaseFilters):
    sort: Optional[str] = Field(
        "timestamp:desc",
        description="Sorting criteria for the result set in the format 'field:direction' (e.g., 'timestamp:desc' or 'timestamp:asc')",
        example="timestamp:desc",
    )
    id: Optional[str] = Field(None, description="Filter by the id of the log")
    message: Optional[str] = Field(None, description="Filter by the message of the log")
    level: Optional[str] = Field(None, description="Filter by the level of the log")
    timestamp: Optional[int] = Field(
        None, description="Filter by the timestamp of the log"
    )
    start_date: Optional[datetime] = Field(
        None, description="Filter by the start date of the log"
    )
    end_date: Optional[datetime] = Field(
        None, description="Filter by the end date of the log"
    )
    service: Optional[str] = Field(None, description="Filter by the service of the log")
    logger_name: Optional[str] = Field(
        None, description="Filter by the logger name of the log"
    )
    search: Optional[str] = Field(
        None,
        description="Search by the message, level, service, or logger name of the log",
    )
