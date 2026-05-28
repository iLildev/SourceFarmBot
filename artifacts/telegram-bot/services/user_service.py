import logging
from datetime import datetime

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.session import async_session_maker

logger = logging.getLogger(__name__)

WELCOME_SEEDS            = 20
REFERRAL_BONUS_REFERRER  = 20
REFERRAL_BONUS_NEW_USER  = 10


async def get_or_create_user(
    telegram_id: int,
    first_name: str,
    last_name: str | None,
    username: str | None,
    referred_by: int | None = None,
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

        valid_referrer = None
        if referred_by and referred_by != telegram_id:
            ref_result = await session.execute(
                select(User).where(User.telegram_id == referred_by)
            )
            ref_user = ref_result.scalar_one_or_none()
            if ref_user:
                valid_referrer = ref_user

        starting_seeds = WELCOME_SEEDS
        if valid_referrer:
            starting_seeds += REFERRAL_BONUS_NEW_USER

        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            points=starting_seeds,
            referred_by=valid_referrer.telegram_id if valid_referrer else None,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(user)

        # Atomic referrer bonus — avoids race condition from ORM read-modify-write
        if valid_referrer:
            await session.execute(
                update(User)
                .where(User.id == valid_referrer.id)
                .values(points=User.points + REFERRAL_BONUS_REFERRER)
            )

        await session.commit()
        await session.refresh(user)

        logger.info(
            "New user registered: tg_id=%s ref_by=%s seeds=%s",
            telegram_id,
            valid_referrer.telegram_id if valid_referrer else None,
            user.points,
        )
        if valid_referrer:
            logger.info(
                "Referral reward: referrer tg_id=%s +%s seeds",
                valid_referrer.telegram_id, REFERRAL_BONUS_REFERRER,
            )
        return user, True


async def get_user(telegram_id: int) -> User | None:
    """Fetch a user by telegram_id, returns None if not found."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def get_referral_count(telegram_id: int) -> int:
    """Count how many users were referred by this telegram_id."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(func.count()).where(User.referred_by == telegram_id)
        )
        return result.scalar_one() or 0


async def add_seeds(telegram_id: int, amount: int) -> User | None:
    """
    Atomically add seeds to a user's balance.
    Uses a single UPDATE statement to avoid race conditions.
    Returns the updated user, or None if not found.
    """
    async with async_session_maker() as session:
        result = await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(points=User.points + amount)
            .returning(User)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        await session.commit()
        logger.info(
            "Seeds added: tg_id=%s amount=%s new_balance=%s",
            telegram_id, amount, user.points,
        )
        return user
