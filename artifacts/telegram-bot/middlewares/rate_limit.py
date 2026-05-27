"""
Rate-limiting middleware — sliding window per Telegram user ID.

Config (via env):
  RATE_LIMIT_MESSAGES  — max messages allowed in the window  (default 20)
  RATE_LIMIT_WINDOW    — window size in seconds             (default 60)
  RATE_LIMIT_BLOCK     — block duration in seconds          (default 60)
"""
import logging
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from config import RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW, RATE_LIMIT_BLOCK

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """Sliding-window rate limiter.  Works for both Message and CallbackQuery."""

    def __init__(self) -> None:
        self._timestamps: dict[int, deque] = defaultdict(deque)
        self._blocked_until: dict[int, float] = {}

    def _get_user_id(self, event: TelegramObject) -> int | None:
        if isinstance(event, (Message, CallbackQuery)):
            return event.from_user.id if event.from_user else None
        return None

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = self._get_user_id(event)
        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()

        # ── Check if still in block period ──
        blocked_until = self._blocked_until.get(user_id, 0)
        if now < blocked_until:
            remaining = int(blocked_until - now)
            if isinstance(event, Message):
                await event.answer(
                    f"⏳ أرسلت كثيراً! انتظر <b>{remaining}</b> ثانية.",
                    parse_mode="HTML",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    f"⏳ أسرعت! انتظر {remaining}ث.", show_alert=True
                )
            logger.warning("Rate-limited tg_id=%s (blocked %ss left)", user_id, remaining)
            return

        # ── Sliding-window check ──
        window = self._timestamps[user_id]
        cutoff  = now - RATE_LIMIT_WINDOW

        # Drop stale entries
        while window and window[0] < cutoff:
            window.popleft()

        window.append(now)

        if len(window) > RATE_LIMIT_MESSAGES:
            self._blocked_until[user_id] = now + RATE_LIMIT_BLOCK
            self._timestamps[user_id].clear()
            logger.warning(
                "Rate-limit BLOCK: tg_id=%s exceeded %d msgs/%ds — blocked %ds",
                user_id, RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW, RATE_LIMIT_BLOCK,
            )
            if isinstance(event, Message):
                await event.answer(
                    f"🚫 تجاوزت الحد المسموح به!\n"
                    f"انتظر <b>{RATE_LIMIT_BLOCK}</b> ثانية قبل الإرسال مجدداً.",
                    parse_mode="HTML",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    f"🚫 تجاوزت الحد! انتظر {RATE_LIMIT_BLOCK}ث.", show_alert=True
                )
            return

        return await handler(event, data)
