"""
Central webhook server for all installed sub-bots.

When WEBHOOK_HOST is set, each sub-bot registers its webhook at:
    {WEBHOOK_HOST}/sub/{bot_id}

This module maintains a registry of (aiogram Bot, Dispatcher) pairs
and routes incoming updates to the correct dispatcher.

Usage (in main.py _run_webhook):
    from runtime.webhook_server import add_routes_to_app
    add_routes_to_app(app)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    from aiogram import Bot, Dispatcher

logger = logging.getLogger(__name__)

_registry: dict[int, tuple["Bot", "Dispatcher"]] = {}


async def _handle_sub_webhook(request: web.Request) -> web.Response:
    from aiogram.types import Update

    try:
        bot_id = int(request.match_info["bot_id"])
    except (KeyError, ValueError):
        return web.Response(status=400, text="bad bot_id")

    entry = _registry.get(bot_id)
    if not entry:
        logger.warning("[webhook_server] Update for unknown bot_id=%s", bot_id)
        return web.Response(status=404, text="bot not registered")

    aiogram_bot, dp = entry
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot=aiogram_bot, update=update)
    except Exception as exc:
        logger.error("[webhook_server] Error processing update for bot_id=%s: %s", bot_id, exc)
        return web.Response(status=500, text="error")

    return web.Response(status=200, text="ok")


def add_routes_to_app(app: web.Application) -> None:
    """Register the /sub/{bot_id} route on an existing aiohttp app."""
    app.router.add_post("/sub/{bot_id}", _handle_sub_webhook)
    logger.info("[webhook_server] Sub-bot webhook routes registered.")


def register_bot(bot_id: int, bot: "Bot", dp: "Dispatcher") -> None:
    _registry[bot_id] = (bot, dp)
    logger.info("[webhook_server] Registered bot_id=%s", bot_id)


def unregister_bot(bot_id: int) -> None:
    _registry.pop(bot_id, None)
    logger.info("[webhook_server] Unregistered bot_id=%s", bot_id)
