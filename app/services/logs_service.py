import os
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from app.core.config import settings


class LogService:
    """
    A service class for reading and managing logs from log files.
    Provides the same interface as MeiliSearchService for compatibility.
    """

    def __init__(self, logs_dir: str = "logs"):
        """
        Initialize the service with a logs directory.
        :param logs_dir: Path to the logs directory
        """
        self.logs_dir = Path(logs_dir)
        if not self.logs_dir.exists():
            self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _parse_log_line(self, line: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Parse a single log line into a structured log entry.
        Format: %(asctime)s - %(name)s - %(levelname)s: %(message)s
        Example: 2025-10-27 08:45:01,223 - app_logger - INFO: Starting the application
        """
        if not line.strip():
            return None

        # Pattern to match: YYYY-MM-DD HH:MM:SS,mmm - logger_name - LEVEL: message
        pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (\w+): (.+)"
        match = re.match(pattern, line.strip())

        if not match:
            return None

        timestamp_str, logger_name, level, message = match.groups()

        # Convert timestamp string to datetime then to unix timestamp
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
            timestamp = int(dt.timestamp())
        except ValueError:
            return None

        # Normalize service name to match schema allowed values
        service_name = self._normalize_service_name(settings.SERVICE_NAME)

        # Generate a unique ID from timestamp, level, and logger name
        log_id = f"{int(dt.timestamp() * 1000)}-{level}-{service_name}"

        return {
            "id": log_id,
            "timestamp": timestamp,
            "timestamp_readable": dt.isoformat(),
            "level": level,
            "message": message,
            "service": service_name,
            "logger_name": logger_name,
        }

    def _normalize_service_name(self, service_name: str) -> str:
        """
        Normalize service name to match schema allowed values.
        Maps variations like 'mt_dev_api_v2' to 'mt_api_v2'.
        """
        if not service_name:
            return "mt_api_v2"

        service_lower = service_name.lower()

        # Map common variations to schema-allowed values
        service_mapping = {
            "mt_dev_api_v2": "mt_api_v2",
            "mt_api_v2": "mt_api_v2",
            "mediatranscribe": "mt_api_v2",  # Common alias
            "auth": "auth",
            "logs": "logs",
            "analytics": "analytics",
            "messaging_layer": "messaging_layer",
        }

        # Check exact match first
        if service_lower in service_mapping:
            return service_mapping[service_lower]

        # Check if it contains 'mt_api_v2' or variations
        if "mt" in service_lower and "api" in service_lower and "v2" in service_lower:
            return "mt_api_v2"

        # Return mapped value or default to 'mt_api_v2' if not found
        return service_mapping.get(service_lower, "mt_api_v2")

    def _read_all_logs(self) -> List[Dict[str, Any]]:
        """
        Read all log files from the logs directory and parse them.
        Includes rotated log files with various formats:
        - Date-based: *.log.YYYY-MM-DD (e.g., app_logger.log.2025-10-16)
        - Numeric: *.log.1, *.log.2, etc.
        - Current: *.log
        """
        all_logs = []

        # Get all .log files in the logs directory (including rotated ones)
        # Pattern matches:
        # - *.log (current files)
        # - *.log.* (rotated files: date-based like .2025-10-16 or numeric like .1, .2)
        log_files = []
        for pattern in ["*.log", "*.log.*"]:
            log_files.extend(self.logs_dir.glob(pattern))

        # Remove duplicates and filter out directories
        log_files = [f for f in set(log_files) if f.is_file()]

        # Sort by modification time (oldest first) to maintain chronological order
        # This ensures logs appear in the correct time sequence
        log_files = sorted(log_files, key=lambda x: x.stat().st_mtime)

        # Process each log file
        for log_file in log_files:
            try:
                # Skip empty files
                if log_file.stat().st_size == 0:
                    continue

                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        log_entry = self._parse_log_line(line, log_file)
                        if log_entry:
                            all_logs.append(log_entry)
            except (IOError, UnicodeDecodeError, OSError, PermissionError) as e:
                # Skip files that can't be read
                continue

        return all_logs

    def _filter_logs(
        self,
        logs: List[Dict[str, Any]],
        filters: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Apply filters to logs. Filters are in the format used by MeiliSearch.
        Example: "timestamp >= 1234567890 AND level = 'INFO'"
        """
        if not filters:
            return logs

        filtered_logs = logs.copy()

        # Parse filter string (simple implementation)
        # Handle AND conditions
        conditions = filters.split(" AND ")

        for condition in conditions:
            condition = condition.strip()

            # Handle timestamp comparisons
            if "timestamp >=" in condition:
                match = re.search(r"timestamp >= (\d+)", condition)
                if match:
                    min_timestamp = int(match.group(1))
                    filtered_logs = [
                        log
                        for log in filtered_logs
                        if log.get("timestamp", 0) >= min_timestamp
                    ]

            if "timestamp <=" in condition:
                match = re.search(r"timestamp <= (\d+)", condition)
                if match:
                    max_timestamp = int(match.group(1))
                    filtered_logs = [
                        log
                        for log in filtered_logs
                        if log.get("timestamp", 0) <= max_timestamp
                    ]

            # Handle exact matches
            if " = " in condition:
                field_match = re.search(r"(\w+) = '([^']+)'", condition)
                if field_match:
                    field, value = field_match.groups()
                    filtered_logs = [
                        log
                        for log in filtered_logs
                        if str(log.get(field, "")).lower() == value.lower()
                    ]

            # Handle IN conditions
            if " IN " in condition:
                # Handle both formats: "id IN ['id1', 'id2']" and "id IN [id1, id2]"
                match = re.search(r"id IN \[(.*?)\]", condition)
                if not match:
                    # Try without brackets: "id IN id1,id2"
                    match = re.search(r"id IN (.+)", condition)
                if match:
                    ids_str = match.group(1)
                    # Extract IDs, handling quotes
                    ids = [
                        id.strip().strip("'\"")
                        for id in re.split(r",\s*", ids_str)
                        if id.strip()
                    ]
                    filtered_logs = [
                        log for log in filtered_logs if log.get("id") in ids
                    ]

        return filtered_logs

    def _search_logs(
        self, logs: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """
        Search logs by message, level, service, or logger_name.
        """
        if not query:
            return logs

        query_lower = query.lower()
        matched_logs = []

        for log in logs:
            # Search in message, level, service, logger_name
            if (
                query_lower in str(log.get("message", "")).lower()
                or query_lower in str(log.get("level", "")).lower()
                or query_lower in str(log.get("service", "")).lower()
                or query_lower in str(log.get("logger_name", "")).lower()
            ):
                matched_logs.append(log)

        return matched_logs

    def _sort_logs(
        self, logs: List[Dict[str, Any]], sort: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Sort logs based on sort parameters.
        Format: ["timestamp:desc", "level:asc"]
        """
        if not sort:
            # Default sort by timestamp descending
            return sorted(logs, key=lambda x: x.get("timestamp", 0), reverse=True)

        # Apply sorting (last sort param takes precedence)
        sorted_logs = logs.copy()

        for sort_param in sort:
            if ":" in sort_param:
                field, direction = sort_param.split(":")
                reverse = direction.lower() == "desc"

                sorted_logs = sorted(
                    sorted_logs,
                    key=lambda x: x.get(field, ""),
                    reverse=reverse,
                )

        return sorted_logs

    def search(
        self,
        query: str = "",
        filters: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        sort: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Perform a search query with optional filters.
        Returns a dict similar to MeiliSearch response format.
        """
        # Read all logs
        all_logs = self._read_all_logs()

        # Apply filters
        filtered_logs = self._filter_logs(all_logs, filters)

        # Apply search query
        searched_logs = self._search_logs(filtered_logs, query)

        # Apply sorting
        sorted_logs = self._sort_logs(searched_logs, sort)

        # Apply pagination
        total = len(sorted_logs)
        paginated_logs = sorted_logs[offset : offset + limit]

        return {
            "hits": paginated_logs,
            "estimatedTotalHits": total,
            "limit": limit,
            "offset": offset,
        }

    def get_one(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single log entry by ID.
        """
        all_logs = self._read_all_logs()
        for log in all_logs:
            if log.get("id") == document_id:
                return log
        return None

    def delete_one(self, document_id: str) -> Dict[str, Any]:
        """
        Delete a log entry by ID.
        Note: This is a no-op for file-based logs as we don't modify log files.
        In a real implementation, you might want to mark logs as deleted or move them.
        """
        # For file-based logs, deletion is not straightforward
        # We'll just return a success response
        return {"id": document_id, "status": "deleted"}

    def list_data(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        List logs with pagination.
        """
        return self.search(query="", limit=limit, offset=offset)
