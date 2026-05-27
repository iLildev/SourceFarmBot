import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.session import async_session_maker

logger = logging.getLogger(__name__)


async def get_or_create_user(
    telegram_id: int,
    first_name: str,
    last_name: str | None,
    username: str | None,
) -> tuple[User, bool]:
    """
    Fetch the user by telegram_id, or create them if they don't exist yet.
    Returns (user, created) where `created` is True on first registration.
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            changed = False
            if user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if user.last_name != last_name:
                user.last_name = last_name
                changed = True
            if user.username != username:
                user.username = username
                changed = True
            if changed:
                await session.commit()
                await session.refresh(user)
            return user, False

        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            points=0,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("New user registered: tg_id=%s username=%s", telegram_id, username)
        return user, True


async def get_user(telegram_id: int) -> User | None:
    """Fetch a user by telegram_id, returns None if not found."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def add_seeds(telegram_id: int, amount: int) -> User | None:
    """Add seeds (points) to a user's balance. Returns updated user or None."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.points += amount
        await session.commit()
        await session.refresh(user)
        logger.info("Seeds added: tg_id=%s amount=%s new_balance=%s", telegram_id, amount, user.points)
        return user
