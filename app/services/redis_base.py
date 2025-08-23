import time
import redis
import redis.asyncio as redis_async
import json
from typing import Optional

from ..core.config import settings


client = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    username=settings.REDIS_USERNAME,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
    db=0,
)

# Global async Redis client with connection pooling
_async_client: Optional[redis_async.Redis] = None


async def get_async_redis_client() -> redis_async.Redis:
    """Get or create async Redis client with connection pooling"""
    global _async_client
    if _async_client is None:
        _async_client = redis_async.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            username=settings.REDIS_USERNAME,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            db=0,
            max_connections=20,  # Connection pool size
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={},
        )
    return _async_client


async def close_async_redis_client():
    """Close async Redis client connection"""
    global _async_client
    if _async_client:
        await _async_client.close()
        _async_client = None
