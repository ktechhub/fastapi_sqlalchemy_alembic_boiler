from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.base_filters import BaseFilters
from app.schemas.base_schema import (
    BaseResponseSchema,
    BaseSlugSchema,
    BaseTotalCountResponseSchema,
)


class CountryBaseSchema(BaseModel):
    name: str = Field(..., description="Country name")


class CountryCreateSchema(BaseModel):
    name: str = Field(..., description="Country name")
    slug: Optional[str] = Field(
        None,
        description="A unique identifier for the country, typically a URL-friendly version of the name",
    )


class CountryUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, description="Country name")


class CountrySchema(CountryBaseSchema, BaseSlugSchema):
    is_active: bool = Field(True, description="Indicates if the country is active")


class CountryResponseSchema(BaseResponseSchema):
    data: Optional[CountrySchema] = None


class CountryTotalCountListResponseSchema(BaseTotalCountResponseSchema):
    data: Optional[list[CountrySchema]] = None


class CountryFilters(BaseFilters):
    name: Optional[str] = Field(None, description="Filter by coupon name")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
