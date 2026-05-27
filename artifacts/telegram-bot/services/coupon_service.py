"""
Coupon service — the brain of the coupon system.

Types:
  seeds        — adds N seeds to user balance immediately
  free_install — grants N free bot installations (no seeds deducted)
  discount     — sets a % discount on the user's next install

Validation layers:
  1. Code exists?
  2. Code active?
  3. Not expired?
  4. Under global max_uses?
  5. User within per_user_limit?
  6. User has min_seeds requirement?
"""
import logging
from datetime import datetime

from sqlalchemy import select, func

from database.models import Coupon, CouponUse, User
from database.session import async_session_maker
from services.audit_service import log_action

logger = logging.getLogger(__name__)


# ── Type metadata ─────────────────────────────────────────────────────────────

TYPE_LABELS = {
    "seeds":        "🌱 بذور",
    "free_install": "📦 تثبيت مجاني",
    "discount":     "🏷 خصم على التثبيت",
}

TYPE_EMOJIS = {
    "seeds":        "🌱",
    "free_install": "📦",
    "discount":     "🏷",
}


def _value_label(coupon_type: str, value: int) -> str:
    if coupon_type == "seeds":
        return f"{value:,} بذرة"
    if coupon_type == "free_install":
        return f"{value} تثبيت مجاني"
    if coupon_type == "discount":
        return f"خصم {value}% على التثبيت القادم"
    return str(value)


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_user_by_tg(session, telegram_id: int) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def _user_use_count(session, coupon_id: int, user_id: int) -> int:
    result = await session.execute(
        select(func.count())
        .where(CouponUse.coupon_id == coupon_id)
        .where(CouponUse.user_id == user_id)
    )
    return result.scalar_one() or 0


# ── Public API ─────────────────────────────────────────────────────────────────

async def validate_coupon(
    code: str, telegram_id: int
) -> tuple[Coupon | None, str | None]:
    """
    Validate a coupon for a user.
    Returns (coupon, None) on success or (None, error_message) on failure.
    """
    code = code.strip().upper()
    async with async_session_maker() as session:
        result = await session.execute(
            select(Coupon).where(Coupon.code == code)
        )
        coupon = result.scalar_one_or_none()

        if not coupon:
            return None, "❌ الكود غير موجود. تحقق من الكتابة وحاول مجدداً."

        if not coupon.is_active:
            return None, "🚫 هذا الكود غير مفعَّل حالياً."

        if coupon.expires_at and datetime.utcnow() > coupon.expires_at:
            return None, (
                f"⏰ انتهت صلاحية هذا الكود في "
                f"{coupon.expires_at.strftime('%d/%m/%Y')}."
            )

        if coupon.max_uses is not None and coupon.uses_count >= coupon.max_uses:
            return None, "🔒 تم استنفاد الحد الأقصى لاستخدامات هذا الكود."

        user = await _get_user_by_tg(session, telegram_id)
        if not user:
            return None, "❌ حسابك غير مسجَّل — أرسل /start أولاً."

        use_count = await _user_use_count(session, coupon.id, user.id)
        if use_count >= coupon.per_user_limit:
            times = "مرة" if coupon.per_user_limit == 1 else f"{coupon.per_user_limit} مرات"
            return None, f"⚠️ استخدمت هذا الكود بالفعل ({times} كحد أقصى)."

        if coupon.min_seeds > 0 and user.points < coupon.min_seeds:
            return None, (
                f"🌱 يتطلب هذا الكود رصيداً لا يقل عن "
                f"<b>{coupon.min_seeds:,} بذرة</b>.\n"
                f"رصيدك الحالي: <code>{user.points:,} بذرة</code>"
            )

        return coupon, None


async def redeem_coupon(coupon_id: int, telegram_id: int) -> dict:
    """
    Apply coupon effect and record the use.
    Returns a result dict with keys: type, value, label, new_balance, free_installs, discount_pct
    Raises ValueError on race-condition failures.
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(Coupon).where(Coupon.id == coupon_id)
        )
        coupon = result.scalar_one_or_none()
        if not coupon or not coupon.is_active:
            raise ValueError("invalid_coupon")

        user = await _get_user_by_tg(session, telegram_id)
        if not user:
            raise ValueError("user_not_found")

        # Double-check use count (race-condition guard)
        use_count = await _user_use_count(session, coupon.id, user.id)
        if use_count >= coupon.per_user_limit:
            raise ValueError("already_used")

        if coupon.max_uses is not None and coupon.uses_count >= coupon.max_uses:
            raise ValueError("exhausted")

        # ── Apply effect ──────────────────────────────────────────────────────
        if coupon.type == "seeds":
            user.points += coupon.value
        elif coupon.type == "free_install":
            user.free_installs += coupon.value
        elif coupon.type == "discount":
            # Take the higher discount if one is already pending
            user.discount_pct = max(user.discount_pct, coupon.value)

        # ── Record use ────────────────────────────────────────────────────────
        use_entry = CouponUse(
            coupon_id=coupon.id,
            user_id=user.id,
            used_at=datetime.utcnow(),
        )
        session.add(use_entry)
        coupon.uses_count += 1

        # Auto-disable when max_uses reached
        if coupon.max_uses is not None and coupon.uses_count >= coupon.max_uses:
            coupon.is_active = False
            logger.info("Coupon %s auto-disabled (max_uses reached)", coupon.code)

        await session.commit()
        await session.refresh(user)

        result_dict = {
            "type":          coupon.type,
            "value":         coupon.value,
            "label":         _value_label(coupon.type, coupon.value),
            "code":          coupon.code,
            "description":   coupon.description or "",
            "new_balance":   user.points,
            "free_installs": user.free_installs,
            "discount_pct":  user.discount_pct,
        }

        logger.info(
            "Coupon redeemed: code=%s tg_id=%s type=%s value=%s",
            coupon.code, telegram_id, coupon.type, coupon.value,
        )
        await log_action(
            admin_id=0,  # 0 = user action
            action="coupon_redeem",
            target_id=telegram_id,
            details={"code": coupon.code, "type": coupon.type, "value": coupon.value},
        )
        return result_dict


async def get_user_history(telegram_id: int, limit: int = 10) -> list[dict]:
    """Return a list of coupons the user has redeemed, newest first."""
    async with async_session_maker() as session:
        user = await _get_user_by_tg(session, telegram_id)
        if not user:
            return []
        result = await session.execute(
            select(CouponUse, Coupon)
            .join(Coupon, CouponUse.coupon_id == Coupon.id)
            .where(CouponUse.user_id == user.id)
            .order_by(CouponUse.used_at.desc())
            .limit(limit)
        )
        rows = result.fetchall()
        history = []
        for use, coupon in rows:
            history.append({
                "code":       coupon.code,
                "type":       coupon.type,
                "value":      coupon.value,
                "label":      _value_label(coupon.type, coupon.value),
                "emoji":      TYPE_EMOJIS.get(coupon.type, "🎫"),
                "used_at":    use.used_at,
                "description": coupon.description or "",
            })
        return history


async def create_coupon(
    code: str,
    coupon_type: str,
    value: int,
    created_by: int,
    description: str | None = None,
    max_uses: int | None = None,
    per_user_limit: int = 1,
    min_seeds: int = 0,
    expires_at: datetime | None = None,
) -> Coupon:
    """Create a new coupon. Raises ValueError if code already exists."""
    code = code.strip().upper()
    async with async_session_maker() as session:
        existing = await session.execute(
            select(Coupon).where(Coupon.code == code)
        )
        if existing.scalar_one_or_none():
            raise ValueError("duplicate_code")

        coupon = Coupon(
            code=code,
            type=coupon_type,
            value=value,
            description=description,
            max_uses=max_uses,
            uses_count=0,
            per_user_limit=per_user_limit,
            min_seeds=min_seeds,
            expires_at=expires_at,
            is_active=True,
            created_by=created_by,
            created_at=datetime.utcnow(),
        )
        session.add(coupon)
        await session.commit()
        await session.refresh(coupon)
        logger.info(
            "Coupon created: code=%s type=%s value=%s by=%s",
            code, coupon_type, value, created_by,
        )
        await log_action(
            admin_id=created_by, action="coupon_create",
            details={"code": code, "type": coupon_type, "value": value,
                     "max_uses": max_uses, "expires_at": str(expires_at)},
        )
        return coupon


async def get_all_coupons() -> list[Coupon]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Coupon).order_by(Coupon.created_at.desc())
        )
        return result.scalars().all()


async def get_coupon_by_code(code: str) -> Coupon | None:
    code = code.strip().upper()
    async with async_session_maker() as session:
        result = await session.execute(
            select(Coupon).where(Coupon.code == code)
        )
        return result.scalar_one_or_none()


async def toggle_coupon(code: str) -> Coupon | None:
    code = code.strip().upper()
    async with async_session_maker() as session:
        result = await session.execute(select(Coupon).where(Coupon.code == code))
        coupon = result.scalar_one_or_none()
        if not coupon:
            return None
        coupon.is_active = not coupon.is_active
        await session.commit()
        await session.refresh(coupon)
        logger.info("Coupon %s toggled → active=%s", code, coupon.is_active)
        return coupon


async def delete_coupon(code: str) -> bool:
    code = code.strip().upper()
    async with async_session_maker() as session:
        result = await session.execute(select(Coupon).where(Coupon.code == code))
        coupon = result.scalar_one_or_none()
        if not coupon:
            return False
        await session.delete(coupon)
        await session.commit()
        logger.info("Coupon %s deleted", code)
        return True


async def get_coupon_stats(coupon_id: int) -> list[CouponUse]:
    """Get all uses for a specific coupon."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(CouponUse)
            .where(CouponUse.coupon_id == coupon_id)
            .order_by(CouponUse.used_at.desc())
            .limit(20)
        )
        return result.scalars().all()


async def consume_free_install(telegram_id: int) -> bool:
    """Decrement free_installs by 1. Returns True if consumed successfully."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user or user.free_installs <= 0:
            return False
        user.free_installs -= 1
        await session.commit()
        return True


async def consume_discount(telegram_id: int) -> int:
    """Get and reset the user's pending discount_pct. Returns the % value (0 if none)."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user or user.discount_pct <= 0:
            return 0
        pct = user.discount_pct
        user.discount_pct = 0
        await session.commit()
        return pct
