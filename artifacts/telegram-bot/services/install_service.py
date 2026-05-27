import logging
import re
import aiohttp
from datetime import datetime

from sqlalchemy import select
from database.models import Bot, User
from database.session import async_session_maker
from services.user_service import get_user

logger = logging.getLogger(__name__)

# Telegram token: {bot_id}:{secret}
# bot_id: 8-12 digits, secret: 35-46 chars of [A-Za-z0-9_-]
TOKEN_RE = re.compile(r"^\d{5,15}:[A-Za-z0-9_-]{25,50}$")


class InstallError(Exception):
    pass


def is_valid_token_format(token: str) -> bool:
    return bool(TOKEN_RE.match(token.strip()))


async def fetch_bot_info(token: str) -> dict:
    """Call Telegram getMe to validate token. Returns bot info dict."""
    url = f"https://api.telegram.org/bot{token}/getMe"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            data = await resp.json()
    if not data.get("ok"):
        raise InstallError("token_invalid")
    return data["result"]


async def get_user_seeds(telegram_id: int) -> int:
    user = await get_user(telegram_id)
    return user.points if user else 0


async def token_already_registered(token_hint: str) -> bool:
    """Check if a bot with this token hint already exists."""
    hint = token_hint[:10]
    async with async_session_maker() as session:
        result = await session.execute(
            select(Bot).where(Bot.token_hint == hint)
        )
        return result.scalar_one_or_none() is not None


async def install_bot(
    telegram_id: int,
    token: str,
    bot_name: str,
    source_cost: int,
    source_name: str,
) -> Bot:
    """
    Deduct seeds and persist the new Bot record.
    Raises InstallError on insufficient seeds or duplicate token.
    """
    token = token.strip()
    hint  = token[:10]

    async with async_session_maker() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise InstallError("user_not_found")

        if source_cost > 0 and user.points < source_cost:
            raise InstallError("insufficient_seeds")

        dup_result = await session.execute(
            select(Bot).where(Bot.token_hint == hint)
        )
        if dup_result.scalar_one_or_none():
            raise InstallError("duplicate_token")

        if source_cost > 0:
            user.points -= source_cost

        bot = Bot(
            owner_id=user.id,
            name=bot_name,
            token_hint=hint,
            is_running=False,
            mode="studio",
            created_at=datetime.utcnow(),
        )
        session.add(bot)
        await session.commit()
        await session.refresh(bot)

        logger.info(
            "Bot installed: owner_tg=%s bot_name=%s source=%s cost=%s seeds_left=%s",
            telegram_id, bot_name, source_name, source_cost, user.points,
        )
        return bot
