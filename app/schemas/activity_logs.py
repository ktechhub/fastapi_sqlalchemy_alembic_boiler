from datetime import datetime, date
from typing import Literal, Optional, List, Union, Dict, Any
from pydantic import (
    BaseModel,
    Field,
    model_validator,
    EmailStr,
    field_validator,
    ConfigDict,
)
from .base_schema import (
    BaseSchema,
    BaseUUIDSchema,
    BaseResponseSchema,
    BaseTotalCountResponseSchema,
)
from .base_filters import BaseFilters
from fastapi import HTTPException, status
from ..utils.responses import bad_request_response


ActionType = Literal[
    "create",
    "update",
    "delete",
    "login",
    "logout",
    "create_password",
    "reset_password",
    "change_password",
    "confirm_email",
    "verify_email",
]
action_choices = [
    "create",
    "update",
    "delete",
    "login",
    "logout",
    "create_password",
    "reset_password",
    "change_password",
    "confirm_email",
    "verify_email",
]


class ActivityLogBaseSchema(BaseModel):
    """Base schema for activity logs"""

    user_uuid: Optional[str] = Field(
        None, description="UUID reference to the user who performed the action"
    )
    entity: str = Field(..., description="The entity that was affected by the action")
    previous_data: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        None, description="The data before the action was performed"
    )
    new_data: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        None, description="The data after the action was performed"
    )
    action: ActionType = Field(..., description="The type of action performed")
    delete_protection: Optional[bool] = Field(
        True, description="Whether the log entry is protected from deletion"
    )
    description: Optional[str] = Field(
        None, description="A description of the action performed"
    )

    @model_validator(mode="before")
    def convert_datetime_to_isoformat(cls, values):
        """Convert datetime objects to ISO format strings for JSON serialization"""
        if isinstance(values, dict):
            for key, value in values.items():
                if isinstance(value, (datetime, date)):
                    values[key] = value.isoformat()
                elif isinstance(value, dict):
                    values[key] = cls.convert_datetime_to_isoformat(value)
                elif isinstance(value, list):
                    values[key] = [
                        (
                            cls.convert_datetime_to_isoformat(item)
                            if isinstance(item, (dict, datetime))
                            else item
                        )
                        for item in value
                    ]
        return values


class ActivityLogCreateSchema(ActivityLogBaseSchema):
    """Schema for creating activity logs"""

    pass


class UserSchema(BaseSchema, BaseUUIDSchema):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_verified: Optional[bool] = None
    verified_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    status: Optional[str] = None


class ActivityLogSchema(ActivityLogBaseSchema, BaseSchema):
    user: Optional[UserSchema] = None


class ActivityLogResponseSchema(BaseResponseSchema):
    """Schema for single activity log response"""

    data: Optional[ActivityLogSchema] = None


class ActivityLogListResponseSchema(BaseResponseSchema):
    """Schema for list of activity logs response"""

    data: Optional[List[ActivityLogSchema]] = None


class ActivityLogTotalCountListResponseSchema(BaseTotalCountResponseSchema):
    """Schema for list of activity logs with total count response"""

    data: Optional[List[ActivityLogSchema]] = None


class ActivityLogFilters(BaseFilters):
    """Filters for activity logs"""

    model_config = ConfigDict(extra="forbid")

    user_uuid: Optional[str] = Field(
        None, description="Filter by the UUID of the user who performed the action"
    )
    entity: Optional[str] = Field(None, description="Filter by the affected entity")
    action: Optional[ActionType] = Field(
        None, description="Filter by the type of action performed"
    )
    exclude_actions: Optional[str] = Field(
        None,
        description="Exclude the type of action performed separated by comma",
    )
    include_actions: Optional[str] = Field(
        None,
        description="Include the type of action performed separated by comma",
    )
    start_date: Optional[datetime] = Field(
        None, description="Filter by the start date of the activity"
    )
    end_date: Optional[datetime] = Field(
        None, description="Filter by the end date of the activity"
    )
    search: Optional[str] = Field(
        None, description="Search by entity, action, or user details"
    )

    @model_validator(mode="after")
    def validate_action_filters(cls, values):
        exclude_actions = values.exclude_actions
        include_actions = values.include_actions

        if exclude_actions and include_actions:
            return bad_request_response(
                "Cannot use exclude_actions and include_actions together"
            )
        return values

    @field_validator("exclude_actions", "include_actions")
    def validate_actions(cls, value):
        if not value:
            return None

        check_values = [v.strip() for v in value.split(",")]
        if check_values:
            for v in check_values:
                if v not in action_choices:
                    return bad_request_response(
                        f"Invalid action: {v}. Allowed actions are: {action_choices}"
                    )
        return value
