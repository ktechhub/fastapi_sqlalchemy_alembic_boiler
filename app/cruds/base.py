from typing import Dict, Generic, Tuple, Type, TypeVar, List, Optional, Any, Union
from math import ceil
from datetime import datetime, timezone
from sqlalchemy import and_, asc, desc, func, or_, update, distinct, insert
from sqlalchemy.orm import contains_eager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from sqlalchemy.orm import joinedload
from app.database.base import Base
from ..core.loggers import db_logger as logger

ModelType = TypeVar("ModelType", bound="Base")  # type: ignore
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        """
        self.model = model

    def _build_filters(self, filters: Dict[str, Any]) -> List:
        """
        Dynamically build SQLAlchemy filter conditions based on the provided filters.

        **Supported Filters**
        - Standard field filters
        - Inclusion filters (IN operator)
        - Range filters (numeric and date ranges)
        - Boolean filters
        - Full-text search (with `search` and `search_fields`)
        """
        filter_conditions = []

        # Regular field-based and inclusion filters (existing functionality)
        for field, value in filters.items():
            column = getattr(self.model, field, None)
            if column is not None:
                if isinstance(value, (list, tuple)):
                    filter_conditions.append(column.in_(value))
                elif isinstance(value, dict):
                    # Process advanced conditions if value is a dict (handled below)
                    continue
                else:
                    filter_conditions.append(column == value)

        # Range filters (e.g., price: {"gte": 10, "lte": 100})
        if "range_filters" in filters:
            for field, range_values in filters["range_filters"].items():
                column = getattr(self.model, field, None)
                if column:
                    if "gte" in range_values:
                        filter_conditions.append(column >= range_values["gte"])
                    if "lte" in range_values:
                        filter_conditions.append(column <= range_values["lte"])
                    if "gt" in range_values:
                        filter_conditions.append(column > range_values["gt"])
                    if "lt" in range_values:
                        filter_conditions.append(column < range_values["lt"])

        # Date range filters (e.g., date_range: {"start": "2023-01-01", "end": "2023-01-31"})
        if "date_range" in filters:
            date_range = filters["date_range"]
            column = getattr(
                self.model, "created_at", None
            )  # Assuming a `created_at` field
            if column:
                if "start" in date_range:
                    filter_conditions.append(column >= date_range["start"])
                if "end" in date_range:
                    filter_conditions.append(column <= date_range["end"])

        # Boolean filters (e.g., is_active: True)
        if "boolean_filters" in filters:
            for field, value in filters["boolean_filters"].items():
                column = getattr(self.model, field, None)
                if column is not None:
                    filter_conditions.append(column.is_(value))

        # Full-text search across multiple fields (e.g., search="john", search_fields=["name", "email"])
        if "search" in filters and "search_fields" in filters:
            search_term = f"%{filters['search']}%"
            search_conditions = []
            # This code snippet is performing a database query to retrieve multiple Role entities with
            # their associated permissions eagerly loaded. Here's a breakdown of what each part does:
            for field_name in filters["search_fields"]:
                column = getattr(self.model, field_name, None)
                if column:
                    search_conditions.append(column.ilike(search_term))
            if search_conditions:
                filter_conditions.append(or_(*search_conditions))

        return filter_conditions

    def _extract_sort_params(
        self,
        sort: str = "",
        models: List[Type[Base]] = [],  # type: ignore
    ) -> List:
        """
        Extract sort parameters for SQLAlchemy.

        **Parameters**

        * `sort`: Sort parameters (e.g., "field1:asc,field2:desc")
        * `models`: List of models to help resolve field sorting.

        **Returns**

        A list of SQLAlchemy sort expressions.
        """
        if not sort:
            return [desc("created_at")]

        sort_params = []
        for sort_param in sort.split(","):
            if ":" in sort_param:
                field, order = sort_param.split(":")
                column = self._resolve_column(field, models)
                if column:
                    sort_params.append(desc(column) if order == "desc" else asc(column))
            else:
                column = self._resolve_column(sort_param, models)
                if column:
                    sort_params.append(asc(column))
        return sort_params

    def _resolve_column(
        self,
        field: str,
        models: List[Type[Base]],  # type: ignore
    ) -> Optional[Any]:
        """
        Resolves a column by searching through the current model and additional models.

        **Parameters**

        * `field`: The name of the field to resolve.
        * `models`: List of additional models to search for the field.

        **Returns**

        The resolved column or None if not found.
        """
        column = getattr(self.model, field, None)
        if column:
            return column
        for model in models:
            column = getattr(model, field, None)
            if column:
                return column
        return None

    async def get(
        self,
        db: AsyncSession,
        *,
        statement: Optional[Any] = None,
        models: Optional[List[Type[Base]]] = None,  # type: ignore
        joins: Optional[List[Tuple[Any, Any]]] = None,
        eager_load: Optional[List[Any]] = None,
        fields: Optional[List[Any]] = None,
        sort: Optional[str] = None,
        query_filters: Optional[List[Any]] = None,
        group_by: Optional[List[Any]] = None,
        **filters: Any,
    ) -> Any:
        """
        Retrieve data using flexible queries, including aggregates, joins, grouping, and filtering.

        **Parameters**
        - `db`: The database session
        - `statement`: A raw SQLAlchemy `select` statement (e.g., `select(func.sum(...))`). If provided, overrides default query construction.
        - `models`: Additional models to include in the query (default is None).
        - `joins`: List of tuples specifying joins between models (default is None).
        - `eager_load`: List of relationships to load using `contains_eager` (default is None).
        - `fields`: List of specific fields to select (default is None).
        - `sort`: A comma-separated list of fields to sort by (default is None).
        - `query_filters`: List of SQLAlchemy-style filters to apply (default is None).
        - `group_by`: List of fields to group the query by (default is None).
        - `**filters`: Keyword arguments for dynamic filtering.

        **Returns**
        The result of the query.

        **Example**
        ```python
        total_revenue_stmt = (
            select(func.sum(Payment.amount))
            .where(extract("year", Payment.paid_at) == 2025)
            .where(Payment.status == "success")
        )
        total_revenue = await user_crud.get(db=session, statement=total_revenue_stmt)
        ```

        **Example with joins and grouping**
        ```python
        user = await user_crud.get(
            db=session,
            models=[Profile],
            joins=[(User.id == Profile.user_id)],
            eager_load=[User.user_roles],
            fields=[User.id, User.email, Profile.bio],
            sort="email:asc",
            email="test@example.com"
        )
        revenue_breakdown_stmt = (
            select(PropertyType.label.label("property_type_name"), func.sum(Payment.amount).label("total_revenue"))
            .join(PropertyDebt, Payment.property_debt_uuid == PropertyDebt.uuid)
            .join(Property, PropertyDebt.property_uuid == Property.uuid)
            .join(PropertyType, Property.property_type_uuid == PropertyType.uuid)
            .where(extract("year", Payment.paid_at) == 2025)
            .where(Payment.status == "success")
            .group_by(PropertyType.label)
        )
        result = await user_crud.get(db=session, statement=revenue_breakdown_stmt)
                total_revenue_stmt = (
            select(func.sum(Payment.amount))
            .where(extract("year", Payment.paid_at) == 2025)
            .where(Payment.status == "success")
        )
        total_revenue = await user_crud.get(db=session, statement=total_revenue_stmt)
        revenue_breakdown_stmt = (
            select(PropertyType.label.label("property_type_name"), func.sum(Payment.amount).label("total_revenue"))
            .join(PropertyDebt, Payment.property_debt_uuid == PropertyDebt.uuid)
            .join(Property, PropertyDebt.property_uuid == Property.uuid)
            .join(PropertyType, Property.property_type_uuid == PropertyType.uuid)
            .where(extract("year", Payment.paid_at) == 2025)
            .where(Payment.status == "success")
            .group_by(PropertyType.label)
        )
        revenue_breakdown = await user_crud.get(db=session, statement=revenue_breakdown_stmt)
        ```
        """
        # If a custom statement is provided, execute it directly
        if statement is not None:
            result = await db.execute(statement)
            return result.scalars().first()

        # Default query construction for basic queries
        models = models or [self.model]
        query = select(*fields) if fields else select(*models)

        # Build filters
        filter_conditions = self._build_filters(filters)
        if query_filters:
            filter_conditions.extend(query_filters)

        if filter_conditions:
            query = query.where(and_(*filter_conditions))

        # Apply joins
        if joins:
            for join_condition in joins:
                query = query.join(*join_condition)

        # Apply eager loading
        if eager_load:
            for relationship in eager_load:
                query = query.options(joinedload(relationship))

        # Apply sorting
        if sort:
            sort_params = self._extract_sort_params(sort, models)
            query = query.order_by(*sort_params)

        # Apply grouping if provided
        if group_by:
            query = query.group_by(*group_by)

        # Execute the query
        result = await db.execute(query)
        return result.scalars().first()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        statement: Optional[Any] = None,
        skip: int = 0,
        limit: int = 100,
        models: Optional[List[Type[Base]]] = None,  # type: ignore
        joins: Optional[List[Tuple[Any, Any]]] = None,
        eager_load: Optional[List[Any]] = None,
        fields: Optional[List[Any]] = None,
        sort: Optional[str] = "",
        query_filters: Optional[List[Any]] = None,
        group_by: Optional[List[Any]] = None,
        unique_records: Optional[bool] = False,
        distinct_fields: Optional[List[Any]] = None,
        is_distinct: Optional[bool] = False,
        return_rows: Optional[bool] = False,
        **filters: Any,
    ) -> Dict[str, Any]:
        """
            Retrieve multiple records with pagination, custom statements, grouping, joins, and eager loading.

            **Parameters**
            - `db`: The database session
            - `statement`: A raw SQLAlchemy `select` statement for custom queries (default is None). If provided, it overrides query construction.
            - `skip`: The number of records to skip (default is 0).
            - `limit`: The maximum number of records to return (default is 100).
            - `models`: Additional models to include in the query (default is None).
            - `joins`: List of tuples specifying joins between models (default is None).
            - `eager_load`: List of relationships to load using `contains_eager` (default is None).
            - `fields`: List of specific fields to select (default is None).
            - `sort`: A comma-separated list of fields to sort by (default is None).
            - `query_filters`: List of SQLAlchemy-style filters to apply (default is None).
            - `group_by`: List of fields to group the query by (default is None).
            - `unique_records`: Flag to return only unique records (default is False).
            - `is_distinct`: Flag to apply distinct on the query (default is False).
            - `distinct_fields`: List of fields to use for distinct records (default is None).
            - `**filters`: Keyword arguments for filtering.

            **Returns**
            A dictionary containing:
            - `data`: A list of retrieved records.
            - `total_count`: The total number of records.

            **Example with raw statement**
        `   ``python
            revenue_breakdown_stmt = (
                select(PropertyType.label.label("property_type_name"), func.sum(Payment.amount).label("total_revenue"))
                .join(PropertyDebt, Payment.property_debt_uuid == PropertyDebt.uuid)
                .join(Property, PropertyDebt.property_uuid == Property.uuid)
                .join(PropertyType, Property.property_type_uuid == PropertyType.uuid)
                .group_by(PropertyType.label)
            )
            result = await user_crud.get_multi(db=session, statement=revenue_breakdown_stmt)
            ```

            **Example with default query**
            ```python
            users = await user_crud.get_multi(
                db=session,
                models=[Profile],
                joins=[(User.id == Profile.user_id)],
                eager_load=[User.user_roles],
                fields=[User.id, User.email, Profile.bio],
                sort="email:asc",
                skip=0,
                limit=10,
                query_filters=[User.is_active == True],
            )
            result = await user_crud.get_multi(
                db=session,
                skip=0,
                limit=20,
                sort="created_at:desc",
                search="john",
                search_fields=["first_name", "last_name", "email"],
                range_filters={"age": {"gte": 18, "lte": 60}},
                date_range={"start": "2023-01-01", "end": "2023-01-31"},
                boolean_filters={"is_active": True},
            )
            result = await user_crud.get_multi(
                db=session,
                skip=0,
                limit=10,
                sort="created_at:desc",
                filters={
                    "status": "active",
                    "range_filters": {
                        "age": {"gte": 18, "lte": 60}
                    },
                    "date_range": {
                        "start": "2023-01-01",
                        "end": "2023-02-01"
                    },
                    "boolean_filters": {
                        "is_active": True
                    },
                    "search": "john",
                    "search_fields": ["first_name", "last_name", "email"]
                }
            )
            ```
        """
        if skip < 0:
            skip = 0

        # Build filters
        filter_conditions = self._build_filters(filters)
        sort_params = []
        if sort:
            sort_params = self._extract_sort_params(sort, models)

        # If a custom statement is provided, execute it directly
        if statement is not None:
            count_query = select(func.count()).select_from(statement.subquery())
            total_count_result = await db.execute(count_query)
            total_count = total_count_result.scalar()

            statement = statement.offset(skip)
            # Apply pagination to the statement
            if limit > 0:
                statement = statement.limit(limit)

            if filter_conditions:
                statement = statement.where(*filter_conditions)

            if sort_params:
                statement = statement.order_by(*sort_params)

            # Execute the query
            result = await db.execute(statement)
            if not return_rows:
                data = (
                    result.scalars().unique().all()
                    if unique_records
                    else result.scalars().all()
                )
            else:
                data = result.all()
            return {"data": data, "total_count": total_count}

        # Default query construction
        models = models or [self.model]
        query = select(*fields) if fields else select(*models)

        if query_filters:
            filter_conditions.extend(query_filters)

        if filter_conditions:
            query = query.where(and_(*filter_conditions))

        # Apply joins
        if joins:
            for join_condition in joins:
                query = query.join(*join_condition)

        # Apply eager loading
        if eager_load:
            for relationship in eager_load:
                query = query.options(contains_eager(relationship))

        # Apply grouping
        if group_by:
            query = query.group_by(*group_by)

        # Apply sorting
        if sort_params:
            query = query.order_by(*sort_params)

        # Apply pagination (skip and limit)
        query = query.offset(skip)
        if limit > 0:
            query = query.limit(limit)

        if is_distinct and distinct_fields:
            query = query.distinct(*distinct_fields)

        # Execute the query
        result = await db.execute(query)
        items = (
            result.scalars().unique().all()
            if unique_records
            else result.scalars().all()
        )

        # Get the total count of matching records
        count_query = select(func.count()).select_from(self.model)
        if filter_conditions:
            count_query = count_query.where(and_(*filter_conditions))

        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar()

        return {"data": items, "total_count": total_count}

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record in the database.

        **Parameters**
        - `db`: The database session
        - `obj_in`: The data for the new record (must be a Pydantic model instance corresponding to the `CreateSchemaType`)

        **Returns**
        The created record after committing to the database.

        **Example**
        ```python
        new_user = await user_crud.create(
            db=session,
            obj_in=UserCreate(
                email="newuser@example.com",
                password="hashed_password",
                is_active=True
            )
        )
        ```
        """
        db_obj = self.model(**obj_in.model_dump())
        try:
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except Exception as e:
            await db.rollback()  # Rollback on failure to avoid partial commits
            logger.error(f"Error creating object: {e}")
            raise RuntimeError(f"Error creating object: {e}")

    async def create_multi(
        self, db: AsyncSession, *, objs_in: List[CreateSchemaType]
    ) -> List[ModelType]:
        """
        Create multiple records in a single database transaction.

        **Parameters**
        - `db`: The database session
        - `objs_in`: A list of Pydantic models containing the data for the new records

        **Returns**
        A list of created records after committing to the database.

        **Example**
        ```python
        users = await user_crud.create_multi(
            db=session,
            objs_in=[
                UserCreate(email="user1@example.com", password="hashed_password1"),
                UserCreate(email="user2@example.com", password="hashed_password2"),
            ]
        )
        ```
        """
        if not objs_in:
            return []

        # Convert Pydantic models to SQLAlchemy models
        db_objs = [self.model(**obj_in.model_dump()) for obj_in in objs_in]

        try:
            # Add all objects in a single batch operation
            db.add_all(db_objs)
            await db.commit()

            # Refresh the objects to reflect any database-generated values
            for db_obj in db_objs:
                await db.refresh(db_obj)

            return db_objs
        except Exception as e:
            await db.rollback()  # Rollback the transaction on failure
            logger.error(f"Error creating multiple objects: {e}")
            raise RuntimeError(f"Error creating multiple objects: {e}")

    async def bulk_create(
        self,
        db: AsyncSession,
        *,
        objs_in: List[CreateSchemaType],
        batch_size: int = 200,
    ) -> None:
        """
        Bulk insert multiple records in batches for optimized performance and stability.

        **Parameters**
        - `db`: The database session
        - `objs_in`: A list of Pydantic models containing the data for the new records
        - `batch_size`: The number of records to insert per batch (default is 200)

        **Note**: This method does not return the created objects or refresh them.

        **Example**
        ```python
        await user_crud.bulk_create(
            db=session,
            objs_in=[
                UserCreate(email="bulkuser1@example.com", password="hashed_password1"),
                UserCreate(email="bulkuser2@example.com", password="hashed_password2"),
            ],
            batch_size=200
        )
        ```
        """
        if not objs_in:
            return

        try:
            # Convert Pydantic models to dictionaries
            db_objs_data = [obj_in.model_dump() for obj_in in objs_in]

            # Calculate the number of batches needed
            total_batches = ceil(len(db_objs_data) / batch_size)

            # Insert in batches
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = start_idx + batch_size
                batch = db_objs_data[start_idx:end_idx]

                # Execute bulk insert for the current batch
                await db.execute(self.model.__table__.insert(), batch)

            # Commit all inserts
            await db.commit()

            return True

        except Exception as e:
            await db.rollback()
            raise RuntimeError(f"Error performing bulk insert: {e}")

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Optional[ModelType] = None,
        obj_in: Optional[UpdateSchemaType] = None,
        statement: Optional[Any] = None,
        allow_null: bool = False,
    ) -> Optional[ModelType]:
        """
        Update an existing record using either direct object updates or a custom SQLAlchemy statement.

        **Parameters**
        - `db`: The database session
        - `db_obj`: The existing record to update (used for object-based updates)
        - `obj_in`: The new data for the record (used for object-based updates)
        - `statement`: A custom SQLAlchemy update statement (used for statement-based updates)
        - `allow_null`: A flag indicating whether fields with `None` values should be updated (default is `False`)

        **Returns**
        The updated record (for object-based updates) or `None` (for statement-based updates).

        **Example with object-based update**
        ```python
        updated_user = await user_crud.update(
            db=session,
            db_obj=existing_user,
            obj_in=UserUpdate(email="newemail@example.com"),
            allow_null=False
        )
        ```

        **Example with statement-based update**
        ```python
        statement = (
            update(User)
            .where(User.id == 1)
            .values(email="newemail@example.com")
        )
        await user_crud.update(db=session, statement=statement)
        ```
        """
        if statement:
            # Statement-based update logic
            try:
                result = await db.execute(statement)
                await db.commit()
                return None  # No specific object is returned for statement updates
            except Exception as e:
                await db.rollback()
                logger.error(f"Error executing update statement: {e}")
                raise RuntimeError(f"Error executing update statement: {e}")

        # Object-based update logic
        if db_obj and obj_in:
            obj_data = db_obj.__dict__
            update_data = obj_in.model_dump()

            for field in obj_data:
                if field in update_data:
                    # Check allow_null flag to determine whether to update nullable fields
                    if update_data[field] is not None or allow_null:
                        setattr(db_obj, field, update_data[field])

            try:
                db.add(db_obj)
                await db.commit()
                await db.refresh(db_obj)
                return db_obj
            except Exception as e:
                await db.rollback()  # Rollback on failure to avoid partial commits
                logger.error(f"Error updating object: {e}")
                raise RuntimeError(f"Error updating object: {e}")

        raise ValueError(
            "Either `db_obj` and `obj_in` or `statement` must be provided."
        )

    async def update_multi(
        self,
        db: AsyncSession,
        *,
        updates: Optional[List[Dict[str, Any]]] = None,
        statement: Optional[Any] = None,
        allow_null: bool = False,
    ) -> int:
        """
        Update multiple records using either direct updates or a custom statement.

        **Parameters**
        - `db`: The database session
        - `updates`: A list of dictionaries containing the filters and update data (default is None)
        - `statement`: A custom SQLAlchemy update statement (default is None)
        - `allow_null`: Whether to update fields with `None` values (default is False)

        **Returns**
        The number of affected rows.

        **Example with statement**
        ```python
        statement = (
            update(User)
            .where(User.last_active <= datetime.now() - timedelta(days=365))
            .values(is_active=False)
        )
        await user_crud.update_multi(db=session, statement=statement)
        ```

        **Example with default updates**
        ```python
        await user_crud.update_multi(
            db=session,
            updates=[
                {"filters": {"id": 1}, "data": {"email": "newemail@example.com"}},
                {"filters": {"id": 2}, "data": {"is_active": False}},
            ]
        )
        ```
        """
        if statement:
            # Execute custom update statement
            result = await db.execute(statement)
            await db.commit()
            return result.rowcount

        # Default bulk update logic (update records using filters and data)
        if updates:
            updated_count = 0
            for update_info in updates:
                filters = update_info.get("filters")
                update_data = update_info.get("data")

                if not filters or not update_data:
                    continue

                # Build dynamic filter
                filter_conditions = [
                    getattr(self.model, field) == value
                    for field, value in filters.items()
                ]

                # Build the update statement
                stmt = (
                    update(self.model)
                    .where(and_(*filter_conditions))
                    .values(**update_data)
                )

                # Execute update statement
                result = await db.execute(stmt)
                updated_count += result.rowcount

            await db.commit()
            return updated_count

        return 0

    async def remove(
        self,
        db: AsyncSession,
        *,
        models: Optional[List[Type[Base]]] = None,  # type: ignore
        joins: Optional[List[Tuple[Any, Any]]] = None,
        fields: Optional[List[Any]] = None,
        sort: Optional[str] = None,
        query_filters: Optional[List[Any]] = None,
        **filters: Any,
    ) -> Optional[ModelType]:
        """
        Delete a record by dynamically specified conditions, with optional joins, sorting, and filters.

        **Parameters**
        - `db`: The database session
        - `models`: Additional models to include in the query (default is None).
        - `joins`: List of tuples specifying joins between models (e.g., [(ModelA.id == ModelB.model_a_id)]).
        - `fields`: List of specific fields to select before deletion (default is None).
        - `sort`: A comma-separated list of fields to sort by (e.g., "field1:asc,field2:desc") (default is None).
        - `query_filters`: List of SQLAlchemy-style filters to apply (default is None).
        - `**filters`: Keyword arguments for dynamic filtering (e.g., `email="test@example.com"`).

        **Returns**
        The deleted record, or `None` if no matching record was found.

        **Example**
        ```python
        deleted_user = await user_crud.remove(
            db=session,
            filters={"id": 1, "email": "user@example.com"},
            models=[Profile],
            joins=[(User.id == Profile.user_id)],
            sort="created_at:desc"
        )
        ```
        """
        models = models or [self.model]
        query = select(*fields) if fields else select(*models)

        # Build dynamic filter conditions
        filter_conditions = [
            getattr(self.model, field) == value for field, value in filters.items()
        ]
        if query_filters:
            filter_conditions.extend(query_filters)

        if filter_conditions:
            query = query.where(and_(*filter_conditions))

        # Apply joins if provided
        if joins:
            for join_condition in joins:
                query = query.join(*join_condition)

        # Apply sorting if provided
        if sort:
            sort_params = self.extract_sort_params(sort, models)
            query = query.order_by(*sort_params)

        # Fetch the record to delete
        result = await db.execute(query)
        obj = result.scalars().first()

        if not obj:
            return None

        try:
            # Delete the record
            await db.delete(obj)
            await db.commit()

        except Exception as e:
            await db.rollback()  # Rollback on failure to avoid partial commits
            logger.error(f"Error deleting object: {e}")
            raise RuntimeError(f"Error deleting object: {e}")
        return obj

    async def remove_multi(
        self,
        db: AsyncSession,
        *,
        models: Optional[List[Type[Base]]] = None,  # type: ignore
        joins: Optional[List[Tuple[Any, Any]]] = None,
        fields: Optional[List[Any]] = None,
        sort: Optional[str] = None,
        query_filters: Optional[List[Any]] = None,
        **filters: Any,
    ) -> List[ModelType]:
        """
        Delete multiple records dynamically by filters, joins, and sorting.

        **Parameters**
        - `db`: The database session
        - `models`: Additional models to include in the query (default is None).
        - `joins`: List of tuples specifying joins between models (e.g., [(ModelA.id == ModelB.model_a_id)]).
        - `fields`: List of specific fields to select before deletion (default is None).
        - `sort`: A comma-separated list of fields to sort by (e.g., "field1:asc,field2:desc") (default is None).
        - `query_filters`: List of SQLAlchemy-style filters to apply (default is None).
        - `**filters`: Keyword arguments for dynamic filtering (e.g., `email="test@example.com"`).

        **Returns**
        A list of deleted records.

        **Example**
        ```python
        deleted_users = await user_crud.remove_multi(
            db=session,
            filters={"is_active": False},
            models=[Profile],
            joins=[(User.id == Profile.user_id)],
            sort="created_at:desc"
        )
        ```
        """
        models = models or [self.model]
        query = select(*fields) if fields else select(*models)

        # Build dynamic filter conditions
        filter_conditions = self._build_filters(filters)
        if query_filters:
            filter_conditions.extend(query_filters)

        if filter_conditions:
            query = query.where(and_(*filter_conditions))

        # Apply joins if provided
        if joins:
            for join_condition in joins:
                query = query.join(*join_condition)

        # Apply sorting if provided
        if sort:
            sort_params = self.extract_sort_params(sort, models)
            query = query.order_by(*sort_params)

        # Fetch the records to delete
        result = await db.execute(query)
        objs = result.scalars().all()

        if not objs:
            return []

        try:
            # Delete all records
            for obj in objs:
                await db.delete(obj)

            await db.commit()
        except Exception as e:
            await db.rollback()  # Rollback on failure to avoid partial commits
            logger.error(f"Error deleting: {e}")
            raise RuntimeError(f"Error deleting: {e}")
        return objs

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        db_obj: Optional[ModelType] = None,
        statement: Optional[Any] = None,
        **filters: Any,
    ) -> Optional[ModelType]:
        """
        Soft delete an existing record using either direct object updates or a custom SQLAlchemy statement.

        **Parameters**
        - `db`: The database session
        - `db_obj`: The existing record to update (used for object-based updates)
        - `statement`: A custom SQLAlchemy update statement (used for statement-based updates)
        - `**filters`: Keyword arguments for dynamic filtering.

        **Returns**
        The updated record (for object-based updates) or `None` (for statement-based updates).
        """
        if statement:
            # Statement-based update logic
            try:
                result = await db.execute(statement)
                await db.commit()
                return None  # No specific object is returned for statement updates
            except Exception as e:
                await db.rollback()
                logger.error(f"Error executing update statement: {e}")
                raise RuntimeError(f"Error executing update statement: {e}")

        # Object-based update logic
        if db_obj:
            setattr(db_obj, "soft_deleted_at", datetime.now(timezone.utc))
            setattr(db_obj, "soft_deleted", True)
            setattr(db_obj, "is_active", False)

            try:
                db.add(db_obj)
                await db.commit()
                await db.refresh(db_obj)
                return db_obj
            except Exception as e:
                await db.rollback()
                logger.error(f"Error updating object: {e}")
                raise RuntimeError(f"Error updating object: {e}")

    async def restore(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        fields: Dict = {"soft_deleted": False, "soft_deleted_at": None},
    ):
        """
        Restore a soft-deleted record by updating the `soft_deleted` and `soft_deleted_at` fields.

        **Parameters**
        - `db`: The database session
        - `db_obj`: The soft-deleted record to restore
        - `fields`: The fields to update for restoration (default is {"soft_deleted": False, "soft_deleted_at": None}).

        **Returns**
        The restored record after committing to the database.

        **Example**
        ```python
        restored_user = await user_crud.restore_record(
            db=session,
            db_obj=deleted_user,
            fields={"soft_deleted": False, "soft_deleted_at": None}
        )
        ```
        """
        for field, value in fields.items():
            setattr(db_obj, field, value)
        try:
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except Exception as e:
            await db.rollback()
            logger.error(f"Error restoring object: {e}")
            raise RuntimeError(f"Error restoring object: {e}")
