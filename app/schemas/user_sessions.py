from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from .base_schema import (
    BaseUUIDSchema,
    BaseResponseSchema,
    BaseTotalCountResponseSchema,
)
from .base_filters import BaseFilters


class UserSessionBaseSchema(BaseModel):
    """Base schema for user sessions"""

    user_uuid: str = Field(..., description="UUID of the user")
    token_jti: str = Field(..., description="JWT ID (jti) of the token")
    ip_address: str = Field(..., description="IP address of the session")
    user_agent: Optional[str] = Field(None, description="Raw user agent string")
    browser: Optional[str] = Field(None, description="Browser name")
    browser_version: Optional[str] = Field(None, description="Browser version")
    os: Optional[str] = Field(None, description="Operating system")
    os_version: Optional[str] = Field(None, description="Operating system version")
    device_type: Optional[str] = Field(
        None, description="Device type (Desktop, Mobile, Tablet)"
    )
    location_city: Optional[str] = Field(None, description="City location")
    location_region: Optional[str] = Field(None, description="Region/State location")
    location_country: Optional[str] = Field(None, description="Country code (e.g., DE)")
    location_country_name: Optional[str] = Field(
        None, description="Country name (e.g., Germany)"
    )
    is_active: bool = Field(True, description="Whether the session is active")
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")
    closed_at: Optional[datetime] = Field(None, description="Session closed timestamp")


class UserSessionCreateSchema(UserSessionBaseSchema):
    """Schema for creating user sessions"""

    pass


class UserSessionUpdateSchema(BaseModel):
    """Schema for updating user sessions"""

    is_active: Optional[bool] = Field(None, description="Whether the session is active")
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")
    closed_at: Optional[datetime] = Field(None, description="Session closed timestamp")
    location_city: Optional[str] = Field(None, description="City location")
    location_region: Optional[str] = Field(None, description="Region/State location")
    location_country: Optional[str] = Field(None, description="Country code")
    location_country_name: Optional[str] = Field(None, description="Country name")


class UserSessionSchema(UserSessionBaseSchema, BaseUUIDSchema):
    """Schema for user session response"""

    pass


class UserSessionResponseSchema(BaseResponseSchema):
    """Schema for single user session response"""

    data: Optional[UserSessionSchema] = None


class UserSessionListResponseSchema(BaseTotalCountResponseSchema):
    """Schema for list of user sessions response"""

    data: Optional[list[UserSessionSchema]] = None


class UserSessionFilters(BaseFilters):
    """Filters for user sessions"""

    is_active: Optional[bool] = Field(None, description="Filter by active status")
    token_jti: Optional[str] = Field(None, description="Filter by token JTI")
