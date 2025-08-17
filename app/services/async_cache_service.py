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
        # Handle SQLAlchemy objects that don't have to_dict method
        elif hasattr(obj, "__table__"):
            # For SQLAlchemy model instances without to_dict method
            try:
                # Try to convert to dict using SQLAlchemy's __dict__
                result = {}
                for key, value in obj.__dict__.items():
                    if not key.startswith("_"):
                        if isinstance(value, datetime):
                            result[key] = value.isoformat()
                        else:
                            result[key] = value
                return result
            except Exception:
                # If conversion fails, return a simple representation
                return f"{obj.__class__.__name__}(id={getattr(obj, 'id', 'unknown')})"
        # Handle other non-serializable objects
        else:
            try:
                # Try to convert to string
                return str(obj)
            except Exception:
                # If all else fails, return a simple representation
                return f"{obj.__class__.__name__}(unserializable)"


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
                "namespace": settings.APP_NAME.lower(),
            }

            # Only add password if it's provided
            if settings.REDIS_PASSWORD:
                cache_config["password"] = settings.REDIS_PASSWORD

            caches.set_config({"default": cache_config})
            self.cache = caches.get("default")
        except Exception as e:
            logger.warning(f"Failed to configure aiocache: {e}")
            self.cache = None

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
                try:
                    # Try to deserialize the data
                    return json.loads(cached_data)
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to deserialize cached data for key {key}: {e}"
                    )
                    return None
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

            # Try to serialize the value first to catch any serialization errors
            try:
                # Use custom encoder for SQLAlchemy objects
                serialized_value = json.dumps(value, cls=SQLAlchemyJSONEncoder)
            except Exception as serialization_error:
                logger.warning(
                    f"Failed to serialize value for cache key {key}: {serialization_error}"
                )
                # Try to serialize a simplified version
                try:
                    if isinstance(value, dict) and "data" in value:
                        # For list results, try to serialize just the data
                        simplified_value = {
                            "data": [
                                str(item) if hasattr(item, "__table__") else item
                                for item in value.get("data", [])
                            ],
                            "total_count": value.get("total_count", 0),
                        }
                        serialized_value = json.dumps(
                            simplified_value, cls=SQLAlchemyJSONEncoder
                        )
                    else:
                        # For other types, try to convert to string
                        serialized_value = json.dumps(str(value))
                except Exception as fallback_error:
                    logger.error(
                        f"Failed to serialize even simplified value for cache key {key}: {fallback_error}"
                    )
                    return False

            await self.cache.set(key, serialized_value, ttl=ttl)
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
        Delete all keys matching a pattern using SCAN for better performance

        Args:
            pattern: Redis pattern (e.g., 'roles:*')

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.cache:
            return False

        try:
            # Use SCAN instead of KEYS for better performance (non-blocking)
            if hasattr(self.cache, "_redis"):
                cursor = 0
                total_deleted = 0

                while True:
                    # SCAN with count limit for better performance
                    cursor, keys = await self.cache._redis.scan(
                        cursor, match=pattern, count=100  # Process 100 keys at a time
                    )

                    if keys:
                        # Delete keys in batch
                        deleted = await self.cache._redis.delete(*keys)
                        total_deleted += deleted

                    # Stop when cursor returns to 0
                    if cursor == 0:
                        break

                if total_deleted > 0:
                    print(
                        f"Deleted {total_deleted} cache keys matching pattern: {pattern}"
                    )
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
        Invalidate cache for a model and all its dependent models using optimized batch operations

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

            if not hasattr(self.cache, "_redis"):
                return False

            # Collect all keys to delete in a single batch operation
            all_keys_to_delete = []

            for model in models_to_invalidate:
                pattern = f"{model}:*"
                cursor = 0

                while True:
                    # Use SCAN for each model pattern
                    cursor, keys = await self.cache._redis.scan(
                        cursor, match=pattern, count=100
                    )

                    if keys:
                        all_keys_to_delete.extend(keys)

                    if cursor == 0:
                        break

            # Delete all keys in a single batch operation
            if all_keys_to_delete:
                # Split into chunks to avoid Redis command size limits
                chunk_size = 1000
                total_deleted = 0

                for i in range(0, len(all_keys_to_delete), chunk_size):
                    chunk = all_keys_to_delete[i : i + chunk_size]
                    deleted = await self.cache._redis.delete(*chunk)
                    total_deleted += deleted

                print(
                    f"Invalidated {total_deleted} cache keys for {len(models_to_invalidate)} models"
                )
                return True

            return False
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

    async def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache in a single operation

        Args:
            keys: List of cache keys to retrieve

        Returns:
            Dictionary mapping keys to their values (None if not found)
        """
        if not self.enabled or not self.cache:
            return {key: None for key in keys}

        try:
            if hasattr(self.cache, "_redis"):
                # Use pipeline for better performance
                pipe = self.cache._redis.pipeline()
                for key in keys:
                    pipe.get(key)
                results = await pipe.execute()

                return {key: result for key, result in zip(keys, results)}
            else:
                # Fallback to individual gets
                results = {}
                for key in keys:
                    results[key] = await self.get(key)
                return results
        except Exception as e:
            logger.warning(f"Cache get_multi error: {e}")
            return {key: None for key in keys}

    async def set_multi(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set multiple values in cache in a single operation

        Args:
            data: Dictionary mapping keys to values
            ttl: Time to live in seconds (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.cache:
            return False

        try:
            ttl = ttl or self.ttl

            if hasattr(self.cache, "_redis"):
                # Use pipeline for better performance
                pipe = self.cache._redis.pipeline()
                for key, value in data.items():
                    pipe.setex(key, ttl, value)
                await pipe.execute()
                return True
            else:
                # Fallback to individual sets
                for key, value in data.items():
                    await self.set(key, value, ttl)
                return True
        except Exception as e:
            logger.warning(f"Cache set_multi error: {e}")
            return False

    async def delete_multi(self, keys: List[str]) -> int:
        """
        Delete multiple keys from cache in a single operation

        Args:
            keys: List of cache keys to delete

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.cache:
            return 0

        try:
            if hasattr(self.cache, "_redis"):
                # Use pipeline for better performance
                pipe = self.cache._redis.pipeline()
                for key in keys:
                    pipe.delete(key)
                results = await pipe.execute()
                return sum(results)
            else:
                # Fallback to individual deletes
                deleted_count = 0
                for key in keys:
                    if await self.delete(key):
                        deleted_count += 1
                return deleted_count
        except Exception as e:
            logger.warning(f"Cache delete_multi error: {e}")
            return 0


# Global async cache service instance
async_cache_service = AsyncCacheService()
