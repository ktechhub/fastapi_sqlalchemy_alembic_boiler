import time
import redis
import redis.asyncio as redis_async
import json
from typing import Optional

from ..core.config import settings
from ..core.loggers import app_logger as logger


client = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    username=settings.REDIS_USERNAME,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
    db=0,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
    health_check_interval=30,  # Check connection health every 30 seconds
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE: start keepalive after 1 second of idle
        2: 1,  # TCP_KEEPINTVL: send keepalive every 1 second
        3: 3,  # TCP_KEEPCNT: send 3 keepalive probes before considering connection dead
    },
)

# Global async Redis client with connection pooling
_async_client: Optional[redis_async.Redis] = None


async def get_async_redis_client() -> redis_async.Redis:
    """Get or create async Redis client with connection pooling and health checks

    The client is configured with:
    - Connection pooling (max 20 connections)
    - Socket keepalive to prevent idle connection timeouts
    - Health check interval to detect dead connections
    - Automatic retry on timeout
    """
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
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,  # Check connection health every 30 seconds
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE: start keepalive after 1 second of idle
                2: 1,  # TCP_KEEPINTVL: send keepalive every 1 second
                3: 3,  # TCP_KEEPCNT: send 3 keepalive probes before considering connection dead
            },
        )
    return _async_client


async def close_async_redis_client():
    """Close async Redis client connection"""
    global _async_client
    if _async_client:
        try:
            await _async_client.close()
        except Exception as e:
            logger.warning(f"Error closing Redis client: {e}")
        _async_client = None
