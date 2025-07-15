#!/usr/bin/env python3
"""
Test script to demonstrate the caching system functionality
"""

import asyncio
import json
from datetime import datetime


# Mock the necessary imports for demonstration
class MockRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value
        return True

    def delete(self, key):
        if key in self.data:
            del self.data[key]
            return 1
        return 0

    def keys(self, pattern):
        return [k for k in self.data.keys() if pattern.replace("*", "") in k]


# Mock cache service for testing
class MockCacheService:
    def __init__(self):
        self.client = MockRedis()
        self.enabled = True
        self.ttl = 1800

        # Define model dependencies
        self.model_dependencies = {
            "role": ["user", "permission", "role_permission", "user_role"],
            "user": ["role", "user_role", "activity_log", "verification_code"],
            "permission": ["role", "role_permission"],
            "role_permission": ["role", "permission"],
            "user_role": ["user", "role"],
            "activity_log": ["user"],
            "verification_code": ["user"],
        }

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        sorted_params = sorted(kwargs.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        return f"{prefix}:{param_str}"

    def get(self, key: str):
        if not self.enabled:
            return None

        cached_data = self.client.get(key)
        if cached_data:
            return json.loads(cached_data)
        return None

    def set(self, key: str, value, ttl=None):
        if not self.enabled:
            return False

        serialized_value = json.dumps(value, default=str)
        self.client.setex(key, ttl or self.ttl, serialized_value)
        return True

    def delete_pattern(self, pattern: str) -> bool:
        if not self.enabled:
            return False

        keys = self.client.keys(pattern)
        if keys:
            for key in keys:
                self.client.delete(key)
            print(f"Deleted {len(keys)} cache keys matching pattern: {pattern}")
            return True
        return False

    def invalidate_model_cache_with_dependencies(self, model_name: str) -> bool:
        if not self.enabled:
            return False

        models_to_invalidate = self._get_models_to_invalidate(model_name)

        for model in models_to_invalidate:
            pattern = f"{model}:*"
            self.delete_pattern(pattern)

        return True

    def _get_models_to_invalidate(self, model_name: str):
        models_to_invalidate = {model_name}

        # Add direct dependencies
        if model_name in self.model_dependencies:
            models_to_invalidate.update(self.model_dependencies[model_name])

        # Add reverse dependencies
        for dependent_model, dependencies in self.model_dependencies.items():
            if model_name in dependencies:
                models_to_invalidate.add(dependent_model)

        return models_to_invalidate

    def get_list_cache_key(self, model_name: str, **filters) -> str:
        return self._generate_cache_key(f"{model_name}:list", **filters)

    def cache_list_result(self, model_name: str, result, **filters) -> bool:
        key = self.get_list_cache_key(model_name, **filters)
        return self.set(key, result, self.ttl)

    def get_cached_list(self, model_name: str, **filters):
        key = self.get_list_cache_key(model_name, **filters)
        return self.get(key)


# Mock CRUD class
class MockCRUD:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.cache_service = MockCacheService()

    async def get_multi_with_cache(self, **filters):
        # Try to get from cache first
        cached_result = self.cache_service.get_cached_list(self.model_name, **filters)
        if cached_result:
            print(f"Using cached data for {self.model_name} list")
            return cached_result

        # Simulate database query
        print(f"Cache miss for {self.model_name} list, fetching from database")
        result = {
            "data": [{"id": 1, "name": f"test_{self.model_name}"}],
            "total_count": 1,
        }

        # Cache the result
        self.cache_service.cache_list_result(self.model_name, result, **filters)

        return result

    def invalidate_cache_with_dependencies(self):
        return self.cache_service.invalidate_model_cache_with_dependencies(
            self.model_name
        )


async def test_caching_system():
    print("=== Testing Caching System ===\n")

    # Create CRUD instances
    role_crud = MockCRUD("role")
    user_crud = MockCRUD("user")
    permission_crud = MockCRUD("permission")

    print("1. First request - should miss cache and fetch from DB")
    result1 = await role_crud.get_multi_with_cache(skip=0, limit=10, sort="name:asc")
    print(f"Result: {result1}\n")

    print("2. Second request with same parameters - should hit cache")
    result2 = await role_crud.get_multi_with_cache(skip=0, limit=10, sort="name:asc")
    print(f"Result: {result2}\n")

    print("3. Request with different parameters - should miss cache")
    result3 = await role_crud.get_multi_with_cache(skip=10, limit=10, sort="name:asc")
    print(f"Result: {result3}\n")

    print("4. Request for users - should miss cache")
    result4 = await user_crud.get_multi_with_cache(skip=0, limit=10)
    print(f"Result: {result4}\n")

    print("5. Invalidate role cache with dependencies")
    role_crud.invalidate_cache_with_dependencies()
    print()

    print("6. Request roles again - should miss cache (was invalidated)")
    result5 = await role_crud.get_multi_with_cache(skip=0, limit=10, sort="name:asc")
    print(f"Result: {result5}\n")

    print(
        "7. Request users again - should miss cache (was invalidated due to dependency)"
    )
    result6 = await user_crud.get_multi_with_cache(skip=0, limit=10)
    print(f"Result: {result6}\n")

    print("=== Cache System Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_caching_system())
