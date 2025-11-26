import time
import redis
import json
import asyncio
from typing import Dict, List, Optional
from collections import defaultdict

from .redis_base import client, get_async_redis_client
from app.core.loggers import redis_logger as logger

# Batch configuration
BATCH_SIZE = 50  # Number of messages to batch
BATCH_TIMEOUT = 5  # Seconds to wait before flushing batch
FLUSH_INTERVAL = 10  # Seconds between forced flushes

# Global batch storage
_message_batches: Dict[str, List[Dict]] = defaultdict(list)
_last_flush: Dict[str, float] = defaultdict(lambda: 0)
_flush_task: Optional[asyncio.Task] = None


def redis_lpush(message: dict, delay_seconds: int = 0) -> None:
    """
    Push a message to a Redis Stream (synchronous version for backward compatibility).

    Args:
        message (dict): The message to push to the stream.
        delay_seconds (int): The number of seconds to delay the message.

    Returns:
        None
    """
    queue_name = message["queue_name"]
    stream_name = f"{queue_name}:stream"

    if delay_seconds > 0:
        # For delayed messages, use timestamp-based ID
        delay_timestamp_ms = int((time.time() + delay_seconds) * 1000)
        delayed_datetime = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(delay_timestamp_ms / 1000)
        )
        message["delay_until"] = delayed_datetime
        # Use timestamp as stream ID for delayed messages
        stream_id = f"{delay_timestamp_ms}-0"
        client.xadd(stream_name, {"data": json.dumps(message)}, id=stream_id)
        logger.info(
            f"Pushed {message} to {queue_name} stream with delay of {delay_seconds} seconds (ID: {stream_id})"
        )
    else:
        # For immediate messages, use auto-generated ID
        stream_id = client.xadd(stream_name, {"data": json.dumps(message)})
        logger.info(f"Pushed {message} to {queue_name} stream (ID: {stream_id})")


async def redis_push_async(
    message: dict, delay_seconds: int = 0, log: bool = True
) -> None:
    """
    Push a message to a Redis Stream.

    Args:
        message (dict): The message to push to the stream.
        delay_seconds (int): The number of seconds to delay the message.
        log (bool): Whether to log the operation.
    """
    queue_name = message["queue_name"]
    stream_name = f"{queue_name}:stream"
    async_client = await get_async_redis_client()

    if delay_seconds > 0:
        # For delayed messages, use timestamp-based ID
        delay_timestamp_ms = int((time.time() + delay_seconds) * 1000)
        delayed_datetime = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(delay_timestamp_ms / 1000)
        )
        message["delay_until"] = delayed_datetime
        # Use timestamp as stream ID for delayed messages
        stream_id = f"{delay_timestamp_ms}-0"
        await async_client.xadd(
            stream_name, {"data": json.dumps(message)}, id=stream_id
        )
        if log:
            logger.info(
                f"Pushed {message} to {queue_name} stream with delay of {delay_seconds} seconds (ID: {stream_id})"
            )
    else:
        # For immediate messages, use auto-generated ID
        stream_id = await async_client.xadd(stream_name, {"data": json.dumps(message)})
        if log:
            logger.info(f"Pushed {message} to {queue_name} stream (ID: {stream_id})")


# New async methods with batching and connection pooling
async def _flush_batch_async(queue_name: str) -> None:
    """Flush a batch of messages to Redis Stream using async client"""
    if not _message_batches[queue_name]:
        return

    try:
        async_client = await get_async_redis_client()
        messages = _message_batches[queue_name]
        _message_batches[queue_name] = []
        stream_name = f"{queue_name}:stream"

        # Use pipeline for batch operations
        async with async_client.pipeline() as pipe:
            for message in messages:
                delay_seconds = message.get("delay_seconds", 0)
                if delay_seconds > 0:
                    # For delayed messages, use timestamp-based ID
                    delay_timestamp_ms = int((time.time() + delay_seconds) * 1000)
                    delayed_datetime = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(delay_timestamp_ms / 1000)
                    )
                    message["delay_until"] = delayed_datetime
                    stream_id = f"{delay_timestamp_ms}-0"
                    pipe.xadd(stream_name, {"data": json.dumps(message)}, id=stream_id)
                else:
                    # For immediate messages, use auto-generated ID
                    pipe.xadd(stream_name, {"data": json.dumps(message)})

            await pipe.execute()

        logger.info(f"Flushed {len(messages)} messages to {queue_name} stream")
        _last_flush[queue_name] = time.time()

    except Exception as e:
        logger.error(f"Error flushing batch for {queue_name}: {str(e)}")
        # Restore messages to batch on error
        _message_batches[queue_name].extend(messages)


async def _periodic_flush_async() -> None:
    """Periodically flush all batches using async client"""
    while True:
        try:
            current_time = time.time()
            for queue_name in list(_message_batches.keys()):
                # Flush if batch is full or timeout reached
                if (
                    len(_message_batches[queue_name]) >= BATCH_SIZE
                    or current_time - _last_flush[queue_name] >= BATCH_TIMEOUT
                ):
                    await _flush_batch_async(queue_name)

            await asyncio.sleep(FLUSH_INTERVAL)
        except Exception as e:
            logger.error(f"Error in periodic flush: {str(e)}")
            await asyncio.sleep(FLUSH_INTERVAL)


def _ensure_flush_task_async() -> None:
    """Ensure the periodic flush task is running"""
    global _flush_task
    if _flush_task is None or _flush_task.done():
        try:
            loop = asyncio.get_event_loop()
            _flush_task = loop.create_task(_periodic_flush_async())
        except RuntimeError:
            # No event loop, skip for now
            pass


async def redis_lpush_batched(message: dict, delay_seconds: int = 0) -> None:
    """
    Push a message to Redis with batching and async operations.

    Args:
        message (dict): The message to push to the list.
        delay_seconds (int): The number of seconds to delay the message.
    """
    queue_name = message["queue_name"]
    message["delay_seconds"] = delay_seconds

    # Add to batch
    _message_batches[queue_name].append(message)

    # Ensure flush task is running
    _ensure_flush_task_async()

    # Flush immediately if batch is full
    if len(_message_batches[queue_name]) >= BATCH_SIZE:
        await _flush_batch_async(queue_name)


async def flush_all_batches_async() -> None:
    """Force flush all pending batches"""
    for queue_name in list(_message_batches.keys()):
        await _flush_batch_async(queue_name)
