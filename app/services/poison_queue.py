from .redis_push import redis_lpush
from ..core.loggers import redis_logger as logger
from ..core.config import settings


async def process_poison_queue(queue_name, message):
    retries = message.get("retries", 0)
    if retries >= settings.MAX_REDIS_QUEUE_RETRIES:
        poison_queue_name = f"{queue_name}-poison"
        message["queue_name"] = poison_queue_name
        redis_lpush(message)
        logger.info(f"Moved message to poison queue {poison_queue_name}: {message}")
    else:
        message["retries"] = retries + 1
        message["queue_name"] = queue_name
        redis_lpush(message)
        logger.info(
            f"Requeued message {message} for retry, retries={message['retries']}"
        )
    return True
