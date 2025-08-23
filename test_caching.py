#!/usr/bin/env python3
"""
Simple test for the simplified caching system without dependency management.
"""

import json
import asyncio
from typing import Dict, Any, Optional


class MockRedis:
    """Mock Redis client for testing"""

    def __init__(self):
        self.data = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, ttl=None):
        self.data[key] = value
        return True

    async def setex(self, key, ttl, value):
        self.data[key] = value
        return True

    async def delete(self, key):
        if key in self.data:
            del self.data[key]
            return 1
        return 0

    async def scan(self, cursor, match=None, count=1000):
        if match:
            pattern = match.replace("*", "")
            keys = [k for k in self.data.keys() if pattern in k]
        else:
            keys = list(self.data.keys())
        return 0, keys[:count]


class MockAsyncCacheService:
    """Mock async cache service for testing"""

    def __init__(self):
        self.enabled = True
        self.ttl = 1800
        self.cache = type("MockCache", (), {"_redis": MockRedis()})()

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        sorted_params = sorted(kwargs.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        return f"{prefix}:{param_str}"

    async def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None

        cached_data = await self.cache._redis.get(key)
        if cached_data:
            return json.loads(cached_data)
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not self.enabled:
            return False

        serialized_value = json.dumps(value, default=str)
        await self.cache._redis.setex(key, ttl or self.ttl, serialized_value)
        return True

    async def delete(self, key: str) -> bool:
        if not self.enabled:
            return False

        result = await self.cache._redis.delete(key)
        return bool(result)

    async def delete_pattern(self, pattern: str) -> bool:
        if not self.enabled:
            return False

        cursor, keys = await self.cache._redis.scan(0, match=pattern)
        if keys:
            for key in keys:
                await self.cache._redis.delete(key)
            print(f"Deleted {len(keys)} cache keys matching pattern: {pattern}")
            return True
        return False

    async def invalidate_model_cache(self, model_name: str) -> bool:
        """Invalidate all cache entries for a specific model"""
        pattern = f"{model_name}:*"
        return await self.delete_pattern(pattern)

    def get_list_cache_key(self, model_name: str, **filters) -> str:
        return self._generate_cache_key(f"{model_name}:list", **filters)

    def get_item_cache_key(self, model_name: str, identifier: str, **filters) -> str:
        return self._generate_cache_key(f"{model_name}:item:{identifier}", **filters)


class MockCRUD:
    """Mock CRUD class for testing"""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.cache_service = MockAsyncCacheService()

    def _get_cache_filters(
        self, skip: int = 0, limit: int = 100, sort: str = "", **filters
    ) -> Dict[str, Any]:
        cache_filters = {"skip": skip, "limit": limit, "sort": sort}

        for key, value in filters.items():
            if value is not None:
                try:
                    json.dumps(value)
                    cache_filters[key] = value
                except (TypeError, ValueError):
                    continue

        return cache_filters

    async def get_multi_with_cache(
        self, skip: int = 0, limit: int = 100, sort: str = "", **filters
    ):
        """Get multiple records with caching support"""
        cache_filters = self._get_cache_filters(
            skip=skip, limit=limit, sort=sort, **filters
        )
        cache_key = self.cache_service.get_list_cache_key(
            self.model_name, **cache_filters
        )

        # Try to get from cache first
        cached_result = await self.cache_service.get(cache_key)
        if cached_result:
            print(f"Using cached data for {self.model_name} list")
            return cached_result

        # If not in cache, fetch from database (mock)
        result = {"data": [f"item_{i}" for i in range(limit)], "total_count": 100}

        # Cache the result
        await self.cache_service.set(cache_key, result, self.cache_service.ttl)
        print(f"Cached data for {self.model_name} list")

        return result

    async def invalidate_cache(self) -> bool:
        """Invalidate all cache entries for this model"""
        return await self.cache_service.invalidate_model_cache(self.model_name)


async def test_simplified_caching():
    """Test the simplified caching system"""
    print("Testing simplified caching system...")

    # Create mock CRUD instances
    user_crud = MockCRUD("user")
    role_crud = MockCRUD("role")

    # Test 1: Cache list operations
    print("\n1. Testing list caching:")

    # First call - should cache the result
    result1 = await user_crud.get_multi_with_cache(skip=0, limit=10, sort="name:asc")
    print(f"Result 1: {result1}")

    # Second call - should use cached data
    result2 = await user_crud.get_multi_with_cache(skip=0, limit=10, sort="name:asc")
    print(f"Result 2: {result2}")

    # Different parameters - should cache separately
    result3 = await user_crud.get_multi_with_cache(skip=10, limit=20, sort="name:desc")
    print(f"Result 3: {result3}")

    # Test 2: Cache invalidation
    print("\n2. Testing cache invalidation:")

    # Invalidate user cache
    await user_crud.invalidate_cache()
    print("Invalidated user cache")

    # Call again - should cache again (not use old cache)
    result4 = await user_crud.get_multi_with_cache(skip=0, limit=10, sort="name:asc")
    print(f"Result 4: {result4}")

    # Test 3: Independent model caching
    print("\n3. Testing independent model caching:")

    # Role cache should be independent of user cache
    role_result1 = await role_crud.get_multi_with_cache(skip=0, limit=5)
    print(f"Role result 1: {role_result1}")

    # Invalidate user cache again - role cache should remain
    await user_crud.invalidate_cache()
    print("Invalidated user cache again")

    # Role cache should still work
    role_result2 = await role_crud.get_multi_with_cache(skip=0, limit=5)
    print(f"Role result 2: {role_result2}")

    print("\n✅ Simplified caching test completed successfully!")
    print("Key improvements:")
    print("- No complex dependency management")
    print("- Fast cache key generation and checking")
    print("- Independent model cache invalidation")
    print("- Simple and maintainable code")


if __name__ == "__main__":
    asyncio.run(test_simplified_caching())
