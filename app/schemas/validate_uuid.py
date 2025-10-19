from fastapi import HTTPException, status
from uuid import UUID
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import core_schema
from typing import Any
from pydantic.json_schema import JsonSchemaValue
from pydantic import ValidationError


def validate_uuid(uuid) -> bool:
    try:
        UUID(str(uuid))
        return True
    except (ValueError, TypeError):
        return False


def validate_uuid_str(uuid) -> str:
    try:
        UUID(str(uuid))
        return str(uuid)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid UUID: {uuid}"
        )


class UUIDStr(str):
    """Custom Pydantic type for UUID validation with proper error handling."""

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
            "format": "uuid",
            "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        }

    @classmethod
    def validate(cls, v, *args, **kwargs):
        if v is None:
            return v
        try:
            # Convert to string and validate UUID format
            uuid_str = str(v).strip()
            UUID(uuid_str)
            return str(uuid_str)
        except (ValueError, TypeError, AttributeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid UUID format: {v}. Expected a valid UUID string.",
            )
