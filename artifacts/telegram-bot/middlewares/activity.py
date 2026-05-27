"""
Activity middleware — updates `last_seen` on every user interaction.
Runs as an outer middleware so it fires even if a handler is rate-limited.
"""
import logging
from datetime import datetime
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy import select, update

from database.models import User
from database.session import async_session_maker

logger = logging.getLogger(__name__)


class ActivityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            try:
                async with async_session_maker() as session:
                    await session.execute(
                        update(User)
                        .where(User.telegram_id == user.id)
                        .values(last_seen=datetime.utcnow())
                    )
                    await session.commit()
            except Exception as exc:
                # Never block a user because of a logging failure
                logger.debug("ActivityMiddleware update failed: %s", exc)

        return await handler(event, data)
