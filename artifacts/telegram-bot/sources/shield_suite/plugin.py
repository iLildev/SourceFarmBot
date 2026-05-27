"""
Shield Suite — Plugin class (lifecycle implementation).
"""
from __future__ import annotations

import logging
from typing import Any

from aiogram import Dispatcher

from runtime.plugin_base import BaseSourcePlugin
from sources.shield_suite.config import load_config
from sources.shield_suite.handlers import build_router
from sources.shield_suite.state import ShieldState

logger = logging.getLogger(__name__)


class ShieldSuitePlugin(BaseSourcePlugin):

    def __init__(self, token: str, bot_id: int, config: dict[str, Any]) -> None:
        merged_config = load_config(config)
        super().__init__(token=token, bot_id=bot_id, config=merged_config)
        self._state = ShieldState()

    async def on_startup(self) -> None:
        logger.info("[ShieldSuite bot_id=%s] Startup — config loaded.", self.bot_id)

    async def on_shutdown(self) -> None:
        logger.info("[ShieldSuite bot_id=%s] Shutdown — cleaning up.", self.bot_id)

    def build_dispatcher(self) -> Dispatcher:
        dp     = Dispatcher()
        router = build_router(self._state, self.config, self.bot_id)
        dp.include_router(router)
        return dp
