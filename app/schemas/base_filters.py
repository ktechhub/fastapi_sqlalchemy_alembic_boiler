from typing import Dict, Optional, List
from pydantic import BaseModel, Field

"""BaseFilters Schema"""


class BaseFilters(BaseModel):
    skip: Optional[int] = Field(
        0,
        description="The number of items to skip before starting the result set",
        example=10,
    )
    limit: Optional[int] = Field(
        10,
        description="The maximum number of items to return in the result set",
        example=50,
    )
    sort: Optional[str] = Field(
        "created_at:desc",
        description="Sorting criteria for the result set in the format 'field:direction' (e.g., 'name:asc' or 'created_at:desc')",
        example="name:asc",
    )
    include_relations: Optional[str] = Field(
        None,
        description="A comma-separated list of related models to include in the result set (e.g., 'permissions,users')",
        example="permissions,users",
    )
    fields: Optional[str] = Field(
        None,
        description="A comma-separated list of specific fields to include in the result set (e.g., 'id,name,email')",
        example="id,name,email",
    )
    search: Optional[str] = Field(
        None,
        description="A search term to filter the results by matching text across various fields (e.g., 'user name or description')",
        example="john",
        pattern=r"""^(?i)[\p{L}\p{N}\s]+(?:[.,'\-\s][\p{L}\p{N}\s]+)*[.]?$""",
    )
    search_fields: Optional[str] = Field(
        None,
        description="A comma-separated list of fields to search in. Supports direct fields (e.g., 'name,email') and related fields (e.g., 'user.email,user.name,profile.bio'). If not provided, all string fields from the current model will be automatically detected and used for search.",
        example="name,label,description,user.email,user.first_name",
    )
