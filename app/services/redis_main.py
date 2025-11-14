import asyncio
import json
import signal
import sys
import redis
from typing import Optional, List
from dotenv import load_dotenv
import meilisearch

load_dotenv()

from .redis_base import client
from .redis_operations import perform_operation
from .poison_queue import process_poison_queue

from app.core.config import settings
from app.core.loggers import redis_logger as logger
from app.mails.email_service import email_service
from app.utils.telegram import send_telegram_msg
from app.database.get_session import AsyncSessionLocal
from app.services.session_service import (
    process_session_creation,
    process_session_update,
)
from app.cruds.activity_logs import activity_log_crud
from app.schemas.activity_logs import ActivityLogCreateSchema


class RedisMessageProcessor:
    def __init__(self, queue_names: List[str]):
        self.queue_names = queue_names
        self.running = True
        self.reconnect_delay = 5
        self.max_reconnect_attempts = 5
        self.reconnect_attempts = 0

    async def process_message(self, message: dict, queue_name: str):
        """Process a single message based on its queue type"""
        try:
            if queue_name == "notifications":
                operation = message.get("operation", "send_email")
                try:
                    if operation == "send_email":
                        await email_service.send_email(
                            recipients=message["data"]["to"],
                            subject=message["data"]["subject"],
                            salutation=message["data"]["salutation"],
                            content=message["data"]["body"],
                            cc=message.get("data", {}).get("cc", None),
                            bcc=message.get("data", {}).get("bcc", None),
                            reply_to=message.get("data", {}).get("reply_to", None),
                        )
                    elif operation == "welcome_email":
                        await email_service.send_welcome_email(
                            name=message["data"]["name"],
                            email=message["data"]["email"],
                            cc=message.get("data", {}).get("cc", None),
                            bcc=message.get("data", {}).get("bcc", None),
                            reply_to=message.get("data", {}).get("reply_to", None),
                        )
                    elif operation == "send_typed_email":
                        await email_service.send_typed_email(
                            recipients=message["data"]["to"],
                            subject=message["data"]["subject"],
                            html=message["data"]["body"],
                            cc=message.get("data", {}).get("cc", None),
                            bcc=message.get("data", {}).get("bcc", None),
                            reply_to=message.get("data", {}).get("reply_to", None),
                        )
                    else:
                        logger.error(f"Invalid operation: {operation}")
                        await process_poison_queue(queue_name, message)
                        return False
                except Exception as e:
                    logger.error(f"Failed to send email: {e}")
                    await process_poison_queue(queue_name, message)
                    return False
                return True

            elif queue_name == "telegram":
                try:
                    send_telegram_msg(message["data"]["message"])
                except Exception as e:
                    logger.error(f"Failed to send telegram message: {e}")
                    await process_poison_queue(queue_name, message)
                    return False
                return True

            elif queue_name == "sessions":
                operation = message.get("operation", "create")
                try:
                    if operation == "create":
                        await process_session_creation(message["data"])
                    elif operation == "update":
                        await process_session_update(message["data"])
                    else:
                        logger.error(f"Invalid session operation: {operation}")
                        await process_poison_queue(queue_name, message)
                        return False
                except Exception as e:
                    logger.error(f"Failed to process session queue: {e}")
                    await process_poison_queue(queue_name, message)
                    return False
                return True

            elif queue_name == "activity_logs":
                operation = message.get("operation", "create")
                data = message.get("data", {})
                try:
                    if operation == "create":
                        async with AsyncSessionLocal() as db:
                            await activity_log_crud.create(
                                db=db, obj_in=ActivityLogCreateSchema(**data)
                            )
                            logger.info(f"Activity log created successfully.")
                except Exception as e:
                    logger.error(f"Failed to create activity log: {e}")
                    await process_poison_queue(queue_name, message)
                    return False
                return True

            # Handle data operations
            if isinstance(message["data"], list):
                new_message = message.copy()
                for item in message["data"]:
                    new_message["data"] = item
                    if await perform_operation(new_message):
                        logger.info(
                            f"Successfully performed operation for {new_message}"
                        )
                    else:
                        await process_poison_queue(queue_name, new_message)
                        logger.info(f"Failed to perform operation for {new_message}")
                return True

            if isinstance(message["data"], dict):
                if await perform_operation(message):
                    logger.info(f"Successfully performed operation for {message}")
                    return True
                else:
                    await process_poison_queue(queue_name, message)
                    logger.info(f"Failed to perform operation for {message}")
                    return False

        except Exception as e:
            logger.error(f"Error processing message from {queue_name}: {e}")
            await process_poison_queue(queue_name, message)
            return False

    async def process_messages(self):
        """Main message processing loop with robust error handling"""
        while self.running:
            try:
                # Check Redis connection
                if not client.ping():
                    logger.error("Lost connection to Redis")
                    await asyncio.sleep(self.reconnect_delay)
                    continue

                # Wait for message with timeout
                result = client.brpop(self.queue_names, timeout=1)
                if not result:
                    continue

                _, json_message = result
                message = json.loads(json_message)
                queue_name = message["queue_name"]
                log_message = message.get("log", True)

                if log_message:
                    logger.info(f"Processing message from {queue_name}: {message}")
                await self.process_message(message, queue_name)

            except redis.ConnectionError as e:
                logger.error(f"Redis connection error: {e}")
                await asyncio.sleep(self.reconnect_delay)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in message processing: {e}")
                await asyncio.sleep(1)

    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info("Received shutdown signal. Cleaning up...")
        self.running = False
        try:
            client.close()
            logger.info("Redis connection closed")
        except:
            pass
        logger.info("Exiting...")
        sys.exit(0)


async def main():
    processor = RedisMessageProcessor(settings.QUEUE_NAMES.split(","))

    # Register signal handlers
    signal.signal(signal.SIGINT, processor.handle_shutdown)
    signal.signal(signal.SIGTERM, processor.handle_shutdown)

    logger.info("Starting Redis Message Processor")
    await processor.process_messages()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
