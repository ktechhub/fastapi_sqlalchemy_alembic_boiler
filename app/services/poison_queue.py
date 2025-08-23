from .redis_base import get_async_redis_client
from .redis_push import redis_push_async
from ..core.loggers import redis_logger as logger
from ..core.config import settings
import json
import time


async def process_poison_queue(queue_name, message, ttl=30 * 24 * 60 * 60):
    retries = message.get("retries", 0)
    if retries >= settings.MAX_REDIS_QUEUE_RETRIES:
        # Move to poison queue with TTL auto-deletion
        poison_queue_name = f"{queue_name}-poison"
        message["queue_name"] = poison_queue_name
        message["poisoned_at"] = time.time()

        redis_client = await get_async_redis_client()

        # Generate unique key for the poisoned message
        message_id = f"{poison_queue_name}:{int(time.time() * 1000)}"
        serialized_message = json.dumps(message)

        # Store with TTL - Redis will auto-delete
        await redis_client.setex(message_id, ttl, serialized_message)

        logger.info(f"Moved message to poison queue '{poison_queue_name}': {message}")

    else:
        message["retries"] = retries + 1
        message["queue_name"] = queue_name
        await redis_push_async(message)
        logger.info(
            f"Requeued message {message} for retry, retries={message['retries']}"
        )
    return True


async def get_poison_queue_messages(queue_name: str, limit: int = 100) -> list:
    """
    Get messages from poison queue (for monitoring/debugging purposes)

    Args:
        queue_name: Name of the original queue
        limit: Maximum number of messages to return

    Returns:
        List of poisoned messages
    """
    try:
        poison_queue_name = f"{queue_name}-poison"
        pattern = f"{poison_queue_name}:*"

        redis_client = await get_async_redis_client()

        # Get all keys matching the pattern
        cursor = 0
        keys = []
        while True:
            cursor, batch_keys = await redis_client.scan(
                cursor, match=pattern, count=100
            )
            keys.extend(batch_keys)
            if cursor == 0:
                break

        # Limit the results
        keys = keys[:limit]

        poisoned_messages = []
        for key in keys:
            try:
                # Get message and TTL
                message_data = await redis_client.get(key)
                ttl = await redis_client.ttl(key)

                if message_data:
                    message = json.loads(message_data)
                    message["key"] = key
                    message["ttl_seconds"] = ttl
                    message["days_until_expiry"] = max(0, ttl / (24 * 60 * 60))
                    poisoned_messages.append(message)

            except json.JSONDecodeError:
                logger.warning(f"Failed to decode poisoned message: {key}")
                continue

        return poisoned_messages

    except Exception as e:
        logger.error(f"Error getting poison queue messages: {e}")
        return []


async def delete_poison_queue(queue_name: str) -> bool:
    """
    Delete all messages from poison queue

    Args:
        queue_name: Name of the original queue

    Returns:
        True if successful, False otherwise
    """
    try:
        poison_queue_name = f"{queue_name}-poison"
        pattern = f"{poison_queue_name}:*"

        redis_client = await get_async_redis_client()

        # Get all keys matching the pattern
        cursor = 0
        keys_to_delete = []
        while True:
            cursor, batch_keys = await redis_client.scan(
                cursor, match=pattern, count=100
            )
            keys_to_delete.extend(batch_keys)
            if cursor == 0:
                break

        if keys_to_delete:
            # Delete all keys in batches
            deleted = 0
            batch_size = 100
            for i in range(0, len(keys_to_delete), batch_size):
                batch = keys_to_delete[i : i + batch_size]
                deleted += await redis_client.delete(*batch)

            logger.info(
                f"Deleted {deleted} messages from poison queue {poison_queue_name}"
            )
            return True
        else:
            logger.info(f"Poison queue {poison_queue_name} was already empty")
            return True

    except Exception as e:
        logger.error(f"Error deleting poison queue: {e}")
        return False
