import inspect
from typing import List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps.user import get_user_with_permission
from app.utils.responses import internal_server_error_response
from app.schemas.base_schema import BaseResponseSchema
from app.schemas.user_deps import UserDepSchema
from app.database.get_session import get_async_session
from app.core.loggers import app_logger as logger
from app.database.base_class import Base


class EntitySchema(BaseModel):
    """Schema for individual entity information"""

    name: str = Field(description="The name of the entity/model")
    table_name: str = Field(description="The database table name")
    is_base_model: bool = Field(description="Whether this is a base model class")


class EntityListResponseSchema(BaseResponseSchema):
    """Schema for entity list response"""

    data: List[EntitySchema] = Field(description="List of available entities")


class EntityRouter:
    def __init__(self):
        self.router = APIRouter()
        self.singular = "Entity"
        self.plural = "Entities"

        self.router.add_api_route(
            "/",
            self.list,
            methods=["GET"],
            response_model=EntityListResponseSchema,
            description="Get all available entities/models",
            summary="Get all entities",
        )

    def _get_all_models(self) -> List[EntitySchema]:
        """Dynamically discover all models from the models module"""
        entities = []

        # Import the models module
        from app import models

        # Get all attributes from the models module
        for attr_name in dir(models):
            attr_value = getattr(models, attr_name)

            # Check if it's a class and inherits from Base
            if (
                inspect.isclass(attr_value)
                and issubclass(attr_value, Base)
                and attr_value != Base
            ):

                # Get the table name
                table_name = getattr(attr_value, "__tablename__", None)

                # Skip if no table name (abstract models)
                if table_name:
                    entities.append(
                        EntitySchema(
                            name=attr_name,
                            table_name=table_name,
                            is_base_model=attr_value == Base,
                        )
                    )

        # Sort by name for consistent ordering
        entities.sort(key=lambda x: x.name)
        return entities

    async def list(
        self,
        user: UserDepSchema = Depends(get_user_with_permission("can_read_logs")),
        db: AsyncSession = Depends(get_async_session),
    ):
        """List all available entities/models"""
        try:
            entities = self._get_all_models()

            return EntityListResponseSchema(
                status=200,
                detail=f"Successfully retrieved {len(entities)} entities",
                data=entities,
            )

        except Exception as e:
            logger.error(f"Error retrieving entities: {str(e)}")
            return internal_server_error_response("Failed to retrieve entities")
