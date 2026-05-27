"""SF Group Manager — in-memory state (warns)."""
from __future__ import annotations
from collections import defaultdict


class GroupManagerState:
    def __init__(self) -> None:
        # warns[chat_id][user_id] = count
        self._warns: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    def add_warn(self, chat_id: int, user_id: int) -> int:
        self._warns[chat_id][user_id] += 1
        return self._warns[chat_id][user_id]

    def get_warns(self, chat_id: int, user_id: int) -> int:
        return self._warns[chat_id][user_id]

    def reset_warns(self, chat_id: int, user_id: int) -> None:
        self._warns[chat_id][user_id] = 0

    def remove_warn(self, chat_id: int, user_id: int) -> int:
        current = self._warns[chat_id][user_id]
        if current > 0:
            self._warns[chat_id][user_id] -= 1
        return self._warns[chat_id][user_id]
