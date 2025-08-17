import json
import hashlib
from typing import Any, Optional, Dict, List, Set, Type
from datetime import datetime
from aiocache import caches, Cache
from aiocache.serializers import JsonSerializer
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy import inspect

from ..core.config import settings
from ..core.loggers import app_logger as logger


class SQLAlchemyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for SQLAlchemy objects"""

    def default(self, obj):
        # Handle SQLAlchemy model instances
        if hasattr(obj, "to_dict"):
            # Always try to use to_dict_with_relations first, fallback to to_dict
            if hasattr(obj, "to_dict_with_relations"):
                return obj.to_dict_with_relations()
            else:
                return obj.to_dict()
        # Handle datetime objects
        elif isinstance(obj, datetime):
            return obj.isoformat()
        # Handle other non-serializable objects
        else:
            return super().default(obj)


class AsyncCacheService:
    """Async cache service for handling Redis caching operations using aiocache"""

    def __init__(
        self,
        enabled: bool = settings.CACHE_ENABLED,
        ttl: int = settings.CACHE_TTL_MEDIUM,
    ):
        self.enabled = enabled
        self.ttl = ttl

        # Initialize empty dependencies - will be populated automatically
        self.model_dependencies = {}

        # Configure aiocache if not already configured
        self._configure_cache()

    def _configure_cache(self):
        """Configure aiocache with Redis backend"""
        try:
            # Configure aiocache with Redis backend
            cache_config = {
                "cache": "aiocache.RedisCache",
                "endpoint": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "timeout": 5,
                "serializer": {"class": "aiocache.serializers.JsonSerializer"},
                "namespace": settings.APP_NAME,
                "key_builder": self._key_builder,
            }

            # Only add password if it's provided
            if settings.REDIS_PASSWORD:
                cache_config["password"] = settings.REDIS_PASSWORD

            caches.set_config({"default": cache_config})
            self.cache = caches.get("default")
        except Exception as e:
            logger.warning(f"Failed to configure aiocache: {e}")
            self.cache = None

    def _key_builder(self, func, *args, **kwargs):
        """Custom key builder for aiocache"""
        # This will be overridden by our custom key generation
        return f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

    def detect_model_dependencies(self, model_class: Type) -> Set[str]:
        """
        Automatically detect model dependencies from SQLAlchemy relationships

        Args:
            model_class: SQLAlchemy model class

        Returns:
            Set of dependent model names
        """
        dependencies = set()
        mapper = inspect(model_class)

        for relationship in mapper.relationships:
            # Get the target model name
            target_model = relationship.mapper.class_
            target_name = target_model.__name__.lower()

            # Add the target model as a dependency
            dependencies.add(target_name)

            # If this is a many-to-many relationship, also add the association table
            if relationship.secondary is not None:
                # Try to infer the association table name
                if hasattr(relationship.secondary, "__tablename__"):
                    assoc_name = relationship.secondary.__tablename__.replace("_", "")
                    dependencies.add(assoc_name)

        return dependencies

    def register_model_dependencies(self, model_name: str, dependencies: List[str]):
        """
        Register dependencies for a model

        Args:
            model_name: Name of the model
            dependencies: List of dependent model names
        """
        self.model_dependencies[model_name] = dependencies

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """
        Generate a unique cache key based on prefix and parameters

        Args:
            prefix: Cache key prefix (e.g., 'roles:list')
            **kwargs: Parameters to include in the cache key

        Returns:
            Unique cache key string
        """
        # Filter out non-serializable parameters
        serializable_kwargs = {}
        for key, value in kwargs.items():
            try:
                # Test if the value is JSON serializable with our custom encoder
                json.dumps(value, cls=SQLAlchemyJSONEncoder)
                serializable_kwargs[key] = value
            except (TypeError, ValueError):
                continue

        # Sort kwargs to ensure consistent key generation
        sorted_params = sorted(serializable_kwargs.items())
        param_str = json.dumps(sorted_params, sort_keys=True, cls=SQLAlchemyJSONEncoder)

        # Create hash for long parameter strings
        if len(param_str) > 100:
            param_hash = hashlib.md5(param_str.encode()).hexdigest()
            return f"{prefix}:{param_hash}"

        return f"{prefix}:{param_str}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled or not self.cache:
            return None

        try:
            cached_data = await self.cache.get(key)
            if cached_data:
                return cached_data
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.cache:
            return False

        try:
            ttl = ttl or self.ttl
            await self.cache.set(key, value, ttl=ttl)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.cache:
            return False

        try:
            result = await self.cache.delete(key)
            if result:
                print(f"Deleted cache key: {key}")
            return bool(result)
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> bool:
        """
        Delete all keys matching a pattern

        Args:
            pattern: Redis pattern (e.g., 'roles:*')

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.cache:
            return False

        try:
            # aiocache doesn't have direct pattern deletion, so we'll use the underlying client
            if hasattr(self.cache, "_redis"):
                keys = await self.cache._redis.keys(pattern)
                if keys:
                    result = await self.cache._redis.delete(*keys)
                    print(f"Deleted {result} cache keys matching pattern: {pattern}")
                    return True
            return False
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return False

    async def invalidate_model_cache(self, model_name: str) -> bool:
        """
        Invalidate all cache entries for a specific model

        Args:
            model_name: Name of the model (e.g., 'roles', 'users')

        Returns:
            True if successful, False otherwise
        """
        pattern = f"{model_name}:*"
        return await self.delete_pattern(pattern)

    async def invalidate_model_cache_with_dependencies(self, model_name: str) -> bool:
        """
        Invalidate cache for a model and all its dependent models

        Args:
            model_name: Name of the model (e.g., 'roles', 'users')

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Get all models that need cache invalidation
            models_to_invalidate = self._get_models_to_invalidate(model_name)

            # Invalidate cache for all affected models
            for model in models_to_invalidate:
                pattern = f"{model}:*"
                if hasattr(self.cache, "_redis"):
                    keys = await self.cache._redis.keys(pattern)
                    if keys:
                        result = await self.cache._redis.delete(*keys)
                        print(f"Invalidated {result} cache keys for model: {model}")

            return True
        except Exception as e:
            logger.warning(f"Cache invalidation error for {model_name}: {e}")
            return False

    def _get_models_to_invalidate(self, model_name: str) -> Set[str]:
        """
        Get all models that should have their cache invalidated when a specific model changes

        Args:
            model_name: Name of the model that changed

        Returns:
            Set of model names to invalidate
        """
        models_to_invalidate = {model_name}

        # Add direct dependencies
        if model_name in self.model_dependencies:
            models_to_invalidate.update(self.model_dependencies[model_name])

        # Add reverse dependencies (models that depend on this model)
        for dependent_model, dependencies in self.model_dependencies.items():
            if model_name in dependencies:
                models_to_invalidate.add(dependent_model)

        print(f"Models to invalidate for {model_name}: {models_to_invalidate}")
        return models_to_invalidate

    def get_list_cache_key(self, model_name: str, **filters) -> str:
        """
        Generate cache key for list operations

        Args:
            model_name: Name of the model
            **filters: Filter parameters (skip, limit, sort, etc.)

        Returns:
            Cache key string
        """
        return self._generate_cache_key(f"{model_name}:list", **filters)

    async def cache_list_result(
        self, model_name: str, result: Dict[str, Any], **filters
    ) -> bool:
        """
        Cache list operation result

        Args:
            model_name: Name of the model
            result: Result data to cache
            **filters: Filter parameters used for the query

        Returns:
            True if successful, False otherwise
        """
        key = self.get_list_cache_key(model_name, **filters)
        return await self.set(key, result, self.ttl)

    async def get_cached_list(
        self, model_name: str, **filters
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached list result

        Args:
            model_name: Name of the model
            **filters: Filter parameters used for the query

        Returns:
            Cached result or None if not found
        """
        key = self.get_list_cache_key(model_name, **filters)
        return await self.get(key)

    def get_item_cache_key(self, model_name: str, identifier: str, **filters) -> str:
        """
        Generate cache key for individual item operations

        Args:
            model_name: Name of the model
            identifier: Item identifier (uuid, id, etc.)
            **filters: Additional filter parameters (eager_load, fields, etc.)

        Returns:
            Cache key string
        """
        return self._generate_cache_key(f"{model_name}:item:{identifier}", **filters)

    async def cache_item_result(
        self, model_name: str, identifier: str, result: Any, **filters
    ) -> bool:
        """
        Cache individual item operation result

        Args:
            model_name: Name of the model
            identifier: Item identifier (uuid, id, etc.)
            result: Result data to cache
            **filters: Additional filter parameters used for the query

        Returns:
            True if successful, False otherwise
        """
        key = self.get_item_cache_key(model_name, identifier, **filters)
        return await self.set(key, result, self.ttl)

    async def get_cached_item(
        self, model_name: str, identifier: str, **filters
    ) -> Optional[Any]:
        """
        Get cached individual item result

        Args:
            model_name: Name of the model
            identifier: Item identifier (uuid, id, etc.)
            **filters: Additional filter parameters used for the query

        Returns:
            Cached result or None if not found
        """
        key = self.get_item_cache_key(model_name, identifier, **filters)
        return await self.get(key)


# Global async cache service instance
async_cache_service = AsyncCacheService()
