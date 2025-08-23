from typing import Dict, Optional, Type, TypeVar, Union, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from ..schemas.activity_logs import ActivityLogCreateSchema
from .activity_logs import activity_log_crud
from .base import CRUDBase
from ..core.loggers import app_logger as logger
from ..core.config import settings

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class ActivityCRUDBase(CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base CRUD class that includes activity logging capabilities.
    Inherit from this class instead of CRUDBase to get automatic activity logging.
    """

    def __init__(self, model: Type[ModelType], ttl: int = settings.CACHE_TTL_MEDIUM):
        super().__init__(model, ttl=ttl)
        self.singular = model.__name__.lower()
        self.model_name = model.__name__.lower()

    def _get_identifier(self, db_obj: ModelType) -> str:
        """Get the identifier (uuid or id) from the database object."""
        return str(getattr(db_obj, "uuid", getattr(db_obj, "id", "unknown")))

    async def _create_activity_log(
        self,
        db: AsyncSession,
        *,
        user_uuid: Optional[str] = None,
        action: str,
        previous_data: Optional[Dict] = None,
        new_data: Optional[Dict] = None,
        description: Optional[str] = None,
    ) -> None:
        """Create an activity log entry."""
        # Skip logging if the model is ActivityLog to prevent infinite recursion
        if self.model_name == "ActivityLog":
            return
        if user_uuid is None:
            logger.warning(f"User UUID is None for {self.singular}")
            return
        await activity_log_crud.create(
            db=db,
            obj_in=ActivityLogCreateSchema(
                user_uuid=user_uuid,
                entity=self.singular,
                action=action,
                previous_data=previous_data or {},
                new_data=new_data or {},
                description=description,
            ),
        )

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: Union[CreateSchemaType, Dict[str, Any]],
        user_uuid: Optional[str] = None,
    ) -> ModelType:
        """Override create method to add activity logging."""
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        if user_uuid is not None:
            # Log the creation activity
            await self._create_activity_log(
                db=db,
                user_uuid=user_uuid,
                action="create",
                new_data=(
                    db_obj.to_dict() if hasattr(db_obj, "to_dict") else obj_in_data
                ),
                description=f"{self.model_name} with identifier {self._get_identifier(db_obj)} created successfully",
            )

        await self.invalidate_cache()

        return db_obj

    async def create_multi(
        self,
        db: AsyncSession,
        *,
        objs_in: List[Union[CreateSchemaType, Dict[str, Any]]],
        user_uuid: Optional[str] = None,
    ) -> List[ModelType]:
        """Override create_multi method to add activity logging."""
        db_objs = await super().create_multi(db, objs_in=objs_in)
        if user_uuid is not None:
            activity_logs = [
                ActivityLogCreateSchema(
                    user_uuid=user_uuid,
                    entity=self.singular,
                    action="create",
                    previous_data={},
                    new_data=(
                        db_obj.to_dict() if hasattr(db_obj, "to_dict") else db_obj
                    ),
                    description=f"{self.model_name} created successfully",
                )
                for db_obj in db_objs
            ]
            await activity_log_crud.create_multi(
                db=db,
                objs_in=activity_logs,
            )

        await self.invalidate_cache()
        return db_objs

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        user_uuid: Optional[str] = None,
        allow_null: bool = False,
    ) -> ModelType:
        """Override update method to add activity logging."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        if not allow_null:
            update_data = {k: v for k, v in update_data.items() if v is not None}

        # Store previous data for logging
        previous_data = db_obj.to_dict() if hasattr(db_obj, "to_dict") else None

        for field in update_data:
            setattr(db_obj, field, update_data[field])

        await db.commit()
        await db.refresh(db_obj)

        # Log the update activity
        if user_uuid is not None:
            await self._create_activity_log(
                db=db,
                user_uuid=user_uuid,
                action="update",
                previous_data=previous_data,
                new_data=(
                    db_obj.to_dict() if hasattr(db_obj, "to_dict") else update_data
                ),
                description=f"{self.model_name} with identifier {self._get_identifier(db_obj)} updated successfully",
            )

        await self.invalidate_cache()

        return db_obj

    async def remove(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        user_uuid: Optional[str] = None,
    ) -> ModelType:
        """Override remove method to add activity logging."""
        # Store data for logging
        previous_data = db_obj.to_dict() if hasattr(db_obj, "to_dict") else None
        identifier = self._get_identifier(db_obj)

        await db.delete(db_obj)
        await db.commit()
        if user_uuid is not None:
            # Log the deletion activity
            await self._create_activity_log(
                db=db,
                user_uuid=user_uuid,
                action="delete",
                previous_data=previous_data,
                description=f"{self.model_name} with identifier {identifier} deleted successfully",
            )

        await self.invalidate_cache()

        return db_obj
