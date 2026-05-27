import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func

from database.models import User, Bot
from database.session import async_session_maker

logger = logging.getLogger(__name__)


async def get_platform_stats() -> dict:
    """Fetch overall platform statistics from the database."""
    async with async_session_maker() as session:

        total_users: int = (await session.execute(
            select(func.count()).select_from(User)
        )).scalar_one()

        today = datetime.utcnow().date()
        new_today: int = (await session.execute(
            select(func.count()).select_from(User).where(func.date(User.created_at) == today)
        )).scalar_one()

        week_ago = datetime.utcnow() - timedelta(days=7)
        new_week: int = (await session.execute(
            select(func.count()).select_from(User).where(User.created_at >= week_ago)
        )).scalar_one()

        # Active users = seen in the last 24 hours
        day_ago = datetime.utcnow() - timedelta(hours=24)
        active_24h: int = (await session.execute(
            select(func.count()).select_from(User).where(User.last_seen >= day_ago)
        )).scalar_one()

        total_seeds: int = (await session.execute(
            select(func.coalesce(func.sum(User.points), 0)).select_from(User)
        )).scalar_one()

        total_referrals: int = (await session.execute(
            select(func.count()).select_from(User).where(User.referred_by.isnot(None))
        )).scalar_one()

        # Bot statistics
        total_bots: int = (await session.execute(
            select(func.count()).select_from(Bot)
        )).scalar_one()

        running_bots: int = (await session.execute(
            select(func.count()).where(Bot.is_running.is_(True))
        )).scalar_one()

        bots_today: int = (await session.execute(
            select(func.count()).where(func.date(Bot.created_at) == today)
        )).scalar_one()

        referrers_result = await session.execute(
            select(
                User.first_name,
                User.username,
                User.telegram_id,
                (
                    select(func.count())
                    .where(User.__table__.c.referred_by == User.telegram_id)
                    .correlate(User)
                    .scalar_subquery()
                ).label("ref_count"),
            )
            .order_by(
                (
                    select(func.count())
                    .where(User.__table__.c.referred_by == User.telegram_id)
                    .correlate(User)
                    .scalar_subquery()
                ).desc()
            )
            .limit(5)
        )
        top_referrers = referrers_result.fetchall()

        return {
            "total_users":    total_users,
            "new_today":      new_today,
            "new_week":       new_week,
            "active_24h":     active_24h,
            "total_seeds":    total_seeds,
            "total_referrals": total_referrals,
            "total_bots":     total_bots,
            "running_bots":   running_bots,
            "bots_today":     bots_today,
            "top_referrers":  top_referrers,
        }


async def get_recent_users(limit: int = 8) -> list[User]:
    """Fetch the most recently registered users."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit)
        )
        return result.scalars().all()
