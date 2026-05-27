import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, text

from database.models import User
from database.session import async_session_maker

logger = logging.getLogger(__name__)


async def get_platform_stats() -> dict:
    """Fetch overall platform statistics from the database."""
    async with async_session_maker() as session:
        total_users = (await session.execute(
            select(func.count()).select_from(User)
        )).scalar_one()

        today = datetime.utcnow().date()
        new_today = (await session.execute(
            select(func.count()).where(
                func.date(User.created_at) == today
            )
        )).scalar_one()

        week_ago = datetime.utcnow() - timedelta(days=7)
        new_week = (await session.execute(
            select(func.count()).where(User.created_at >= week_ago)
        )).scalar_one()

        total_seeds = (await session.execute(
            select(func.coalesce(func.sum(User.points), 0))
        )).scalar_one()

        total_referrals = (await session.execute(
            select(func.count()).where(User.referred_by.isnot(None))
        )).scalar_one()

        top_referrers_result = await session.execute(
            select(
                User.first_name,
                User.username,
                User.telegram_id,
                func.count(text("ref.id")).label("ref_count"),
            )
            .join(
                User.__table__.alias("ref"),
                text("ref.referred_by = users.telegram_id"),
                isouter=True,
            )
            .group_by(User.id)
            .order_by(text("ref_count DESC"))
            .limit(5)
        )
        top_referrers = top_referrers_result.fetchall()

        return {
            "total_users": total_users,
            "new_today": new_today,
            "new_week": new_week,
            "total_seeds": total_seeds,
            "total_referrals": total_referrals,
            "top_referrers": top_referrers,
        }


async def get_recent_users(limit: int = 5) -> list[User]:
    """Fetch the most recently registered users."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit)
        )
        return result.scalars().all()
