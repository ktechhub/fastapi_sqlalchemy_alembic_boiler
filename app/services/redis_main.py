import asyncio
import json
import signal
import sys
import time
import redis
import os
import socket
from typing import Optional, List, Dict, Tuple
from dotenv import load_dotenv
import meilisearch

load_dotenv()

from .redis_base import get_async_redis_client
from .redis_operations import perform_operation
from .poison_queue import process_poison_queue
from .stream_consumer_groups import (
    initialize_consumer_groups,
    claim_pending_messages,
    get_pending_messages,
)

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
    def __init__(self, queue_names: List[str], consumer_group: str = "main-group"):
        self.queue_names = queue_names
        self.consumer_group = consumer_group
        # Generate unique consumer name (hostname + pid)
        hostname = socket.gethostname()
        pid = os.getpid()
        self.consumer_name = f"{hostname}-{pid}"
        self.running = True
        self.reconnect_delay = 5
        self.max_reconnect_attempts = 5
        self.reconnect_attempts = 0
        self.async_client: Optional[redis.asyncio.Redis] = None
        self.pending_claim_interval = 60  # Check for pending messages every 60 seconds

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

    async def _get_async_client(self) -> redis.asyncio.Redis:
        """Get or create async Redis client"""
        if self.async_client is None:
            self.async_client = await get_async_redis_client()
        return self.async_client

    async def _acknowledge_message(self, stream_name: str, message_id: str) -> bool:
        """Acknowledge a processed message"""
        try:
            client = await self._get_async_client()
            await client.xack(stream_name, self.consumer_group, message_id)
            return True
        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")
            return False

    async def _process_pending_messages(self) -> None:
        """Process pending messages (messages that were read but not acknowledged)"""
        try:
            for queue_name in self.queue_names:
                stream_name = f"{queue_name}:stream"
                # Claim pending messages that have been idle for more than 60 seconds
                # This is for messages from other consumers that failed
                claimed = await claim_pending_messages(
                    stream_name=stream_name,
                    group_name=self.consumer_group,
                    consumer_name=self.consumer_name,
                    min_idle_time=60000,  # 60 seconds
                    count=10,
                )

                if not claimed or len(claimed) == 0:
                    continue

                logger.info(
                    f"Processing {len(claimed)} claimed pending messages from {stream_name}"
                )
                # xclaim returns a list of (message_id, message_data) tuples directly
                # Not nested like xreadgroup results
                for message_id, message_data in claimed:
                    try:
                        message_id_str = (
                            message_id.decode()
                            if isinstance(message_id, bytes)
                            else message_id
                        )

                        # Check if message is scheduled for the future (delayed message)
                        try:
                            message_timestamp_ms = int(message_id_str.split("-")[0])
                            current_timestamp_ms = int(time.time() * 1000)

                            if message_timestamp_ms > current_timestamp_ms:
                                # Message is still scheduled for the future, skip it
                                logger.debug(
                                    f"Skipping future-dated pending message {message_id_str}"
                                )
                                continue
                        except (ValueError, IndexError):
                            # If ID format is unexpected, process it anyway
                            pass

                        # Parse message - handle both bytes and string formats
                        if isinstance(message_data, dict):
                            data_str = message_data.get("data", "{}")
                        else:
                            # Handle bytes format
                            data_bytes = message_data.get(b"data", b"{}")
                            data_str = (
                                data_bytes.decode()
                                if isinstance(data_bytes, bytes)
                                else str(data_bytes)
                            )

                        message = json.loads(data_str)
                        message["queue_name"] = queue_name

                        # Process message
                        success = await self.process_message(message, queue_name)

                        if success:
                            # Acknowledge successful processing
                            await self._acknowledge_message(stream_name, message_id_str)
                        else:
                            logger.warning(
                                f"Failed to process pending message {message_id_str}, will retry later"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error processing claimed message {message_id}: {e}"
                        )
        except Exception as e:
            logger.error(f"Error processing pending messages: {e}")

    async def process_messages(self):
        """Main message processing loop with Redis Streams and acknowledgements"""
        # Initialize consumer groups
        await initialize_consumer_groups(self.queue_names, self.consumer_group)
        logger.info(
            f"Initialized consumer groups for queues: {self.queue_names}, consumer: {self.consumer_name}"
        )

        # Start background task for processing pending messages
        pending_task = asyncio.create_task(self._periodic_pending_check())

        while self.running:
            try:
                client = await self._get_async_client()

                # Check Redis connection
                await client.ping()

                # Prepare streams for XREADGROUP
                # Read BOTH pending messages ("0") and new messages (">") in parallel
                # This ensures we process both:
                # 1. Pending messages that are now ready (delayed messages that were skipped)
                # 2. New messages (including new delayed messages)

                # Read pending messages first (messages we've seen before but didn't acknowledge)
                # Use "0" to read our own pending messages
                pending_streams = {
                    f"{queue_name}:stream": "0" for queue_name in self.queue_names
                }
                try:
                    pending_results = await client.xreadgroup(
                        groupname=self.consumer_group,
                        consumername=self.consumer_name,
                        streams=pending_streams,
                        count=10,
                        block=100,  # Short block for pending messages
                    )
                except Exception as e:
                    logger.debug(f"Error reading pending messages: {e}")
                    pending_results = None

                # Read new messages (messages never seen by this consumer group)
                # Use ">" to read new messages
                new_streams = {
                    f"{queue_name}:stream": ">" for queue_name in self.queue_names
                }
                try:
                    new_results = await client.xreadgroup(
                        groupname=self.consumer_group,
                        consumername=self.consumer_name,
                        streams=new_streams,
                        count=10,
                        block=(
                            900 if pending_results else 1000
                        ),  # Adjust block time based on pending results
                    )
                except Exception as e:
                    logger.debug(f"Error reading new messages: {e}")
                    new_results = None

                # Combine results - process pending first, then new
                results = []
                if pending_results:
                    pending_count = sum(len(msgs) for _, msgs in pending_results)
                    results.extend(pending_results)
                    if pending_count > 0:
                        logger.debug(f"Read {pending_count} pending messages")
                if new_results:
                    new_count = sum(len(msgs) for _, msgs in new_results)
                    results.extend(new_results)
                    if new_count > 0:
                        logger.debug(f"Read {new_count} new messages")

                if not results:
                    continue

                # Process each stream's messages
                for stream_name, messages in results:
                    # Extract queue name from stream name (remove ":stream" suffix)
                    queue_name = (
                        stream_name.decode()
                        if isinstance(stream_name, bytes)
                        else stream_name
                    )
                    queue_name = queue_name.replace(":stream", "")

                    for message_id, message_data in messages:
                        message_id_str = (
                            message_id.decode()
                            if isinstance(message_id, bytes)
                            else message_id
                        )

                        try:
                            # Check if message is scheduled for the future (delayed message)
                            # Stream IDs are in format: timestamp-sequence (e.g., "1234567890-0")
                            try:
                                message_timestamp_ms = int(message_id_str.split("-")[0])
                                current_timestamp_ms = int(time.time() * 1000)

                                if message_timestamp_ms > current_timestamp_ms:
                                    # Message is scheduled for the future, skip it
                                    # It will be processed when its time comes
                                    delay_seconds = (
                                        message_timestamp_ms - current_timestamp_ms
                                    ) / 1000
                                    logger.debug(
                                        f"Skipping future-dated message {message_id_str} "
                                        f"(scheduled for {message_timestamp_ms}, current: {current_timestamp_ms}, "
                                        f"delay: {delay_seconds:.1f}s)"
                                    )
                                    # Don't acknowledge it - let it stay in PEL for later processing
                                    # When we read with "0" next time, we'll check again if it's ready
                                    continue
                                else:
                                    # Message is ready (timestamp <= current time)
                                    logger.debug(
                                        f"Message {message_id_str} is ready "
                                        f"(scheduled: {message_timestamp_ms}, current: {current_timestamp_ms})"
                                    )
                            except (ValueError, IndexError):
                                # If ID format is unexpected, process it anyway
                                pass

                            # Parse message - handle both bytes and string formats
                            if isinstance(message_data, dict):
                                data_str = message_data.get("data", "{}")
                            else:
                                # Handle bytes format
                                data_bytes = message_data.get(b"data", b"{}")
                                data_str = (
                                    data_bytes.decode()
                                    if isinstance(data_bytes, bytes)
                                    else str(data_bytes)
                                )

                            message = json.loads(data_str)
                            message["queue_name"] = queue_name
                            log_message = message.get("log", True)

                            if log_message:
                                logger.info(
                                    f"Processing message from {queue_name} (ID: {message_id_str}): {message}"
                                )

                            # Process message
                            success = await self.process_message(message, queue_name)

                            if success:
                                # Acknowledge successful processing
                                await self._acknowledge_message(
                                    stream_name, message_id_str
                                )
                                if log_message:
                                    logger.info(
                                        f"Successfully processed and acknowledged message {message_id_str}"
                                    )
                            else:
                                logger.warning(
                                    f"Failed to process message {message_id_str}, will retry via pending list"
                                )
                                # Message will remain in PEL (Pending Entry List) for retry

                        except json.JSONDecodeError as e:
                            logger.error(
                                f"Failed to decode message {message_id_str}: {e}"
                            )
                            # Acknowledge malformed messages to prevent reprocessing
                            await self._acknowledge_message(stream_name, message_id_str)
                        except Exception as e:
                            logger.error(
                                f"Unexpected error processing message {message_id_str}: {e}"
                            )
                            # Don't acknowledge on error - let it stay in PEL for retry

            except redis.ConnectionError as e:
                logger.error(f"Redis connection error: {e}")
                self.async_client = None  # Reset client to force reconnection
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                logger.error(f"Unexpected error in message processing: {e}")
                await asyncio.sleep(1)

        # Cancel pending task on shutdown
        pending_task.cancel()
        try:
            await pending_task
        except asyncio.CancelledError:
            pass

    async def _periodic_pending_check(self):
        """Periodically check and process pending messages"""
        while self.running:
            try:
                await asyncio.sleep(self.pending_claim_interval)
                await self._process_pending_messages()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic pending check: {e}")

    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info("Received shutdown signal. Cleaning up...")
        self.running = False
        # Note: async client cleanup will happen when event loop closes
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
