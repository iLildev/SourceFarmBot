"""
install_service — validates token, deducts seeds, persists Bot record,
then delegates startup to BotManager.
"""
import logging
import re
import aiohttp
from datetime import datetime

from sqlalchemy import select, update, func

from database.models import Bot, User
from database.session import async_session_maker
from runtime.crypto import encrypt_token
from services.user_service import get_user
from config import MAX_BOTS_FREE

logger = logging.getLogger(__name__)

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


async def install_bot(
    telegram_id: int,
    token: str,
    bot_name: str,
    source_id: int,
    source_cost: int,
    source_name: str,
) -> Bot:
    """
    1. Validate user + seeds.
    2. Detect duplicate tokens.
    3. Deduct seeds.
    4. Persist Bot record with encrypted token.
    5. Start bot via BotManager.
    Raises InstallError on any failure.
    """
    token = token.strip()
    hint  = token[:10]

    async with async_session_maker() as session:
        # Load user
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise InstallError("user_not_found")

        # Bot count limit (admins bypass the limit)
        from config import ADMIN_IDS
        if user.telegram_id not in ADMIN_IDS:
            bot_count_result = await session.execute(
                select(func.count()).select_from(Bot).where(Bot.owner_id == user.id)
            )
            bot_count = bot_count_result.scalar() or 0
            if bot_count >= MAX_BOTS_FREE:
                raise InstallError("bot_limit_reached")

        # Seeds check
        if source_cost > 0 and user.points < source_cost:
            raise InstallError("insufficient_seeds")

        # Duplicate token check
        dup_result = await session.execute(
            select(Bot).where(Bot.token_hint == hint)
        )
        if dup_result.scalar_one_or_none():
            raise InstallError("duplicate_token")

        # Deduct seeds
        if source_cost > 0:
            user.points -= source_cost

        # Encrypt full token
        try:
            encrypted = encrypt_token(token)
        except Exception as exc:
            logger.error("Token encryption failed: %s", exc)
            raise InstallError("encryption_failed") from exc

        now = datetime.utcnow()
        bot = Bot(
            owner_id=user.id,
            name=bot_name,
            token_hint=hint,
            token_encrypted=encrypted,
            source_id=source_id,
            is_running=False,
            pid=None,
            status="stopped",
            installed_at=now,
            created_at=now,
            mode="studio",
        )
        session.add(bot)
        await session.commit()
        await session.refresh(bot)

        logger.info(
            "Bot installed: owner_tg=%s bot_name=%s source=%s cost=%s seeds_left=%s bot_id=%s",
            telegram_id, bot_name, source_name, source_cost, user.points, bot.id,
        )

    # Start the bot subprocess via BotManager (outside the DB session)
    from runtime.bot_manager import get_manager
    manager = get_manager()
    started = await manager.start_bot(bot.id)
    if not started:
        logger.error("BotManager failed to start bot_id=%s — stored but not running.", bot.id)
        # Don't raise — bot is persisted, user can restart manually later

    return bot
