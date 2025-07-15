import json
import hashlib
from typing import Any, Optional, Dict, List, Set, Type
from datetime import datetime
import redis
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy import inspect

from ..core.config import settings
from ..core.loggers import app_logger as logger
from .redis_base import client as redis_client


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


class CacheService:
    """Global cache service for handling Redis caching operations"""

    def __init__(
        self,
        enabled: bool = settings.CACHE_ENABLED,
        ttl: int = settings.CACHE_TTL_MEDIUM,
    ):
        self.enabled = enabled
        self.client = redis_client
        self.ttl = ttl

        # Initialize empty dependencies - will be populated automatically
        self.model_dependencies = {}

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

        # print(f"Detected dependencies for {model_class.__name__}: {dependencies}")
        return dependencies

    def register_model_dependencies(self, model_name: str, dependencies: List[str]):
        """
        Register dependencies for a model

        Args:
            model_name: Name of the model
            dependencies: List of dependent model names
        """
        self.model_dependencies[model_name] = dependencies
        # print(f"Registered dependencies for {model_name}: {dependencies}")

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

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled:
            return None

        try:
            cached_data = self.client.get(key)
            if cached_data:
                # logger.debug(f"Cache hit for key: {key}")
                return json.loads(cached_data)
            # logger.debug(f"Cache miss for key: {key}")
            return None
        except (redis.ConnectionError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Use custom encoder for SQLAlchemy objects
            serialized_value = json.dumps(value, cls=SQLAlchemyJSONEncoder)
            ttl = ttl or self.ttl
            self.client.setex(key, ttl, serialized_value)
            # logger.debug(f"Cached data for key: {key} with TTL: {ttl}")
            return True
        except (redis.ConnectionError, TypeError) as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            result = self.client.delete(key)
            if result:
                print(f"Deleted cache key: {key}")
            return bool(result)
        except redis.ConnectionError as e:
            return False

    def delete_pattern(self, pattern: str) -> bool:
        """
        Delete all keys matching a pattern

        Args:
            pattern: Redis pattern (e.g., 'roles:*')

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            keys = self.client.keys(pattern)
            if keys:
                result = self.client.delete(*keys)
                print(f"Deleted {result} cache keys matching pattern: {pattern}")
                return True
            return False
        except redis.ConnectionError as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return False

    def invalidate_model_cache(self, model_name: str) -> bool:
        """
        Invalidate all cache entries for a specific model

        Args:
            model_name: Name of the model (e.g., 'roles', 'users')

        Returns:
            True if successful, False otherwise
        """
        pattern = f"{model_name}:*"
        return self.delete_pattern(pattern)

    def invalidate_model_cache_with_dependencies(self, model_name: str) -> bool:
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
                keys = self.client.keys(pattern)
                if keys:
                    result = self.client.delete(*keys)
                    print(f"Invalidated {result} cache keys for model: {model}")

            return True
        except redis.ConnectionError as e:
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

    def cache_list_result(
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
        return self.set(key, result, self.ttl)

    def get_cached_list(self, model_name: str, **filters) -> Optional[Dict[str, Any]]:
        """
        Get cached list result

        Args:
            model_name: Name of the model
            **filters: Filter parameters used for the query

        Returns:
            Cached result or None if not found
        """
        key = self.get_list_cache_key(model_name, **filters)
        return self.get(key)

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

    def cache_item_result(
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
        return self.set(key, result, self.ttl)

    def get_cached_item(
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
        return self.get(key)


# Global cache service instance
cache_service = CacheService()

"""
Example of how dependency-aware caching works:

1. When a Role is updated:
   - Role cache is invalidated
   - User cache is invalidated (because users have roles)
   - Permission cache is invalidated (because roles have permissions)
   - RolePermission cache is invalidated (because it links roles and permissions)
   - UserRole cache is invalidated (because it links users and roles)

2. When a User is updated:
   - User cache is invalidated
   - Role cache is invalidated (because users have roles)
   - UserRole cache is invalidated (because it links users and roles)
   - ActivityLog cache is invalidated (because logs reference users)
   - VerificationCode cache is invalidated (because codes belong to users)

3. When a Permission is updated:
   - Permission cache is invalidated
   - Role cache is invalidated (because roles have permissions)
   - RolePermission cache is invalidated (because it links roles and permissions)

This ensures that when any model changes, all related cached data is automatically
invalidated, preventing stale data from being served to clients.

Usage in CRUD classes:
- Use `get_multi_with_cache()` instead of `get_multi()` for listing operations
- Cache is automatically invalidated on create/update/delete operations
- Dependencies are automatically detected from SQLAlchemy relationships
- Manual dependency registration is also supported for complex cases
"""
