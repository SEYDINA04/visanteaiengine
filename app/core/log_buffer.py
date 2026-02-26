"""
In-memory log buffer for GET /api/v1/log.

Stores recent log records (e.g. last 500) so the log endpoint can return them.
"""

import logging
from collections import deque
from typing import Any

# Max records to keep in memory
MAX_LOG_ENTRIES = 500

_log_buffer: deque[dict[str, Any]] = deque(maxlen=MAX_LOG_ENTRIES)


def add_record(record: dict[str, Any]) -> None:
    """Append a log record to the buffer."""
    _log_buffer.append(record)


def get_recent(limit: int = 100) -> list[dict[str, Any]]:
    """Return the most recent log entries (newest last)."""
    n = min(max(1, limit), len(_log_buffer))
    return list(_log_buffer)[-n:]


class BufferHandler(logging.Handler):
    """Logging handler that pushes formatted records to the in-memory buffer."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            add_record({
                "timestamp": record.created,
                "level": record.levelname,
                "logger": record.name,
                "message": msg,
            })
        except Exception:
            self.handleError(record)
