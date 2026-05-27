"""
BaseSourcePlugin — lifecycle contract every source must implement.

Each source's main.py instantiates a subclass and calls .run().
The bot_manager starts the source as an isolated subprocess via its entry point.
"""
from __future__ import annotations

import asyncio
import json
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
    Lifecycle:
        1. __init__  — load config, set up router
        2. on_startup()  — async setup (DB pools, caches, etc.)
        3. run()     — starts aiogram polling (blocking)
        4. on_shutdown() — async teardown (flush logs, close pools)
    """

    def __init__(self, token: str, bot_id: int, config: dict[str, Any]) -> None:
        self.token  = token
        self.bot_id = bot_id
        self.config = config
        self._setup_logging()

    # ── Overridable lifecycle hooks ───────────────────────────────────────────

    async def on_startup(self) -> None:
        """Called once before polling starts."""

    async def on_shutdown(self) -> None:
        """Called once after polling stops."""

    @abstractmethod
    def build_dispatcher(self):
        """Return a configured aiogram Dispatcher."""

    # ── Final run loop — do not override ─────────────────────────────────────

    def run(self) -> None:
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode

        bot = Bot(
            token=self.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dp = self.build_dispatcher()

        dp.startup.register(self.on_startup)
        dp.shutdown.register(self.on_shutdown)

        self._install_signal_handlers()

        logger.info("[bot_id=%s] Starting polling ...", self.bot_id)
        asyncio.run(dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()))
        logger.info("[bot_id=%s] Polling stopped.", self.bot_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _setup_logging(self) -> None:
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
