from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Any, Tuple, Dict
from .base import CRUDBase
from ..models.activity_logs import ActivityLog
from ..cruds.base import CRUDBase
from ..schemas.activity_logs import ActivityLogCreateSchema
from ..core.loggers import db_logger as logger


class CRUDActivityLog(
    CRUDBase[ActivityLog, ActivityLogCreateSchema, ActivityLogCreateSchema]
):
    async def _remove_sensitive_data(
        self, data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Remove sensitive data from the given dictionary.

        This method removes sensitive data from the dictionary by checking
        if the key is in the list of sensitive data keys.
        """
        if data is None:
            return None

        sensitive_data_keys = ["password"]

        for key in sensitive_data_keys:
            if key in data:
                data[key] = "********"

        return data

    async def changes_made(
        self,
        previous_data: Optional[Dict[str, Any]],
        new_data: Optional[Dict[str, Any]],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Compare previous_data and new_data to identify exact changes made.

        Args:
            previous_data: The data before the action was performed
            new_data: The data after the action was performed

        Returns:
            Tuple containing:
            - Dictionary of changed fields from previous_data (or None)
            - Dictionary of changed fields from new_data (or None)
        """
        if previous_data is None and new_data is None:
            return None, None

        previous_data = await self._remove_sensitive_data(previous_data)
        new_data = await self._remove_sensitive_data(new_data)

        if previous_data is None:
            return None, new_data

        if new_data is None:
            return previous_data, None

        # Find exact changes
        previous_changes = {}
        new_changes = {}

        # Check all keys in both dictionaries
        all_keys = set(previous_data.keys()) | set(new_data.keys())

        for key in all_keys:
            prev_value = previous_data.get(key)
            new_value = new_data.get(key)

            if prev_value != new_value:
                if prev_value is not None:
                    previous_changes[key] = prev_value
                if new_value is not None:
                    new_changes[key] = new_value

        return previous_changes, new_changes

    async def create(
        self, db: AsyncSession, *, obj_in: ActivityLogCreateSchema
    ) -> ActivityLog:
        """
        Create a new record in the database.

        **Parameters**
        - `db`: The database session
        - `obj_in`: The data for the new record (must be a Pydantic model instance corresponding to the `CreateSchemaType`)

        **Returns**
        The created record after committing to the database.
        """
        db_obj = self.model(**obj_in.model_dump())
        previous_changes, new_changes = await self.changes_made(
            previous_data=db_obj.previous_data, new_data=db_obj.new_data
        )
        db_obj.previous_data = previous_changes or {}
        db_obj.new_data = new_changes or {}

        try:
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            # logger.info(f"Activity log created: {db_obj.uuid}")
            return db_obj
        except Exception as e:
            await db.rollback()  # Rollback on failure to avoid partial commits
            logger.error(f"Error creating object: {e}")
            raise RuntimeError(f"Error creating object: {e}")


activity_log_crud = CRUDActivityLog(ActivityLog)
