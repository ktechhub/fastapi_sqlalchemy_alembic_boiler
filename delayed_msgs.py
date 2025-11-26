import json
import time
import asyncio
import os
import redis
import redis.asyncio as redis_async
import logging
import signal
import sys
from typing import Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("delayed_msgs_processor")


class DelayedMessageProcessor:
    def __init__(self):
        self.client: Optional[redis_async.Redis] = None
        self.running = True
        self.reconnect_delay = 5
        self.max_reconnect_attempts = 5
        self.reconnect_attempts = 0
        self.processed_streams: Dict[str, str] = (
            {}
        )  # Track last processed ID per stream
        self.logged_messages: set = set()  # Track already logged messages to avoid spam

    async def connect_redis(self) -> bool:
        """Establish Redis connection with retry logic"""
        try:
            self.client = redis_async.Redis(
                host=os.environ.get("REDIS_HOST", "localhost"),
                port=int(os.environ.get("REDIS_PORT", 6379)),
                username=os.environ.get("REDIS_USERNAME", "default"),
                password=os.environ.get("REDIS_PASSWORD", ""),
                decode_responses=True,
                db=0,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test the connection
            await self.client.ping()
            self.reconnect_attempts = 0
            logger.info("Successfully connected to Redis")
            return True
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            return False

    async def _get_ready_delayed_messages(self, stream_name: str) -> List[tuple]:
        """
        Get delayed messages from a stream that are ready to be processed.
        Only returns messages with timestamp-based IDs (delayed messages).
        Immediate messages (auto-generated IDs) are ignored - they're handled by main consumer.

        Args:
            stream_name: Name of the Redis stream

        Returns:
            List of (message_id, message_data) tuples for delayed messages only
        """
        try:
            current_timestamp_ms = int(time.time() * 1000)
            # Read messages with IDs from 0 to current timestamp
            # Stream IDs are in format: timestamp-sequence
            messages = await self.client.xrange(
                stream_name,
                min="-",  # Start from beginning
                max=f"{current_timestamp_ms}",  # Up to current time
                count=100,  # Process up to 100 messages at a time
            )

            # Filter to only include messages with timestamp-based IDs (delayed messages)
            # Immediate messages have auto-generated IDs that don't match timestamp format
            delayed_messages = []
            for message_id, message_data in messages:
                message_id_str = (
                    message_id.decode() if isinstance(message_id, bytes) else message_id
                )

                # Check if this is a timestamp-based ID (delayed message)
                # Format: timestamp-sequence (e.g., "1764148853563-0")
                try:
                    parts = message_id_str.split("-")
                    if len(parts) == 2:
                        timestamp_part = int(parts[0])
                        sequence_part = int(parts[1])
                        # If timestamp is reasonable (not too far in past/future), it's a delayed message
                        # Immediate messages have auto-generated IDs that are usually much smaller
                        # Delayed messages have timestamps that are close to current time when ready
                        if (
                            timestamp_part > 1000000000000
                        ):  # After year 2001 (timestamp in ms)
                            delayed_messages.append((message_id, message_data))
                except (ValueError, IndexError):
                    # Not a timestamp-based ID, skip it (it's an immediate message)
                    continue

            return delayed_messages
        except Exception as e:
            logger.error(f"Error reading delayed messages from {stream_name}: {e}")
            return []

    async def process_delayed_messages(self):
        """Process delayed messages from Redis Streams with robust error handling"""
        while self.running:
            try:
                if not self.client:
                    if not await self.connect_redis():
                        logger.warning(
                            f"Retrying connection in {self.reconnect_delay} seconds..."
                        )
                        await asyncio.sleep(self.reconnect_delay)
                        continue

                # Test connection
                try:
                    await self.client.ping()
                except:
                    if not await self.connect_redis():
                        await asyncio.sleep(self.reconnect_delay)
                        continue

                # Get all stream keys (streams are named: queue_name:stream)
                # We need to find streams that might have delayed messages
                # For now, we'll scan for streams matching the pattern
                stream_pattern = "*:stream"
                cursor = 0
                stream_names = []

                # Scan for stream keys
                while True:
                    cursor, keys = await self.client.scan(
                        cursor, match=stream_pattern, count=100
                    )
                    stream_names.extend([k for k in keys if k.endswith(":stream")])
                    if cursor == 0:
                        break

                if not stream_names:
                    await asyncio.sleep(10)
                    continue

                # Process each stream for delayed messages
                for stream_name in stream_names:
                    try:
                        # Get ready delayed messages (those with timestamp <= now)
                        ready_messages = await self._get_ready_delayed_messages(
                            stream_name
                        )

                        if not ready_messages:
                            continue

                        # Process each ready message
                        for message_id, message_data in ready_messages:
                            try:
                                # Parse message
                                data_str = (
                                    message_data.get("data", "{}")
                                    if isinstance(message_data, dict)
                                    else (
                                        message_data.get(b"data", b"{}").decode()
                                        if isinstance(message_data.get(b"data"), bytes)
                                        else "{}"
                                    )
                                )

                                if isinstance(data_str, bytes):
                                    data_str = data_str.decode()

                                message = json.loads(data_str)

                                # Only process messages that have delay_until field (delayed messages)
                                # Immediate messages don't have this field and should be ignored
                                if "delay_until" not in message:
                                    # This is an immediate message, skip it - main consumer handles it
                                    continue

                                original_queue_name = message.get("queue_name")

                                if not original_queue_name:
                                    logger.warning(
                                        f"Message {message_id} missing queue_name, skipping"
                                    )
                                    # Delete the message from stream
                                    await self.client.xdel(stream_name, message_id)
                                    continue

                                # The message is already in the stream with the correct queue name
                                # The main consumer will pick it up automatically via XREADGROUP
                                # We just log it once to indicate it's ready, then let the main consumer handle it

                                message_key = f"{stream_name}:{message_id}"
                                if message_key not in self.logged_messages:
                                    logger.info(
                                        f"Delayed message {message_id} is ready for queue {original_queue_name}"
                                    )
                                    self.logged_messages.add(message_key)

                                    # Clean up old logged messages to prevent memory growth
                                    # Keep only last 1000 logged message keys
                                    if len(self.logged_messages) > 1000:
                                        # Remove oldest entries (simple approach: clear and rebuild)
                                        self.logged_messages = set(
                                            list(self.logged_messages)[-500:]
                                        )

                                # Note: We don't delete the message here - it will be consumed
                                # by the main consumer group. The message ID timestamp ensures
                                # it's only readable when the time comes.

                            except json.JSONDecodeError as e:
                                logger.error(
                                    f"Failed to decode delayed message {message_id}: {e}"
                                )
                                # Delete malformed message
                                await self.client.xdel(stream_name, message_id)
                            except Exception as e:
                                logger.error(
                                    f"Error processing delayed message {message_id}: {e}"
                                )

                    except redis.RedisError as e:
                        logger.error(
                            f"Redis error processing stream {stream_name}: {e}"
                        )
                        await asyncio.sleep(1)
                        continue
                    except Exception as e:
                        logger.error(
                            f"Unexpected error processing stream {stream_name}: {e}"
                        )
                        await asyncio.sleep(1)
                        continue

                await asyncio.sleep(1)

            except redis.ConnectionError as e:
                logger.error(f"Redis connection lost: {e}")
                self.client = None
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                await asyncio.sleep(5)

    async def close(self):
        """Close Redis connection"""
        if self.client:
            try:
                await self.client.aclose()  # Use aclose() instead of close() for async client
                logger.info("Redis connection closed")
            except:
                pass

    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info("Received shutdown signal. Cleaning up...")
        self.running = False
        # Note: async cleanup will happen when event loop closes
        logger.info("Exiting...")
        sys.exit(0)


async def main():
    processor = DelayedMessageProcessor()

    # Register signal handlers
    signal.signal(signal.SIGINT, processor.handle_shutdown)
    signal.signal(signal.SIGTERM, processor.handle_shutdown)

    logger.info("Starting Delayed Message Processor (Redis Streams)")
    try:
        await processor.process_delayed_messages()
    finally:
        await processor.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
