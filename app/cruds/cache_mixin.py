from typing import Dict, Any, Optional, List, Type, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..services.async_cache_service import async_cache_service
from ..core.loggers import app_logger as logger
from ..core.config import settings


class CacheMixin:
    """Mixin to add caching functionality to CRUD classes"""

    def __init__(self, model_name: str = None, ttl: int = settings.CACHE_TTL_MEDIUM):
        """
        Initialize cache mixin

        Args:
            model_name: Name of the model for cache keys (defaults to model.__name__.lower())
            ttl: Time to live for cache entries
        """
        self.model_name = model_name or self.model.__name__.lower()
        self.ttl = ttl
        self.cache_service = async_cache_service

        # Auto-detect and register dependencies if not already registered
        self._register_dependencies()

    def _register_dependencies(self):
        """Register model dependencies for cache invalidation"""
        if (
            not hasattr(self, "model")
            or self.model_name not in self.cache_service.model_dependencies
        ):
            try:
                # Auto-detect dependencies from SQLAlchemy relationships
                detected_deps = self.cache_service.detect_model_dependencies(self.model)
                if detected_deps:
                    self.cache_service.register_model_dependencies(
                        self.model_name, list(detected_deps)
                    )
                    # print(
                    #     f"Auto-registered dependencies for {self.model_name}: {detected_deps}"
                    # )
            except Exception as e:
                logger.warning(
                    f"Could not auto-detect dependencies for {self.model_name}: {e}"
                )

    def _get_cache_filters(
        self, skip: int = 0, limit: int = 100, sort: str = "", **filters
    ) -> Dict[str, Any]:
        """
        Extract cache-relevant filters from query parameters

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            sort: Sort parameters
            **filters: Additional filters

        Returns:
            Dictionary of cache-relevant parameters
        """
        cache_filters = {"skip": skip, "limit": limit, "sort": sort}

        # Add other filters that affect the result, but only if they're JSON serializable
        for key, value in filters.items():
            if value is not None:
                # Check if the value is JSON serializable
                try:
                    import json

                    json.dumps(value)
                    cache_filters[key] = value
                except (TypeError, ValueError):
                    # Skip non-serializable values (like SQLAlchemy Select objects)
                    # logger.debug(f"Skipping non-serializable filter {key}: {type(value)}")
                    continue

        return cache_filters

    async def get_multi_with_cache(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        sort: str = "",
        **filters: Any,
    ) -> Dict[str, Any]:
        """
        Get multiple records with caching support

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            sort: Sort parameters
            **filters: Additional filters

        Returns:
            Dictionary containing data and total_count
        """
        # Generate cache filters using optimized method
        cache_filters = self._get_cache_filters(
            skip=skip, limit=limit, sort=sort, **filters
        )

        # Generate cache key directly using the optimized method
        cache_key = self.cache_service.get_list_cache_key(
            self.model_name, **cache_filters
        )

        # Try to get from cache first
        cached_result = await self.cache_service.get(cache_key)
        if cached_result:
            # logger.info(f"Using cached data for {self.model_name} list")
            return cached_result

        # If not in cache, fetch from database
        result = await self.get_multi(
            db=db, skip=skip, limit=limit, sort=sort, **filters
        )

        # Cache the result using the optimized set method
        await self.cache_service.set(cache_key, result, self.ttl)

        return result

    async def invalidate_cache(self) -> bool:
        """
        Invalidate all cache entries for this model using optimized pattern deletion

        Returns:
            True if successful, False otherwise
        """
        return await self.cache_service.invalidate_model_cache(self.model_name)

    async def invalidate_cache_with_dependencies(self) -> bool:
        """
        Invalidate cache for this model and all its dependent models using optimized batch operations

        Returns:
            True if successful, False otherwise
        """
        return await self.cache_service.invalidate_model_cache_with_dependencies(
            self.model_name
        )

    async def invalidate_list_cache(self, **filters) -> bool:
        """
        Invalidate specific list cache entries using optimized cache key generation

        Args:
            **filters: Filter parameters to match cache keys

        Returns:
            True if successful, False otherwise
        """
        cache_filters = self._get_cache_filters(**filters)
        cache_key = self.cache_service.get_list_cache_key(
            self.model_name, **cache_filters
        )
        return await self.cache_service.delete(cache_key)

    def _get_item_cache_filters(
        self,
        eager_load: Optional[List[Any]] = None,
        fields: Optional[Union[str, List[Any]]] = None,
        **filters,
    ) -> Dict[str, Any]:
        """
        Extract cache-relevant filters for individual item queries

        Args:
            eager_load: List of relationships to eager load
            fields: Specific fields to select
            **filters: Additional filters

        Returns:
            Dictionary of cache-relevant parameters
        """
        cache_filters = {}

        # Add eager_load information if provided
        if eager_load:
            cache_filters["eager_load"] = [str(rel) for rel in eager_load]

        # Add fields information if provided
        if fields:
            if isinstance(fields, str):
                cache_filters["fields"] = fields
            else:
                cache_filters["fields"] = [str(field) for field in fields]

        # Add other filters that affect the result, but only if they're JSON serializable
        for key, value in filters.items():
            if value is not None:
                try:
                    import json

                    json.dumps(value)
                    cache_filters[key] = value
                except (TypeError, ValueError):
                    continue

        return cache_filters

    async def get_with_cache(
        self,
        db: AsyncSession,
        *,
        identifier: str,
        eager_load: Optional[List[Any]] = None,
        fields: Optional[Union[str, List[Any]]] = None,
        **filters: Any,
    ) -> Any:
        """
        Get a single record with caching support

        Args:
            db: Database session
            identifier: Item identifier (uuid, id, etc.)
            eager_load: List of relationships to eager load
            fields: Specific fields to select
            **filters: Additional filters

        Returns:
            The retrieved record or None
        """
        # Generate cache filters
        cache_filters = self._get_item_cache_filters(
            eager_load=eager_load, fields=fields, **filters
        )

        # Generate cache key directly using the optimized method
        cache_key = self.cache_service.get_item_cache_key(
            self.model_name, identifier, **cache_filters
        )

        # Try to get from cache first
        cached_result = await self.cache_service.get(cache_key)
        if cached_result:
            # logger.info(f"Using cached data for {self.model_name} item {identifier}")
            return cached_result

        # If not in cache, fetch from database
        result = await self.get(
            db=db,
            eager_load=eager_load,
            fields=fields,
            **{self._get_identifier_field_name(): identifier, **filters},
        )

        # Cache the result if found using the optimized set method
        if result:
            await self.cache_service.set(cache_key, result, self.ttl)

        return result

    async def invalidate_item_cache(self, identifier: str, **filters) -> bool:
        """
        Invalidate a specific item cache entry using optimized cache key generation

        Args:
            identifier: Item identifier (uuid, id, etc.)
            **filters: Additional filter parameters

        Returns:
            True if successful, False otherwise
        """
        cache_filters = self._get_item_cache_filters(**filters)
        cache_key = self.cache_service.get_item_cache_key(
            self.model_name, identifier, **cache_filters
        )
        return await self.cache_service.delete(cache_key)
