import logging
from sqlalchemy import select, delete
from database.models import Bot, User
from database.session import async_session_maker

logger = logging.getLogger(__name__)


async def get_user_bots(telegram_id: int) -> list[Bot]:
    async with async_session_maker() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return []
        result = await session.execute(
            select(Bot).where(Bot.owner_id == user.id).order_by(Bot.created_at.desc())
        )
        return result.scalars().all()


async def get_bot_by_id(bot_id: int, telegram_id: int) -> Bot | None:
    """Fetch a single bot — only if owned by this telegram_id."""
    async with async_session_maker() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return None
        result = await session.execute(
            select(Bot).where(Bot.id == bot_id, Bot.owner_id == user.id)
        )
        return result.scalar_one_or_none()


async def toggle_bot_running(bot_id: int, telegram_id: int, running: bool) -> Bot | None:
    async with async_session_maker() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return None
        result = await session.execute(
            select(Bot).where(Bot.id == bot_id, Bot.owner_id == user.id)
        )
        bot = result.scalar_one_or_none()
        if not bot:
            return None
        bot.is_running = running
        await session.commit()
        await session.refresh(bot)
        logger.info("Bot id=%s running=%s by tg_id=%s", bot_id, running, telegram_id)
        return bot


async def delete_bot(bot_id: int, telegram_id: int) -> bool:
    async with async_session_maker() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return False
        result = await session.execute(
            select(Bot).where(Bot.id == bot_id, Bot.owner_id == user.id)
        )
        bot = result.scalar_one_or_none()
        if not bot:
            return False
        await session.delete(bot)
        await session.commit()
        logger.info("Bot id=%s deleted by tg_id=%s", bot_id, telegram_id)
        return True
