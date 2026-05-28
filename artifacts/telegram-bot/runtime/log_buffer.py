"""
Thread-safe circular log buffer — stores last N plain-text lines per bot_id.
Used by BotManager to capture in-process bot output for Live Logs display.
"""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from threading import Lock

_MAX_PER_BOT = 50


class LogBuffer:
    def __init__(self) -> None:
        self._data: dict[int, deque[str]] = {}
        self._lock = Lock()

    def push(self, bot_id: int, level: str, msg: str) -> None:
        ts = datetime.utcnow().strftime("%H:%M:%S")
        line = f"[{ts}] {level:<4} {msg}"
        with self._lock:
            if bot_id not in self._data:
                self._data[bot_id] = deque(maxlen=_MAX_PER_BOT)
            self._data[bot_id].append(line)

    def get(self, bot_id: int) -> list[str]:
        with self._lock:
            return list(self._data.get(bot_id, []))

    def get_for_bots(self, bot_ids: list[int], limit: int = 20) -> list[str]:
        result: list[str] = []
        with self._lock:
            for bid in bot_ids:
                for line in self._data.get(bid, []):
                    result.append(f"[bot_{bid}] {line}")
        return result[-limit:]

    def clear(self, bot_id: int) -> None:
        with self._lock:
            self._data.pop(bot_id, None)


class _BufferHandler(logging.Handler):
    """Logging handler that pushes records into a LogBuffer."""

    def __init__(self, bot_id: int, buffer: LogBuffer) -> None:
        super().__init__()
        self._bot_id = bot_id
        self._buffer = buffer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._buffer.push(
                self._bot_id,
                record.levelname[:4],
                record.getMessage(),
            )
        except Exception:
            pass


_instance: LogBuffer | None = None


def get_log_buffer() -> LogBuffer:
    global _instance
    if _instance is None:
        _instance = LogBuffer()
    return _instance


def attach_buffer_handler(bot_id: int) -> None:
    """Attach a buffer log handler to the bot.{bot_id} logger."""
    buf = get_log_buffer()
    lg = logging.getLogger(f"bot.{bot_id}")
    if not any(isinstance(h, _BufferHandler) for h in lg.handlers):
        handler = _BufferHandler(bot_id, buf)
        handler.setLevel(logging.DEBUG)
        lg.addHandler(handler)
        lg.propagate = True
