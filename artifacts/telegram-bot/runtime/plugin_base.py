"""
BaseSourcePlugin — lifecycle contract every source must implement.

Two run modes:
    run()        — subprocess entry point (keeps backward compatibility)
    run_async()  — in-process asyncio Task (used by BotManager)
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BaseSourcePlugin(ABC):
    """
    Lifecycle (in-process via run_async):
        1. __init__          — load config
        2. on_startup()      — async setup
        3. run_async()       — polling or webhook loop (blocking until cancelled)
        4. on_shutdown()     — async teardown

    Lifecycle (subprocess via run):
        Same as above but called from an isolated subprocess entry point.
    """

    def __init__(self, token: str, bot_id: int, config: dict[str, Any]) -> None:
        self.token  = token
        self.bot_id = bot_id
        self.config = config
        self.logger = logging.getLogger(f"bot.{bot_id}")

    # ── Overridable lifecycle hooks ───────────────────────────────────────────

    async def on_startup(self) -> None:
        """Called once before the bot starts processing updates."""

    async def on_shutdown(self) -> None:
        """Called once after the bot stops processing updates."""

    @abstractmethod
    def build_dispatcher(self):
        """Return a configured aiogram Dispatcher with all routers attached."""

    # ── In-process async run (called by BotManager) ───────────────────────────

    async def run_async(self) -> None:
        """
        Run the bot as an asyncio Task inside the main process.

        - Polling mode (default):   starts dp.start_polling()
        - Webhook mode (WEBHOOK_HOST set): sets webhook URL, registers with
          the central webhook server, then waits for cancellation.
        """
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from config import WEBHOOK_HOST

        aiogram_bot = Bot(
            token=self.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dp = self.build_dispatcher()
        dp.startup.register(self.on_startup)
        dp.shutdown.register(self.on_shutdown)

        if WEBHOOK_HOST:
            await self._run_webhook(aiogram_bot, dp, WEBHOOK_HOST)
        else:
            await self._run_polling(aiogram_bot, dp)

    async def _run_polling(self, aiogram_bot, dp) -> None:
        self.logger.info("[bot_id=%s] Starting polling (in-process) ...", self.bot_id)
        try:
            await dp.start_polling(
                aiogram_bot,
                allowed_updates=dp.resolve_used_update_types(),
            )
        except asyncio.CancelledError:
            self.logger.info("[bot_id=%s] Polling cancelled.", self.bot_id)
            raise
        finally:
            self.logger.info("[bot_id=%s] Polling stopped.", self.bot_id)

    async def _run_webhook(self, aiogram_bot, dp, webhook_host: str) -> None:
        from runtime.webhook_server import register_bot, unregister_bot

        path = f"/sub/{self.bot_id}"
        url  = f"{webhook_host.rstrip('/')}{path}"

        await aiogram_bot.set_webhook(
            url,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
        register_bot(self.bot_id, aiogram_bot, dp)
        self.logger.info("[bot_id=%s] Webhook set at %s", self.bot_id, url)

        await self.on_startup()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.logger.info("[bot_id=%s] Webhook bot cancelled.", self.bot_id)
            await self.on_shutdown()
            await aiogram_bot.delete_webhook()
            unregister_bot(self.bot_id)
            raise

    # ── Subprocess run (backward compat for existing main.py entry points) ────

    def run(self) -> None:
        """Start the bot in subprocess mode (long-polling, blocking)."""
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode

        self._setup_subprocess_logging()

        bot = Bot(
            token=self.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dp = self.build_dispatcher()
        dp.startup.register(self.on_startup)
        dp.shutdown.register(self.on_shutdown)
        self._install_signal_handlers()

        logger.info("[bot_id=%s] Starting polling (subprocess) ...", self.bot_id)
        asyncio.run(dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()))
        logger.info("[bot_id=%s] Polling stopped.", self.bot_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _setup_subprocess_logging(self) -> None:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=level,
            format=f"%(asctime)s | %(levelname)-8s | bot_id={self.bot_id} | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    @staticmethod
    def _install_signal_handlers() -> None:
        def _graceful(sig, frame):
            logger.info("Received signal %s — shutting down gracefully.", sig)
            sys.exit(0)

        signal.signal(signal.SIGTERM, _graceful)
        signal.signal(signal.SIGINT,  _graceful)
