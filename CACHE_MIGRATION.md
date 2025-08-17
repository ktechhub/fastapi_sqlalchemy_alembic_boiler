# Cache System Migration: Sync to Async

## Overview

The caching system has been migrated from a synchronous Redis client to an asynchronous implementation using `aiocache`. This change resolves performance issues where cache operations were blocking the FastAPI event loop.

## What Changed

### 1. New Dependencies

Added `aiocache==0.12.2` to `requirements.txt` for async Redis operations.

### 2. New Async Cache Service

Created `app/services/async_cache_service.py` with the following features:
- **Async Operations**: All cache operations are now async and don't block the event loop
- **Dependency-Aware Invalidation**: Automatically detects and invalidates related model caches
- **SQLAlchemy Integration**: Handles SQLAlchemy model serialization
- **Configurable TTL**: Supports different cache durations
- **Error Handling**: Graceful fallback when Redis is unavailable

### 3. Updated Cache Mixin

Modified `app/cruds/cache_mixin.py`:
- **Async Methods**: All cache operations are now async
- **Automatic Dependency Detection**: Uses SQLAlchemy relationships to detect model dependencies
- **Enhanced Invalidation**: Added `invalidate_item_cache()` method for granular cache control

### 4. Updated CRUD Base Classes

Modified `app/cruds/activity_base.py`:
- **Async Cache Invalidation**: All cache invalidation calls are now async
- **Non-blocking Operations**: Cache operations no longer block other async tasks

## Key Benefits

### Performance Improvements
- **Non-blocking**: Cache operations don't block the FastAPI event loop
- **Concurrent Requests**: Multiple requests can be processed simultaneously
- **Better Resource Utilization**: More efficient use of server resources

### Enhanced Features
- **Automatic Dependency Detection**: No need to manually specify model relationships
- **Granular Cache Control**: Invalidate specific items or patterns
- **Better Error Handling**: Graceful degradation when Redis is unavailable

## Usage Examples

### Basic Caching in CRUD Classes

```python
from app.cruds.cache_mixin import CacheMixin

class CRUDUser(CacheMixin, CRUDBase[User, UserCreate, UserUpdate]):
    def __init__(self, model: Type[User]):
        super().__init__(model)
        # CacheMixin is automatically initialized with model dependencies

# Usage in your API endpoints
async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    # This will use cache if available, otherwise fetch from DB
    return await user_crud.get_multi_with_cache(db, skip=skip, limit=limit)
```

### Individual Item Caching

```python
# Get a single user with caching
user = await user_crud.get_with_cache(
    db=db, 
    identifier=user_uuid,
    eager_load=[User.roles, User.permissions]
)
```

### Manual Cache Invalidation

```python
# Invalidate all cache for a model
await user_crud.invalidate_cache()

# Invalidate cache for a specific item
await user_crud.invalidate_item_cache(identifier=user_uuid)

# Invalidate cache with dependencies (affects related models)
await user_crud.invalidate_cache_with_dependencies()
```

## Configuration

### Redis Settings

The async cache service uses the same Redis configuration as before:

```python
# In app/core/config.py
REDIS_HOST: str = "localhost"
REDIS_PORT: int = 6379
REDIS_PASSWORD: str = ""  # Optional
```

### Cache TTL Settings

```python
# Cache duration settings
CACHE_TTL_SHORT: int = 300    # 5 minutes
CACHE_TTL_MEDIUM: int = 1800  # 30 minutes
CACHE_TTL_LONG: int = 3600    # 1 hour
CACHE_TTL_VERY_LONG: int = 86400  # 24 hours
```

## Migration Guide

### For Existing Code

1. **No Changes Required**: Existing CRUD classes that inherit from `CacheMixin` will automatically use the async implementation.

2. **API Endpoints**: No changes needed in your API endpoints - the async operations are handled internally.

3. **Custom Cache Logic**: If you have custom cache logic, update it to use async methods:

```python
# Old (sync)
cache_service.set(key, value)

# New (async)
await cache_service.set(key, value)
```

### Testing

Run the test script to verify the async caching system:

```bash
python test_async_caching.py
```

## Dependency-Aware Caching

The system automatically detects model relationships and invalidates related caches:

### Example Dependencies
- **User** changes → invalidates User, Role, UserRole, ActivityLog, VerificationCode caches
- **Role** changes → invalidates Role, User, Permission, RolePermission, UserRole caches
- **Permission** changes → invalidates Permission, Role, RolePermission caches

### Manual Dependency Registration

For complex cases, you can manually register dependencies:

```python
from app.services.async_cache_service import async_cache_service

# Register dependencies for a custom model
async_cache_service.register_model_dependencies(
    "custom_model", 
    ["user", "role", "permission"]
)
```

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**: The system gracefully handles Redis connection failures and falls back to database queries.

2. **Cache Misses**: If you're seeing unexpected cache misses, check:
   - Cache key generation (filters, parameters)
   - TTL settings
   - Redis connectivity

3. **Performance Issues**: Monitor Redis performance and consider:
   - Increasing Redis memory
   - Adjusting TTL settings
   - Using Redis clustering for high load

### Debugging

Enable debug logging to see cache operations:

```python
import logging
logging.getLogger("app.services.async_cache_service").setLevel(logging.DEBUG)
```

## Performance Monitoring

Monitor cache performance with these metrics:
- Cache hit rate
- Redis memory usage
- Cache invalidation frequency
- Response times with/without cache

## Future Enhancements

Potential improvements:
- **Cache Warming**: Pre-populate cache with frequently accessed data
- **Distributed Caching**: Support for Redis clusters
- **Cache Analytics**: Detailed cache usage statistics
- **Smart Invalidation**: More intelligent cache invalidation strategies
