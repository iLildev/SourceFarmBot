"""
User-facing coupon handler.
Replaces the static placeholder in menu.py (menu_codes callback).

Flow:
  menu_codes   → landing page (history + Enter Code button)
  enter_code   → sets FSM state, prompts for code string
  [message]    → validates code → shows rich preview card
  code_redeem_ → applies coupon, shows reward
  codes_cancel → clears FSM, back to landing
  codes_history→ paginated redemption history
"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, Message,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from services.coupon_service import (
    validate_coupon, redeem_coupon,
    get_user_history, TYPE_LABELS, TYPE_EMOJIS,
)
from services.user_service import get_user

logger = logging.getLogger(__name__)
router = Router(name="codes")

ARABIC_MONTHS = [
    "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]


class CodesStates(StatesGroup):
    waiting_for_code = State()


# ── Keyboards ──────────────────────────────────────────────────────────────────

def _landing_kb(has_history: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="➕ أدخل كوداً",      callback_data="enter_code")],
    ]
    if has_history:
        rows.append([InlineKeyboardButton(text="📜 سجل الكودات المستخدمة", callback_data="codes_history")])
    rows.append([InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ إلغاء", callback_data="codes_cancel"),
    ]])


def _confirm_kb(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ استخدم الكود الآن", callback_data=f"code_redeem_{code}")],
        [InlineKeyboardButton(text="❌ إلغاء",              callback_data="codes_cancel")],
    ])


def _back_to_codes_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ أدخل كوداً آخر",  callback_data="enter_code")],
        [InlineKeyboardButton(text="🔙 رجوع للقائمة",     callback_data="menu")],
    ])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_dt(dt: datetime) -> str:
    return f"{dt.day} {ARABIC_MONTHS[dt.month]} {dt.year}"


def _expiry_tag(coupon) -> str:
    if not coupon.expires_at:
        return "♾ بدون انتهاء"
    delta = coupon.expires_at - datetime.utcnow()
    if delta.total_seconds() <= 0:
        return "⏰ منتهية الصلاحية"
    days = delta.days
    if days == 0:
        hours = int(delta.total_seconds() // 3600)
        return f"⏳ تنتهي بعد {hours} ساعة"
    return f"⏳ تنتهي خلال {days} يوم"


def _uses_tag(coupon) -> str:
    if coupon.max_uses is None:
        return "♾ استخدامات غير محدودة"
    remaining = coupon.max_uses - coupon.uses_count
    return f"🎟 متبقي {remaining} استخدام من {coupon.max_uses}"


def _build_preview(coupon, user_seeds: int) -> str:
    emoji      = TYPE_EMOJIS.get(coupon.type, "🎫")
    type_label = TYPE_LABELS.get(coupon.type, coupon.type)

    if coupon.type == "seeds":
        reward_line = f"🌱 <b>مكافأة:</b>   <code>+{coupon.value:,} بذرة</code>"
        after_line  = f"💰 <b>رصيدك بعد:</b> <code>{user_seeds + coupon.value:,} بذرة</code>"
    elif coupon.type == "free_install":
        reward_line = f"📦 <b>مكافأة:</b>   {coupon.value} تثبيت مجاني"
        after_line  = "⚡ يُطبَّق تلقائياً في التثبيت القادم"
    else:  # discount
        reward_line = f"🏷 <b>مكافأة:</b>   خصم {coupon.value}% على التثبيت القادم"
        after_line  = "⚡ يُطبَّق تلقائياً في أول تثبيت"

    desc_line = f"\n📝 <i>{coupon.description}</i>\n" if coupon.description else ""

    return (
        f"{emoji} <b>معاينة الكود</b>  <code>{coupon.code}</code>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"🏷 <b>النوع:</b>    {type_label}\n"
        f"{reward_line}\n"
        f"{after_line}\n"
        f"{desc_line}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"{_uses_tag(coupon)}\n"
        f"{_expiry_tag(coupon)}\n\n"
        f"هل تريد استخدام هذا الكود؟"
    )


# ── Handlers ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_codes")
async def show_codes_landing(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    history = await get_user_history(callback.from_user.id, limit=5)
    db_user = await get_user(callback.from_user.id)
    seeds   = db_user.points if db_user else 0

    lines = [
        "🎫 <b>الكودات والعروض</b>",
        "━━━━━━━━━━━━━━━━━\n",
    ]

    if db_user:
        extras = []
        if db_user.free_installs > 0:
            extras.append(f"📦 <b>تثبيتات مجانية:</b>  <code>{db_user.free_installs}</code>")
        if db_user.discount_pct > 0:
            extras.append(f"🏷 <b>خصم معلَّق:</b>       <code>{db_user.discount_pct}%</code>")
        if extras:
            lines.append("✨ <b>مزاياك النشطة:</b>")
            lines.extend(extras)
            lines.append("")

    lines.append(f"💰 <b>رصيدك:</b>  <code>{seeds:,} بذرة</code>\n")
    lines.append("أدخل كوداً للحصول على بذور أو مزايا حصرية 👇")

    text = "\n".join(lines)
    await callback.message.edit_text(
        text, reply_markup=_landing_kb(has_history=bool(history)), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "enter_code")
async def prompt_code_input(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CodesStates.waiting_for_code)
    await callback.message.edit_text(
        "🎫 <b>أدخل الكود</b>\n\n"
        "أرسل الكود الذي لديك (الأحرف الكبيرة أو الصغيرة مقبولة):\n\n"
        "<i>مثال: FARM100 أو summer50</i>",
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CodesStates.waiting_for_code)
async def receive_code(message: Message, state: FSMContext) -> None:
    raw_code = (message.text or "").strip()

    if not raw_code or len(raw_code) > 32:
        await message.answer(
            "⚠️ الكود يجب أن يكون نصاً لا يتجاوز 32 حرفاً.\n"
            "حاول مجدداً أو اضغط إلغاء.",
            reply_markup=_cancel_kb(),
            parse_mode="HTML",
        )
        return

    wait_msg = await message.answer("🔍 جارٍ التحقق من الكود...")

    coupon, error = await validate_coupon(raw_code, message.from_user.id)

    await wait_msg.delete()

    if error:
        await message.answer(
            f"<b>الكود: <code>{raw_code.upper()}</code></b>\n\n{error}",
            reply_markup=_cancel_kb(),
            parse_mode="HTML",
        )
        return

    db_user    = await get_user(message.from_user.id)
    user_seeds = db_user.points if db_user else 0

    preview = _build_preview(coupon, user_seeds)
    await state.update_data(coupon_id=coupon.id, coupon_code=coupon.code)

    await message.answer(
        preview,
        reply_markup=_confirm_kb(coupon.code),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("code_redeem_"))
async def redeem_code(callback: CallbackQuery, state: FSMContext) -> None:
    data   = await state.get_data()
    code   = callback.data.split("code_redeem_", 1)[1]
    c_id   = data.get("coupon_id")

    if not c_id:
        await callback.answer("انتهت صلاحية الجلسة — أعد إدخال الكود.", show_alert=True)
        await state.clear()
        return

    await state.clear()

    try:
        result = await redeem_coupon(c_id, callback.from_user.id)
    except ValueError as e:
        err = str(e)
        msgs = {
            "already_used":    "⚠️ استخدمت هذا الكود بالفعل.",
            "exhausted":       "🔒 الكود استُنفد للتو.",
            "invalid_coupon":  "❌ الكود لم يعد صالحاً.",
            "user_not_found":  "❌ حسابك غير مسجَّل — أرسل /start.",
        }
        await callback.answer(msgs.get(err, "❌ حدث خطأ — حاول لاحقاً."), show_alert=True)
        return

    # ── Build rich success card ───────────────────────────────────────────────
    emoji = TYPE_EMOJIS.get(result["type"], "🎫")

    if result["type"] == "seeds":
        effect = (
            f"🌱 <b>تمت إضافة:</b>   <code>+{result['value']:,} بذرة</code>\n"
            f"💰 <b>رصيدك الآن:</b>  <code>{result['new_balance']:,} بذرة</code>"
        )
    elif result["type"] == "free_install":
        effect = (
            f"📦 <b>تم منحك:</b>       {result['value']} تثبيت مجاني\n"
            f"📦 <b>رصيد التثبيت:</b>  <code>{result['free_installs']}</code> متبقي"
        )
    else:  # discount
        effect = (
            f"🏷 <b>خصم:</b>   {result['value']}% مُفعَّل على التثبيت القادم\n"
            f"⚡ سيُطبَّق تلقائياً عند أول تثبيت"
        )

    desc_part = f"\n📝 <i>{result['description']}</i>" if result["description"] else ""

    await callback.message.edit_text(
        f"✅ <b>تم تفعيل الكود بنجاح!</b>{desc_part}\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"{emoji} <b>الكود:</b>   <code>{result['code']}</code>\n\n"
        f"{effect}",
        reply_markup=_back_to_codes_kb(),
        parse_mode="HTML",
    )
    await callback.answer("✅ تم تفعيل الكود!")


@router.callback_query(F.data == "codes_cancel")
async def cancel_code(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    # Re-show landing page
    callback.data = "menu_codes"
    await show_codes_landing(callback, state)


@router.callback_query(F.data == "codes_history")
async def codes_history(callback: CallbackQuery) -> None:
    history = await get_user_history(callback.from_user.id, limit=10)

    if not history:
        await callback.answer("لا يوجد سجل بعد.", show_alert=True)
        return

    lines = ["📜 <b>الكودات المستخدمة:</b>\n"]
    for entry in history:
        dt  = _fmt_dt(entry["used_at"])
        lines.append(
            f"{entry['emoji']} <b>{entry['code']}</b>\n"
            f"   {entry['label']}  |  📅 {dt}\n"
        )

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 رجوع", callback_data="menu_codes"),
    ]])
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=back_kb, parse_mode="HTML"
    )
    await callback.answer()
