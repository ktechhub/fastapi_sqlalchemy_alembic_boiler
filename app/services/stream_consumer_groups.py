"""
Consumer group management utilities for Redis Streams.
Handles creation and management of consumer groups for reliable message processing.
"""

import time
import redis
import asyncio
from typing import List, Optional
from .redis_base import get_async_redis_client
from app.core.loggers import redis_logger as logger
from app.core.config import settings


async def ensure_consumer_group(
    stream_name: str, group_name: str, start_id: str = "0"
) -> bool:
    """
    Ensure a consumer group exists for a stream. Creates it if it doesn't exist.

    Args:
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group
        start_id: Starting ID for the group (default: "0" for all messages)

    Returns:
        True if group exists or was created, False on error
    """
    try:
        async_client = await get_async_redis_client()

        # Try to create the consumer group
        # This will fail if the group already exists, which is fine
        try:
            await async_client.xgroup_create(
                name=stream_name,
                groupname=group_name,
                id=start_id,
                mkstream=True,  # Create stream if it doesn't exist
            )
            logger.info(
                f"Created consumer group '{group_name}' for stream '{stream_name}'"
            )
            return True
        except redis.ResponseError as e:
            # BUSYGROUP means group already exists - that's fine
            if "BUSYGROUP" in str(e):
                logger.debug(
                    f"Consumer group '{group_name}' already exists for stream '{stream_name}'"
                )
                return True
            else:
                logger.error(f"Error creating consumer group: {e}")
                return False

    except Exception as e:
        logger.error(f"Unexpected error ensuring consumer group: {e}")
        return False


async def initialize_consumer_groups(
    queue_names: List[str], group_name: str = "main-group"
) -> None:
    """
    Initialize consumer groups for all specified queues.

    Args:
        queue_names: List of queue names to create consumer groups for
        group_name: Name of the consumer group (default: "main-group")
    """
    for queue_name in queue_names:
        stream_name = f"{queue_name}:stream"
        await ensure_consumer_group(stream_name, group_name)


async def get_pending_messages(
    stream_name: str,
    group_name: str,
    consumer_name: Optional[str] = None,
    count: int = 10,
) -> List:
    """
    Get pending messages from a consumer group (messages that were read but not acknowledged).

    Args:
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group
        consumer_name: Optional consumer name to filter by
        count: Maximum number of messages to return

    Returns:
        List of pending messages
    """
    try:
        async_client = await get_async_redis_client()

        if consumer_name:
            pending = await async_client.xpending_range(
                name=stream_name,
                groupname=group_name,
                min="-",
                max="+",
                count=count,
                consumername=consumer_name,
            )
        else:
            pending = await async_client.xpending_range(
                name=stream_name,
                groupname=group_name,
                min="-",
                max="+",
                count=count,
            )

        return pending
    except redis.ResponseError as e:
        # Redis-specific errors - check if stream/group doesn't exist
        error_str = str(e).lower()
        if (
            "no such key" in error_str
            or "no such group" in error_str
            or "0" in error_str
        ):
            # Stream or group doesn't exist yet, or no pending messages - not an error
            return []
        logger.warning(
            f"Redis error getting pending messages from '{stream_name}': {e}"
        )
        return []
    except Exception as e:
        error_str = str(e)
        if error_str == "0":
            # Exception message is just "0" - not a real error
            return []
        logger.error(f"Error getting pending messages from '{stream_name}': {e}")
        return []


async def claim_pending_messages(
    stream_name: str,
    group_name: str,
    consumer_name: str,
    min_idle_time: int = 60000,  # 60 seconds in milliseconds
    count: int = 10,
) -> List:
    """
    Claim pending messages that have been idle for too long.
    This is useful for recovering messages from failed consumers.

    Args:
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group
        consumer_name: Name of the consumer claiming the messages
        min_idle_time: Minimum idle time in milliseconds before claiming
        count: Maximum number of messages to claim

    Returns:
        List of claimed messages
    """
    try:
        async_client = await get_async_redis_client()

        # Get pending messages
        try:
            pending = await get_pending_messages(
                stream_name, group_name, count=count * 2
            )
        except Exception as e:
            # If we can't get pending messages, there's nothing to claim
            logger.debug(f"Could not get pending messages from '{stream_name}': {e}")
            return []

        if not pending or len(pending) == 0:
            return []

        # Filter messages that are idle long enough
        idle_message_ids = []
        current_time_ms = int(time.time() * 1000)

        for msg in pending:
            try:
                # msg format: (message_id, consumer_name, idle_time_ms, delivery_count)
                if not msg or len(msg) < 3:
                    continue
                message_id = msg[0]
                idle_time_ms = msg[2]

                if idle_time_ms >= min_idle_time:
                    idle_message_ids.append(message_id)
            except (IndexError, TypeError) as e:
                logger.debug(f"Invalid pending message format: {msg}, error: {e}")
                continue

        if not idle_message_ids:
            return []

        # Claim the messages
        # xclaim returns a list of (message_id, message_data) tuples
        try:
            claimed = await async_client.xclaim(
                name=stream_name,
                groupname=group_name,
                consumername=consumer_name,
                min_idle_time=min_idle_time,
                message_ids=idle_message_ids[:count],
            )
        except redis.ResponseError as e:
            # Redis-specific errors - check if it's a "no messages" type error
            error_str = str(e).lower()
            if "0" in error_str or "no such" in error_str or "empty" in error_str:
                # Not a real error, just no messages to claim
                return []
            logger.debug(f"Redis error claiming from '{stream_name}': {e}")
            return []
        except Exception as claim_error:
            # xclaim might raise an error if no messages to claim or other issues
            error_str = str(claim_error)
            if error_str == "0" or error_str == "0L":
                # Exception message is just "0" - not a real error
                return []
            logger.debug(f"No messages to claim from '{stream_name}': {claim_error}")
            return []

        # Handle different return formats
        if not claimed:
            return []

        # Check if it's a valid list
        if isinstance(claimed, (int, str)):
            # Sometimes returns "0" or 0 when no messages
            if str(claimed) == "0" or claimed == 0:
                return []
            logger.warning(
                f"Unexpected xclaim return type: {type(claimed)}, value: {claimed}"
            )
            return []

        # xclaim returns a list of (message_id, message_data) tuples directly
        # Not nested like xreadgroup
        if isinstance(claimed, list) and len(claimed) > 0:
            logger.info(
                f"Claimed {len(claimed)} pending messages from stream '{stream_name}'"
            )
            return claimed

        return []

    except redis.ResponseError as e:
        # Redis-specific errors (like "NOGROUP", "BUSYGROUP", etc.)
        error_str = str(e)
        # If it's just "0" or a no-messages error, don't log as error
        if error_str in ("0", "0L", "No such key"):
            return []
        # For other Redis errors, log as warning
        logger.warning(
            f"Redis error claiming pending messages from '{stream_name}': {e}"
        )
        return []
    except Exception as e:
        # Only log unexpected errors
        error_str = str(e)
        if error_str == "0":
            # Sometimes exceptions have "0" as message - not a real error
            return []
        logger.error(
            f"Unexpected error claiming pending messages from '{stream_name}': {e}"
        )
        return []


async def get_consumer_group_info(stream_name: str, group_name: str) -> Optional[dict]:
    """
    Get information about a consumer group.

    Args:
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group

    Returns:
        Dictionary with consumer group information or None on error
    """
    try:
        async_client = await get_async_redis_client()
        info = await async_client.xinfo_groups(stream_name)

        for group_info in info:
            if group_info["name"] == group_name:
                return group_info

        return None
    except Exception as e:
        logger.error(f"Error getting consumer group info: {e}")
        return None
