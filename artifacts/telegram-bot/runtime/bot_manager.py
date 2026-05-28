"""
BotManager — manages installed bots as in-process asyncio Tasks.

In polling mode (WEBHOOK_HOST not set):
    Each bot runs dp.start_polling() as an asyncio Task.

In webhook mode (WEBHOOK_HOST set):
    Each bot sets its webhook URL and registers its (Bot, Dispatcher)
    with the central webhook server. The task waits for cancellation.

Lifecycle:
    start_bot()   → _launch() → asyncio.Task(plugin.run_async())
    stop_bot()    → task.cancel()
    restart_bot() → stop + start
    Watcher loop  → detects done tasks, restarts with back-off
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, update

from database.models import Bot
from database.session import async_session_maker
from runtime.crypto import decrypt_token

logger = logging.getLogger(__name__)

_BASE_DIR     = Path(__file__).resolve().parent.parent
_MAX_RESTARTS = 5
_BACKOFF_BASE = 5


@dataclass
class _BotTask:
    bot_id:     int
    source_id:  int
    task:       asyncio.Task
    restarts:   int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)


class BotManager:
    """Singleton — use `get_manager()` to obtain the instance."""

    def __init__(self) -> None:
        self._tasks: dict[int, _BotTask] = {}
        self._lock  = asyncio.Lock()
        self._watcher_task: asyncio.Task | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    async def start_bot(self, bot_id: int) -> bool:
        async with self._lock:
            entry = self._tasks.get(bot_id)
            if entry and not entry.task.done():
                logger.info("[manager] bot_id=%s already running", bot_id)
                return False

            bot = await self._load_bot(bot_id)
            if not bot:
                logger.error("[manager] bot_id=%s not found in DB", bot_id)
                return False

            if not bot.token_encrypted:
                logger.error("[manager] bot_id=%s has no encrypted token", bot_id)
                return False

            try:
                token = decrypt_token(bot.token_encrypted)
            except Exception as exc:
                logger.error("[manager] Failed to decrypt token for bot_id=%s: %s", bot_id, exc)
                return False

            task = await self._launch(bot_id, bot.source_id, token)
            if not task:
                return False

            self._tasks[bot_id] = _BotTask(
                bot_id=bot_id, source_id=bot.source_id, task=task
            )
            await self._persist_status(bot_id, is_running=True, pid=None)
            logger.info("[manager] bot_id=%s started (source=%s)", bot_id, bot.source_id)
            return True

    async def stop_bot(self, bot_id: int) -> bool:
        async with self._lock:
            entry = self._tasks.pop(bot_id, None)
            if not entry:
                return False

            if not entry.task.done():
                entry.task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(entry.task), timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

            try:
                from runtime.webhook_server import unregister_bot
                unregister_bot(bot_id)
            except Exception:
                pass

            await self._persist_status(bot_id, is_running=False, pid=None)
            logger.info("[manager] bot_id=%s stopped", bot_id)
            return True

    async def restart_bot(self, bot_id: int) -> bool:
        await self.stop_bot(bot_id)
        await asyncio.sleep(1)
        return await self.start_bot(bot_id)

    def is_running(self, bot_id: int) -> bool:
        entry = self._tasks.get(bot_id)
        return bool(entry and not entry.task.done())

    def status(self, bot_id: int) -> dict:
        entry = self._tasks.get(bot_id)
        if not entry:
            return {"running": False, "pid": None, "restarts": 0}
        return {
            "running":    not entry.task.done(),
            "pid":        None,
            "restarts":   entry.restarts,
            "started_at": entry.started_at.isoformat(),
        }

    def all_statuses(self) -> dict[int, dict]:
        return {bid: self.status(bid) for bid in self._tasks}

    # ── Watcher — restarts crashed tasks ─────────────────────────────────────

    async def start_watcher(self) -> None:
        if self._watcher_task and not self._watcher_task.done():
            return
        self._watcher_task = asyncio.create_task(self._watch_loop())
        logger.info("[manager] Watcher started.")

    async def _watch_loop(self) -> None:
        while True:
            await asyncio.sleep(10)
            crashed = [
                entry for entry in list(self._tasks.values())
                if entry.task.done()
            ]
            for entry in crashed:
                bid = entry.bot_id

                if entry.restarts >= _MAX_RESTARTS:
                    logger.error(
                        "[manager] bot_id=%s exceeded max restarts (%s) — giving up.",
                        bid, _MAX_RESTARTS,
                    )
                    self._tasks.pop(bid, None)
                    await self._persist_status(bid, is_running=False, pid=None)
                    continue

                exc = None
                if not entry.task.cancelled():
                    try:
                        exc = entry.task.exception()
                    except Exception:
                        pass

                logger.warning(
                    "[manager] bot_id=%s finished unexpectedly (exc=%s) — restart #%s in %ss",
                    bid, exc, entry.restarts + 1, _BACKOFF_BASE * (2 ** entry.restarts),
                )
                backoff = _BACKOFF_BASE * (2 ** entry.restarts)
                await asyncio.sleep(backoff)

                async with self._lock:
                    self._tasks.pop(bid, None)

                ok = await self.start_bot(bid)
                if ok and bid in self._tasks:
                    self._tasks[bid].restarts = entry.restarts + 1

    # ── Restore on platform restart ───────────────────────────────────────────

    async def restore_running_bots(self) -> None:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Bot).where(Bot.is_running == True)  # noqa: E712
            )
            bots = result.scalars().all()

        logger.info("[manager] Restoring %s previously-running bots ...", len(bots))
        for bot in bots:
            await self.start_bot(bot.id)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _launch(
        self, bot_id: int, source_id: int, token: str
    ) -> asyncio.Task | None:
        """Import plugin class and create an asyncio Task running plugin.run_async()."""
        from runtime.source_registry import get_plugin_class
        from runtime.log_buffer import attach_buffer_handler

        PluginClass = get_plugin_class(source_id)
        if not PluginClass:
            logger.error("[manager] No plugin class for source_id=%s", source_id)
            return None

        attach_buffer_handler(bot_id)

        try:
            plugin = PluginClass(token=token, bot_id=bot_id, config={})
            task = asyncio.create_task(
                plugin.run_async(),
                name=f"bot_{bot_id}",
            )
            return task
        except Exception as exc:
            logger.error("[manager] Failed to create task for bot_id=%s: %s", bot_id, exc)
            return None

    @staticmethod
    async def _load_bot(bot_id: int) -> Bot | None:
        async with async_session_maker() as session:
            result = await session.execute(select(Bot).where(Bot.id == bot_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def _persist_status(bot_id: int, is_running: bool, pid: int | None) -> None:
        async with async_session_maker() as session:
            await session.execute(
                update(Bot)
                .where(Bot.id == bot_id)
                .values(is_running=is_running, pid=pid)
            )
            await session.commit()


# ── Global singleton ──────────────────────────────────────────────────────────

_manager: BotManager | None = None


def get_manager() -> BotManager:
    global _manager
    if _manager is None:
        _manager = BotManager()
    return _manager
