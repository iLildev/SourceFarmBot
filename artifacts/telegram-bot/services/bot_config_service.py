"""
Per-bot configuration service.

Config is stored as JSON in Bot.bot_config.
Each source has a schema of toggleable boolean settings.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select

from database.models import Bot
from database.session import async_session_maker

logger = logging.getLogger(__name__)


# ── Schema: source_id → {key: (display_label, default)} ──────────────────────

_SCHEMAS: dict[int, dict[str, tuple[str, bool]]] = {
    1: {  # SF Shield Suite
        "captcha_enabled":  ("🛡 الكابتشا عند الانضمام", True),
        "block_links":      ("🔗 حجب الروابط الخارجية",  True),
        "block_forwarded":  ("↩️ حجب الرسائل المُعاد توجيهها", False),
    },
    2: {  # SF Group Manager
        "welcome_enabled":      ("👋 رسالة الترحيب",           True),
        "delete_service_msgs":  ("🗑 حذف رسائل الخدمة",        True),
        "admin_only_cmds":      ("🔒 أوامر المشرفين فقط",       True),
    },
}


def get_schema(source_id: int) -> dict[str, tuple[str, bool]]:
    """Return config schema for a source_id, or empty dict if none."""
    return _SCHEMAS.get(source_id, {})


def parse_config(bot: Bot) -> dict:
    """Parse bot.bot_config JSON, returning {} on failure."""
    if not bot.bot_config:
        return {}
    try:
        return json.loads(bot.bot_config)
    except Exception:
        return {}


def resolve(bot: Bot, key: str) -> bool:
    """Return the current value of a config key (uses schema default if not set)."""
    schema = get_schema(bot.source_id or 0)
    default = schema[key][1] if key in schema else False
    return bool(parse_config(bot).get(key, default))


async def toggle(bot_id: int, key: str) -> bool | None:
    """
    Flip a boolean config key for the given bot.
    Returns the new value, or None if bot not found.
    """
    async with async_session_maker() as session:
        result = await session.execute(select(Bot).where(Bot.id == bot_id))
        bot = result.scalar_one_or_none()
        if not bot:
            return None
        cfg = parse_config(bot)
        schema = get_schema(bot.source_id or 0)
        default = schema[key][1] if key in schema else False
        new_val = not bool(cfg.get(key, default))
        cfg[key] = new_val
        bot.bot_config = json.dumps(cfg)
        await session.commit()
        logger.info("[bot_config] bot_id=%s key=%s → %s", bot_id, key, new_val)
        return new_val
