import re
from fastapi import HTTPException, status
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import core_schema
from typing import Any
from pydantic.json_schema import JsonSchemaValue


def validate_slug(slug: str) -> bool:
    """
    Validate if a string is a valid slug format.
    A valid slug should:
    - Be lowercase
    - Contain only alphanumeric characters and hyphens
    - Not start or end with a hyphen
    - Not contain consecutive hyphens
    - Be between 1 and 255 characters
    """
    if not slug or not isinstance(slug, str):
        return False

    slug = slug.strip()

    # Check length
    if len(slug) < 1 or len(slug) > 255:
        return False

    # Check if it starts or ends with hyphen
    if slug.startswith("-") or slug.endswith("-"):
        return False

    # Check for consecutive hyphens
    if "--" in slug:
        return False

    # Check if it contains only lowercase letters, numbers, and hyphens
    if not re.match(r"^[a-z0-9-]+$", slug):
        return False

    return True


def validate_slug_str(slug: str) -> str:
    """
    Validate and return a slug string, raising HTTPException if invalid.
    """
    if not validate_slug(slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid slug format: {slug}. Slug must be lowercase, contain only alphanumeric characters and hyphens, and be between 1-255 characters.",
        )
    return slug


class SlugStr(str):
    """Custom Pydantic type for slug validation with proper error handling."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                str, return_schema=core_schema.str_schema()
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {
            "type": "string",
            "format": "slug",
            "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$",
            "minLength": 1,
            "maxLength": 255,
            "description": "A URL-friendly slug (lowercase alphanumeric characters and hyphens)",
        }

    @classmethod
    def validate(cls, v, *args, **kwargs):
        if v is None:
            return v
        try:
            # Convert to string and validate slug format
            slug_str = str(v).strip().lower()

            # Check length
            if len(slug_str) < 1 or len(slug_str) > 255:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid slug length: {v}. Slug must be between 1-255 characters.",
                )

            # Check if it starts or ends with hyphen
            if slug_str.startswith("-") or slug_str.endswith("-"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid slug format: {v}. Slug cannot start or end with a hyphen.",
                )

            # Check for consecutive hyphens
            if "--" in slug_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid slug format: {v}. Slug cannot contain consecutive hyphens.",
                )

            # Check if it contains only lowercase letters, numbers, and hyphens
            if not re.match(r"^[a-z0-9-]+$", slug_str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid slug format: {v}. Slug must contain only lowercase letters, numbers, and hyphens.",
                )

            return slug_str
        except (ValueError, TypeError, AttributeError) as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid slug format: {v}. Expected a valid slug string.",
            )
