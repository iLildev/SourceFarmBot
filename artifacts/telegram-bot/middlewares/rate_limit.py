"""
Rate-limiting middleware — sliding window per Telegram user ID.
Blocks survive bot restarts via the rate_limit_blocks DB table.

Config (via env):
  RATE_LIMIT_MESSAGES  — max messages allowed in the window  (default 20)
  RATE_LIMIT_WINDOW    — window size in seconds             (default 60)
  RATE_LIMIT_BLOCK     — block duration in seconds          (default 60)
"""
import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from config import RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW, RATE_LIMIT_BLOCK

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """Sliding-window rate limiter with DB-backed block persistence."""

    def __init__(self) -> None:
        self._timestamps: dict[int, deque]  = defaultdict(deque)
        self._blocked_until: dict[int, float] = {}   # user_id → Unix timestamp

    # ── DB persistence ────────────────────────────────────────────────────────

    async def restore_from_db(self) -> None:
        """Load active blocks from DB on startup. Call from main() on_startup."""
        from database.models import RateLimitBlock
        from database.session import async_session_maker
        from sqlalchemy import select, delete

        now = time.time()
        async with async_session_maker() as session:
            result  = await session.execute(select(RateLimitBlock))
            blocks  = result.scalars().all()
            expired = [b.user_id for b in blocks if b.blocked_until <= now]
            active  = {b.user_id: b.blocked_until for b in blocks if b.blocked_until > now}

            if expired:
                await session.execute(
                    delete(RateLimitBlock).where(RateLimitBlock.user_id.in_(expired))
                )
                await session.commit()

        self._blocked_until.update(active)
        if active:
            logger.info("Restored %d active rate-limit block(s) from DB.", len(active))

    def _persist_block(self, user_id: int, blocked_until: float) -> None:
        """Fire-and-forget: upsert block into DB."""
        asyncio.create_task(self._save_block(user_id, blocked_until))

    async def _save_block(self, user_id: int, blocked_until: float) -> None:
        try:
            from database.models import RateLimitBlock
            from database.session import async_session_maker
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            async with async_session_maker() as session:
                stmt = pg_insert(RateLimitBlock).values(
                    user_id=user_id, blocked_until=blocked_until
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["user_id"],
                    set_={"blocked_until": blocked_until},
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as exc:
            logger.warning("Failed to persist rate-limit block for user %s: %s", user_id, exc)

    async def _clear_block_from_db(self, user_id: int) -> None:
        try:
            from database.models import RateLimitBlock
            from database.session import async_session_maker
            from sqlalchemy import delete

            async with async_session_maker() as session:
                await session.execute(
                    delete(RateLimitBlock).where(RateLimitBlock.user_id == user_id)
                )
                await session.commit()
        except Exception:
            pass

    # ── Middleware logic ──────────────────────────────────────────────────────

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

        now = time.time()

        # ── Check active block ──
        blocked_until = self._blocked_until.get(user_id, 0)
        if now < blocked_until:
            remaining = int(blocked_until - now)
            if isinstance(event, Message):
                await event.answer(
                    f"⏳ أرسلت كثيراً! انتظر <b>{remaining}</b> ثانية.",
                    parse_mode="HTML",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(f"⏳ أسرعت! انتظر {remaining}ث.", show_alert=True)
            logger.warning("Rate-limited tg_id=%s (%ss left)", user_id, remaining)
            return

        # ── Expire old block entry ──
        if user_id in self._blocked_until and now >= self._blocked_until[user_id]:
            del self._blocked_until[user_id]
            asyncio.create_task(self._clear_block_from_db(user_id))

        # ── Sliding-window check ──
        window = self._timestamps[user_id]
        cutoff = now - RATE_LIMIT_WINDOW
        while window and window[0] < cutoff:
            window.popleft()
        window.append(now)

        if len(window) > RATE_LIMIT_MESSAGES:
            new_block = now + RATE_LIMIT_BLOCK
            self._blocked_until[user_id] = new_block
            self._timestamps[user_id].clear()
            self._persist_block(user_id, new_block)

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
                await event.answer(f"🚫 تجاوزت الحد! انتظر {RATE_LIMIT_BLOCK}ث.", show_alert=True)
            return

        return await handler(event, data)
