"""
Audit service — records all admin actions in the database.
"""
import json
import logging
from datetime import datetime

from sqlalchemy import select

from database.models import AuditLog
from database.session import async_session_maker

logger = logging.getLogger(__name__)


async def log_action(
    admin_id: int,
    action: str,
    target_id: int | None = None,
    details: dict | None = None,
) -> None:
    """Insert an audit log entry. Never raises — failures are silently logged."""
    try:
        async with async_session_maker() as session:
            entry = AuditLog(
                admin_id=admin_id,
                action=action,
                target_id=target_id,
                details=json.dumps(details or {}, ensure_ascii=False),
                created_at=datetime.utcnow(),
            )
            session.add(entry)
            await session.commit()
            logger.info("AUDIT: admin=%s action=%s target=%s", admin_id, action, target_id)
    except Exception as exc:
        logger.error("audit_service.log_action failed: %s", exc)


async def get_recent_logs(limit: int = 15) -> list[AuditLog]:
    """Fetch the most recent audit entries."""
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(AuditLog)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    except Exception as exc:
        logger.error("audit_service.get_recent_logs failed: %s", exc)
        return []
