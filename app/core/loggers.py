import logging
import os
import sys
import time
import meilisearch
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from .config import settings


class TimedRotatingFileHandlerWithSize(TimedRotatingFileHandler):
    """
    Custom handler that combines time-based and size-based rotation.
    Rotates logs based on both time intervals and file size.
    """

    def __init__(
        self,
        filename,
        when="D",
        interval=1,
        backupCount=0,
        encoding=None,
        maxBytes=0,
        delay=False,
        utc=False,
        atTime=None,
    ):
        super().__init__(
            filename,
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            utc=utc,
            atTime=atTime,
        )
        self.maxBytes = maxBytes

    def shouldRollover(self, record):
        """
        Determine if rollover should occur based on both time and size.
        """
        # Check time-based rollover
        if super().shouldRollover(record):
            return True

        # Check size-based rollover
        if self.maxBytes > 0:
            try:
                if os.path.getsize(self.baseFilename) >= self.maxBytes:
                    return True
            except OSError:
                pass

        return False


class SetupLogger:
    """
    A logging class that logs messages to rotating file handlers and optionally to Meilisearch.
    Supports both size-based and time-based log rotation.
    Meilisearch integration is only enabled if a valid meili_client is provided.
    """

    def __init__(
        self,
        logger_name,
        log_file,
        meili_client=None,
        meili_index=None,
        use_size_rotation=True,
        use_time_rotation=True,
        max_bytes=5 * 1024 * 1024,  # 5MB
        backup_count=3,
        when="D",  # Daily rotation
        interval=1,
        time_backup_count=7,
    ):
        """
        Initializes the logger.
        :param logger_name: Name of the logger
        :param log_file: Path to the log file
        :param meili_client: Optional Meilisearch client instance
        :param meili_index: Optional Meilisearch index name
        :param use_size_rotation: Whether to use size-based rotation
        :param use_time_rotation: Whether to use time-based rotation
        :param max_bytes: Maximum bytes per file for size rotation
        :param backup_count: Number of backup files for size rotation
        :param when: When to rotate for time rotation ('S', 'M', 'H', 'D', 'W', 'midnight')
        :param interval: Interval for time rotation
        :param time_backup_count: Number of backup files for time rotation
        """
        # Ensure the logs directory exists
        if not os.path.exists("logs"):
            os.makedirs("logs")

        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)

        # Log format
        log_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s: %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        self.logger.addHandler(console_handler)

        # Size-based rotating file handler
        if use_size_rotation and not use_time_rotation:
            size_handler = RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count
            )
            size_handler.setFormatter(log_format)
            self.logger.addHandler(size_handler)

        # Time-based rotating file handler with size limit
        if use_time_rotation:
            time_handler = TimedRotatingFileHandlerWithSize(
                log_file,
                when=when,
                interval=interval,
                backupCount=time_backup_count,
                encoding="utf-8",
                maxBytes=max_bytes if use_size_rotation else 0,
            )
            time_handler.setFormatter(log_format)
            self.logger.addHandler(time_handler)

        # Meilisearch setup (optional)
        self.meili_enabled = meili_client is not None and meili_index is not None
        if self.meili_enabled:
            self.meili_client = meili_client
            self.meili_index = meili_client.index(meili_index)
            # Ensure timestamp is filterable
            self.meili_index.update_filterable_attributes(
                ["timestamp", "level", "service", "logger_name"]
            )

    def _log_to_meilisearch(self, level, message):
        """
        Logs the message to Meilisearch if enabled.
        """
        if not self.meili_enabled:
            return

        log_entry = {
            "id": f"{int(time.time() * 1000)}-{level}-{settings.SERVICE_NAME}",  # Unique ID using timestamp
            "timestamp": int(time.time()),  # UNIX timestamp
            "level": level,
            "message": message,
            "service": settings.SERVICE_NAME,
            "logger_name": self.logger.name,
        }
        self.meili_index.add_documents([log_entry])

    def info(self, message):
        self.logger.info(message)
        self._log_to_meilisearch("INFO", message)

    def warning(self, message):
        self.logger.warning(message)
        self._log_to_meilisearch("WARNING", message)

    def error(self, message):
        self.logger.error(message)
        self._log_to_meilisearch("ERROR", message)

    def debug(self, message):
        self.logger.debug(message)
        self._log_to_meilisearch("DEBUG", message)

    def critical(self, message):
        self.logger.critical(message)
        self._log_to_meilisearch("CRITICAL", message)


# Create Meilisearch client if configured
meili_client = None
if hasattr(settings, "MEILI_SEARCH_URL") and hasattr(settings, "MEILI_SEARCH_API_KEY"):
    meili_client = meilisearch.Client(
        getattr(settings, "MEILI_SEARCH_URL"), getattr(settings, "MEILI_SEARCH_API_KEY")
    )

# Create Base loggers with both rotation types
app_logger = SetupLogger(
    "app_logger",
    "logs/app_logger.log",
    meili_client,
    "logs",
    use_size_rotation=True,
    use_time_rotation=True,
    time_backup_count=3,  # Keep only 3 days of logs
)
db_logger = SetupLogger(
    "db_logger",
    "logs/db_logger.log",
    meili_client,
    "logs",
    use_size_rotation=True,
    use_time_rotation=True,
    time_backup_count=3,  # Keep only 3 days of logs
)
security_logger = SetupLogger(
    "security_logger",
    "logs/security_logger.log",
    meili_client,
    "logs",
    use_size_rotation=True,
    use_time_rotation=True,
    time_backup_count=3,  # Keep only 3 days of logs
)
scheduler_logger = SetupLogger(
    "scheduler_logger",
    "logs/scheduler_logger.log",
    meili_client,
    "logs",
    use_size_rotation=True,
    use_time_rotation=True,
    time_backup_count=3,  # Keep only 3 days of logs
)
redis_logger = SetupLogger(
    "redis_logger",
    "logs/redis_logger.log",
    meili_client,
    "logs",
    use_size_rotation=True,
    use_time_rotation=True,
    time_backup_count=3,  # Keep only 3 days of logs
)
