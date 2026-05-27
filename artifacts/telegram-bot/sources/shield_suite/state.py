"""
In-memory state for Shield Suite (per-bot, per-group).
Tracks: flood counters, warn counts, captcha pending, raid detection.
"""
from __future__ import annotations
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class FloodTracker:
    """Sliding-window message counter per user per chat."""
    window: int = 10          # seconds
    _timestamps: Deque[float] = field(default_factory=deque)

    def record(self) -> int:
        """Record a message and return current count in the window."""
        now = time.monotonic()
        self._timestamps.append(now)
        cutoff = now - self.window
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        return len(self._timestamps)


@dataclass
class RaidTracker:
    """Detects mass-join events (raid) per chat."""
    window: int = 60          # seconds
    _joins: Deque[float] = field(default_factory=deque)

    def record_join(self) -> int:
        now = time.monotonic()
        self._joins.append(now)
        cutoff = now - self.window
        while self._joins and self._joins[0] < cutoff:
            self._joins.popleft()
        return len(self._joins)


class ShieldState:
    """
    All mutable runtime state for one Shield Suite instance.
    Keys are (chat_id, user_id) or chat_id.
    """

    def __init__(self) -> None:
        # (chat_id, user_id) → FloodTracker
        self._flood:    dict[tuple[int, int], FloodTracker]  = defaultdict(FloodTracker)
        # (chat_id, user_id) → warn count
        self._warns:    dict[tuple[int, int], int]           = defaultdict(int)
        # (chat_id, user_id) → message_id of captcha question
        self._captcha:  dict[tuple[int, int], int]           = {}
        # chat_id → RaidTracker
        self._raid:     dict[int, RaidTracker]               = defaultdict(RaidTracker)
        # chat_id → raid_locked (bool)
        self._raid_lock: dict[int, bool]                     = defaultdict(bool)

    # Flood

    def flood_count(self, chat_id: int, user_id: int, threshold: int) -> bool:
        count = self._flood[(chat_id, user_id)].record()
        return count > threshold

    # Warns

    def add_warn(self, chat_id: int, user_id: int) -> int:
        self._warns[(chat_id, user_id)] += 1
        return self._warns[(chat_id, user_id)]

    def reset_warns(self, chat_id: int, user_id: int) -> None:
        self._warns[(chat_id, user_id)] = 0

    def get_warns(self, chat_id: int, user_id: int) -> int:
        return self._warns[(chat_id, user_id)]

    # Captcha

    def set_captcha(self, chat_id: int, user_id: int, msg_id: int) -> None:
        self._captcha[(chat_id, user_id)] = msg_id

    def pop_captcha(self, chat_id: int, user_id: int) -> int | None:
        return self._captcha.pop((chat_id, user_id), None)

    def has_captcha(self, chat_id: int, user_id: int) -> bool:
        return (chat_id, user_id) in self._captcha

    # Raid

    def raid_join(self, chat_id: int, threshold: int) -> bool:
        count = self._raid[chat_id].record_join()
        return count >= threshold

    def set_raid_lock(self, chat_id: int, locked: bool) -> None:
        self._raid_lock[chat_id] = locked

    def is_raid_locked(self, chat_id: int) -> bool:
        return self._raid_lock[chat_id]
