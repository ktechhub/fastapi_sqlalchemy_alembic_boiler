import time
import redis
import json

from .redis_base import client
from ..core.loggers import redis_logger as logger


def redis_lpush(message: dict, delay_seconds: int = 0):
    """
    Push a message to a list in Redis.

    Args:
        message (str, dict, list): The message to push to the list.
        delay_seconds (int): The number of seconds to delay the message.

    Returns:
        None
    """
    queue_name = message["queue_name"]

    if delay_seconds > 0:
        delay_timestamp = int(time.time()) + delay_seconds
        delayed_datetime = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(delay_timestamp)
        )
        message["delay_until"] = delayed_datetime
        client.zadd(f"{queue_name}-delayed", {json.dumps(message): delay_timestamp})
        logger.info(
            f"Pushed {message} to {queue_name} with delay of {delay_seconds} seconds"
        )
    else:
        client.lpush(queue_name, json.dumps(message))
        logger.info(f"Pushed {message} to {queue_name}.")
