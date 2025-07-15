import json
import time
import asyncio
import os
import redis
import logging
import signal
import sys
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("delayed_msgs_processor")


class DelayedMessageProcessor:
    def __init__(self):
        self.client: Optional[redis.StrictRedis] = None
        self.running = True
        self.reconnect_delay = 5
        self.max_reconnect_attempts = 5
        self.reconnect_attempts = 0

    def connect_redis(self) -> bool:
        """Establish Redis connection with retry logic"""
        try:
            self.client = redis.StrictRedis(
                host=os.environ.get("REDIS_HOST"),
                port=os.environ.get("REDIS_PORT"),
                username=os.environ.get("REDIS_USERNAME"),
                password=os.environ.get("REDIS_PASSWORD"),
                decode_responses=True,
                db=0,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test the connection
            self.client.ping()
            self.reconnect_attempts = 0
            logger.info("Successfully connected to Redis")
            return True
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            return False

    async def process_delayed_messages(self):
        """Process delayed messages with robust error handling"""
        while self.running:
            try:
                if not self.client or not self.client.ping():
                    if not self.connect_redis():
                        logger.warning(
                            f"Retrying connection in {self.reconnect_delay} seconds..."
                        )
                        await asyncio.sleep(self.reconnect_delay)
                        continue

                current_timestamp = int(time.time())
                delayed_queues = self.client.keys("*-delayed")

                if not delayed_queues:
                    await asyncio.sleep(10)
                    continue

                for delayed_queue in delayed_queues:
                    try:
                        while True:
                            message = self.client.zrangebyscore(
                                delayed_queue, 0, current_timestamp, start=0, num=1
                            )
                            if not message:
                                break

                            message_data = json.loads(message[0])
                            original_queue_name = message_data["queue_name"]

                            # Use pipeline for atomic operations
                            pipe = self.client.pipeline()
                            pipe.lpush(original_queue_name, json.dumps(message_data))
                            pipe.zrem(delayed_queue, message[0])
                            pipe.execute()

                            logger.info(
                                f"Moved delayed message {message_data} back to {original_queue_name}"
                            )

                    except redis.RedisError as e:
                        logger.error(
                            f"Redis error processing queue {delayed_queue}: {e}"
                        )
                        await asyncio.sleep(1)
                        continue
                    except Exception as e:
                        logger.error(
                            f"Unexpected error processing queue {delayed_queue}: {e}"
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

    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info("Received shutdown signal. Cleaning up...")
        self.running = False
        if self.client:
            try:
                self.client.close()
                logger.info("Redis connection closed")
            except:
                pass
        logger.info("Exiting...")
        sys.exit(0)


async def main():
    processor = DelayedMessageProcessor()

    # Register signal handlers
    signal.signal(signal.SIGINT, processor.handle_shutdown)
    signal.signal(signal.SIGTERM, processor.handle_shutdown)

    logger.info("Starting Delayed Message Processor")
    await processor.process_delayed_messages()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
