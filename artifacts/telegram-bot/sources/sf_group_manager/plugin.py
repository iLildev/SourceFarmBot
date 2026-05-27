"""SF Group Manager — Plugin lifecycle."""
from __future__ import annotations

import logging
from typing import Any

from aiogram import Dispatcher

from runtime.plugin_base import BaseSourcePlugin
from sources.sf_group_manager.config import load_config
from sources.sf_group_manager.handlers import build_router
from sources.sf_group_manager.state import GroupManagerState

logger = logging.getLogger(__name__)


class GroupManagerPlugin(BaseSourcePlugin):

    def __init__(self, token: str, bot_id: int, config: dict[str, Any]) -> None:
        merged = load_config(config)
        super().__init__(token=token, bot_id=bot_id, config=merged)
        self._state = GroupManagerState()

    async def on_startup(self) -> None:
        logger.info("[GroupManager bot_id=%s] Started.", self.bot_id)

    async def on_shutdown(self) -> None:
        logger.info("[GroupManager bot_id=%s] Shutting down.", self.bot_id)

    def build_dispatcher(self) -> Dispatcher:
        dp     = Dispatcher()
        router = build_router(self._state, self.config, self.bot_id)
        dp.include_router(router)
        return dp
