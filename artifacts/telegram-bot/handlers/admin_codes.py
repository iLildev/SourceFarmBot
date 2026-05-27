"""
Admin coupon management.

Commands:
  /newcode            — interactive FSM to create a coupon step by step
  /newcode CODE seeds 500 [max:50] [expires:2026-12-31] [desc:نص_الوصف]
  /listcodes          — list all coupons
  /togglecode CODE    — enable / disable a coupon
  /deletecode CODE    — delete a coupon (with confirmation)

Admin panel button:
  adm_coupons → coupon management page
  adm_coupon_detail_{id} → per-coupon stats
"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from config import ADMIN_IDS
from services.coupon_service import (
    create_coupon, get_all_coupons, toggle_coupon,
    delete_coupon, get_coupon_stats, get_coupon_by_code,
    TYPE_LABELS, _value_label,
)
from services.audit_service import log_action

logger = logging.getLogger(__name__)
router = Router(name="admin_codes")


def is_admin(tg_id: int) -> bool:
    return tg_id in ADMIN_IDS


# ── FSM ───────────────────────────────────────────────────────────────────────

class CreateCouponStates(StatesGroup):
    code_str     = State()
    code_type    = State()
    code_value   = State()
    max_uses     = State()
    per_user     = State()
    min_seeds    = State()
    expiry       = State()
    description  = State()


# ── Keyboards ──────────────────────────────────────────────────────────────────

def _type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌱 بذور (seeds)",           callback_data="ctype_seeds")],
        [InlineKeyboardButton(text="📦 تثبيت مجاني (free_install)", callback_data="ctype_free_install")],
        [InlineKeyboardButton(text="🏷 خصم تثبيت (discount)",   callback_data="ctype_discount")],
        [InlineKeyboardButton(text="❌ إلغاء",                   callback_data="adm_newcode_cancel")],
    ])


def _skip_kb(next_hint: str = "") -> InlineKeyboardMarkup:
    label = f"⏭ تخطى{' (' + next_hint + ')' if next_hint else ''}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label,    callback_data="adm_nc_skip")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="adm_newcode_cancel")],
    ])


def _unlimited_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♾ غير محدود",  callback_data="adm_nc_unlimited")],
        [InlineKeyboardButton(text="❌ إلغاء",       callback_data="adm_newcode_cancel")],
    ])


def _no_expiry_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♾ بدون انتهاء صلاحية", callback_data="adm_nc_no_expiry")],
        [InlineKeyboardButton(text="❌ إلغاء",              callback_data="adm_newcode_cancel")],
    ])


def _coupons_list_kb(coupons: list) -> InlineKeyboardMarkup:
    rows = []
    for c in coupons:
        status = "🟢" if c.is_active else "🔴"
        rows.append([InlineKeyboardButton(
            text=f"{status} {c.code}  [{TYPE_LABELS.get(c.type, c.type)} — {c.value}]",
            callback_data=f"adm_coupon_detail_{c.id}",
        )])
    rows.append([InlineKeyboardButton(text="➕ كود جديد", callback_data="adm_newcode_start")])
    rows.append([InlineKeyboardButton(text="🔙 لوحة الأدمن", callback_data="adm_refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _coupon_detail_kb(coupon) -> InlineKeyboardMarkup:
    toggle_text = "⏹ تعطيل" if coupon.is_active else "▶️ تفعيل"
    toggle_cb   = f"adm_coupon_toggle_{coupon.code}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text,         callback_data=toggle_cb)],
        [InlineKeyboardButton(text="🗑 حذف الكود",      callback_data=f"adm_coupon_delete_{coupon.code}")],
        [InlineKeyboardButton(text="🔙 قائمة الكودات",  callback_data="adm_coupons")],
    ])


def _delete_confirm_kb(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ نعم، احذفه",      callback_data=f"adm_coupon_delete_confirm_{code}"),
        InlineKeyboardButton(text="❌ لا",              callback_data=f"adm_coupon_detail_{code}"),
    ]])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _coupon_card(c) -> str:
    status    = "🟢 مفعَّل" if c.is_active else "🔴 معطَّل"
    type_lbl  = TYPE_LABELS.get(c.type, c.type)
    val_label = _value_label(c.type, c.value)
    uses_line = f"{c.uses_count}/{c.max_uses}" if c.max_uses else f"{c.uses_count} / ♾"
    expiry    = c.expires_at.strftime("%d/%m/%Y") if c.expires_at else "بدون انتهاء"
    desc_line = f"\n📝 <i>{c.description}</i>" if c.description else ""
    min_s     = f"\n🌱 <b>حد أدنى:</b>     {c.min_seeds:,} بذرة" if c.min_seeds else ""
    per_u     = f"\n👤 <b>لكل مستخدم:</b> {c.per_user_limit} مرة" if c.per_user_limit != 1 else ""

    return (
        f"🎫 <b>الكود:</b>       <code>{c.code}</code>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📡 <b>الحالة:</b>      {status}\n"
        f"🏷 <b>النوع:</b>       {type_lbl}\n"
        f"💎 <b>القيمة:</b>      {val_label}\n"
        f"🎟 <b>الاستخدامات:</b> {uses_line}\n"
        f"📅 <b>الانتهاء:</b>    {expiry}"
        f"{min_s}{per_u}{desc_line}"
    )


def _parse_quick_newcode(parts: list[str]) -> dict | None:
    """
    Parse: /newcode CODE TYPE VALUE [max:N] [expires:YYYY-MM-DD] [desc:TEXT]
    Returns dict of kwargs for create_coupon or None if invalid.
    """
    if len(parts) < 4:
        return None
    code        = parts[1].upper()
    coupon_type = parts[2].lower()
    if coupon_type not in ("seeds", "free_install", "discount"):
        return None
    if not parts[3].isdigit():
        return None
    value = int(parts[3])

    kwargs: dict = {
        "code": code, "coupon_type": coupon_type, "value": value,
        "max_uses": None, "expires_at": None, "description": None,
        "per_user_limit": 1, "min_seeds": 0,
    }
    for part in parts[4:]:
        if part.startswith("max:") and part[4:].isdigit():
            kwargs["max_uses"] = int(part[4:])
        elif part.startswith("expires:"):
            try:
                kwargs["expires_at"] = datetime.strptime(part[8:], "%Y-%m-%d")
            except ValueError:
                pass
        elif part.startswith("desc:"):
            kwargs["description"] = part[5:].replace("_", " ")
        elif part.startswith("peruser:") and part[8:].isdigit():
            kwargs["per_user_limit"] = int(part[8:])
        elif part.startswith("minseeds:") and part[9:].isdigit():
            kwargs["min_seeds"] = int(part[9:])
    return kwargs


# ── /newcode ───────────────────────────────────────────────────────────────────

@router.message(Command("newcode"))
async def cmd_newcode(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return

    parts = message.text.strip().split()

    # Quick-create mode
    if len(parts) >= 4:
        kwargs = _parse_quick_newcode(parts)
        if not kwargs:
            await message.answer(
                "⚙️ <b>صيغة سريعة:</b>\n"
                "<code>/newcode CODE TYPE VALUE [max:N] [expires:YYYY-MM-DD] [desc:النص]</code>\n\n"
                "الأنواع: <code>seeds</code>  <code>free_install</code>  <code>discount</code>",
                parse_mode="HTML",
            )
            return
        try:
            coupon = await create_coupon(**kwargs, created_by=message.from_user.id)
            await message.answer(
                f"✅ <b>تم إنشاء الكود بنجاح!</b>\n\n{_coupon_card(coupon)}",
                parse_mode="HTML",
            )
        except ValueError:
            await message.answer(f"❌ الكود <code>{kwargs['code']}</code> موجود مسبقاً.", parse_mode="HTML")
        return

    # Interactive FSM mode
    await state.set_state(CreateCouponStates.code_str)
    await message.answer(
        "🎫 <b>إنشاء كود جديد</b>\n\n"
        "الخطوة 1/7 — أرسل <b>رمز الكود</b> (حروف وأرقام فقط، بدون مسافات):\n\n"
        "<i>مثال: FARM100 أو VIP2026</i>",
        reply_markup=_skip_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_newcode_start")
async def adm_newcode_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(CreateCouponStates.code_str)
    await callback.message.edit_text(
        "🎫 <b>إنشاء كود جديد</b>\n\n"
        "الخطوة 1/7 — أرسل <b>رمز الكود</b> (حروف وأرقام فقط):\n\n"
        "<i>مثال: SUMMER50 أو VIP2026</i>",
        reply_markup=_skip_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateCouponStates.code_str)
async def step_code_str(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip().upper()
    if not code.replace("-", "").replace("_", "").isalnum() or len(code) > 20:
        await message.answer(
            "⚠️ الرمز يجب أن يكون حروفاً وأرقاماً فقط، بحد أقصى 20 حرفاً.",
            reply_markup=_skip_kb(),
            parse_mode="HTML",
        )
        return
    await state.update_data(code=code)
    await state.set_state(CreateCouponStates.code_type)
    await message.answer(
        f"✅ الكود: <code>{code}</code>\n\n"
        "الخطوة 2/7 — اختر <b>نوع الكود</b>:",
        reply_markup=_type_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("ctype_"))
async def step_type(callback: CallbackQuery, state: FSMContext) -> None:
    if await state.get_state() != CreateCouponStates.code_type.state:
        await callback.answer()
        return
    coupon_type = callback.data.split("ctype_", 1)[1]
    await state.update_data(coupon_type=coupon_type)
    await state.set_state(CreateCouponStates.code_value)

    hints = {
        "seeds":        "عدد البذور (مثال: 500)",
        "free_install": "عدد التثبيتات المجانية (مثال: 1 أو 3)",
        "discount":     "نسبة الخصم % (مثال: 20 لـ 20%)",
    }
    await callback.message.edit_text(
        f"✅ النوع: {TYPE_LABELS[coupon_type]}\n\n"
        f"الخطوة 3/7 — أرسل <b>القيمة</b>:\n<i>{hints[coupon_type]}</i>",
        reply_markup=_skip_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateCouponStates.code_value)
async def step_value(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if not txt.isdigit() or int(txt) <= 0:
        await message.answer("⚠️ أرسل رقماً صحيحاً موجباً.", reply_markup=_skip_kb())
        return
    await state.update_data(value=int(txt))
    await state.set_state(CreateCouponStates.max_uses)
    await message.answer(
        "الخطوة 4/7 — <b>الحد الأقصى للاستخدامات</b> (رقم أو غير محدود):",
        reply_markup=_unlimited_kb(), parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_nc_unlimited")
async def step_unlimited(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(max_uses=None)
    await state.set_state(CreateCouponStates.per_user)
    await callback.message.edit_text(
        "الخطوة 5/7 — <b>عدد المرات لكل مستخدم</b>\n"
        "أرسل رقماً (عادةً 1) أو تخطى للإبقاء على 1:",
        reply_markup=_skip_kb("1 لكل مستخدم"), parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateCouponStates.max_uses)
async def step_max_uses(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if not txt.isdigit() or int(txt) <= 0:
        await message.answer("⚠️ أرسل رقماً موجباً أو اضغط «غير محدود».", reply_markup=_unlimited_kb())
        return
    await state.update_data(max_uses=int(txt))
    await state.set_state(CreateCouponStates.per_user)
    await message.answer(
        "الخطوة 5/7 — <b>عدد المرات لكل مستخدم</b>\n"
        "أرسل رقماً أو تخطى للإبقاء على 1:",
        reply_markup=_skip_kb("1 لكل مستخدم"), parse_mode="HTML",
    )


@router.message(CreateCouponStates.per_user)
async def step_per_user(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    per_user = 1
    if txt.isdigit() and int(txt) >= 1:
        per_user = int(txt)
    await state.update_data(per_user_limit=per_user)
    await state.set_state(CreateCouponStates.min_seeds)
    await message.answer(
        "الخطوة 6/7 — <b>الحد الأدنى من البذور المطلوبة</b>\n"
        "أرسل رقماً أو تخطى (0 = بدون حد):",
        reply_markup=_skip_kb("0 بدون حد"), parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_nc_skip")
async def step_skip(callback: CallbackQuery, state: FSMContext) -> None:
    current = await state.get_state()
    if current == CreateCouponStates.per_user.state:
        await state.update_data(per_user_limit=1)
        await state.set_state(CreateCouponStates.min_seeds)
        await callback.message.edit_text(
            "الخطوة 6/7 — <b>الحد الأدنى من البذور</b> (0 = بدون حد):",
            reply_markup=_skip_kb("0"), parse_mode="HTML",
        )
    elif current == CreateCouponStates.min_seeds.state:
        await state.update_data(min_seeds=0)
        await state.set_state(CreateCouponStates.expiry)
        await callback.message.edit_text(
            "الخطوة 7/7 — <b>تاريخ الانتهاء</b> (YYYY-MM-DD) أو بدون:",
            reply_markup=_no_expiry_kb(), parse_mode="HTML",
        )
    elif current == CreateCouponStates.expiry.state:
        await state.update_data(expires_at=None)
        await state.set_state(CreateCouponStates.description)
        await callback.message.edit_text(
            "الخطوة الأخيرة — <b>الوصف</b> (يُعرض للمستخدم) أو تخطى:",
            reply_markup=_skip_kb("بدون وصف"), parse_mode="HTML",
        )
    elif current == CreateCouponStates.description.state:
        await state.update_data(description=None)
        await _finalize(callback, state)
    await callback.answer()


@router.message(CreateCouponStates.min_seeds)
async def step_min_seeds(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    min_seeds = 0
    if txt.isdigit():
        min_seeds = int(txt)
    await state.update_data(min_seeds=min_seeds)
    await state.set_state(CreateCouponStates.expiry)
    await message.answer(
        "الخطوة 7/7 — <b>تاريخ الانتهاء</b> (YYYY-MM-DD) أو بدون:",
        reply_markup=_no_expiry_kb(), parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_nc_no_expiry")
async def step_no_expiry(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(expires_at=None)
    await state.set_state(CreateCouponStates.description)
    await callback.message.edit_text(
        "الخطوة الأخيرة — <b>الوصف</b> (يُعرض للمستخدم) أو تخطى:",
        reply_markup=_skip_kb("بدون وصف"), parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateCouponStates.expiry)
async def step_expiry(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    expires_at = None
    try:
        expires_at = datetime.strptime(txt, "%Y-%m-%d")
    except ValueError:
        await message.answer(
            "⚠️ الصيغة: <code>YYYY-MM-DD</code> مثال: <code>2026-12-31</code>\n"
            "أو اضغط «بدون انتهاء».",
            reply_markup=_no_expiry_kb(), parse_mode="HTML",
        )
        return
    await state.update_data(expires_at=expires_at)
    await state.set_state(CreateCouponStates.description)
    await message.answer(
        "الخطوة الأخيرة — <b>الوصف</b> (يُعرض للمستخدم) أو تخطى:",
        reply_markup=_skip_kb("بدون وصف"), parse_mode="HTML",
    )


@router.message(CreateCouponStates.description)
async def step_description(message: Message, state: FSMContext) -> None:
    desc = (message.text or "").strip() or None
    await state.update_data(description=desc)
    await _finalize_msg(message, state)


async def _finalize(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    try:
        coupon = await create_coupon(
            code=data["code"],
            coupon_type=data["coupon_type"],
            value=data["value"],
            created_by=callback.from_user.id,
            description=data.get("description"),
            max_uses=data.get("max_uses"),
            per_user_limit=data.get("per_user_limit", 1),
            min_seeds=data.get("min_seeds", 0),
            expires_at=data.get("expires_at"),
        )
        await callback.message.edit_text(
            f"✅ <b>تم إنشاء الكود بنجاح!</b>\n\n{_coupon_card(coupon)}",
            reply_markup=_coupon_detail_kb(coupon), parse_mode="HTML",
        )
    except ValueError:
        await callback.message.edit_text(
            f"❌ الكود <code>{data.get('code', '?')}</code> موجود مسبقاً.", parse_mode="HTML"
        )


async def _finalize_msg(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    try:
        coupon = await create_coupon(
            code=data["code"],
            coupon_type=data["coupon_type"],
            value=data["value"],
            created_by=message.from_user.id,
            description=data.get("description"),
            max_uses=data.get("max_uses"),
            per_user_limit=data.get("per_user_limit", 1),
            min_seeds=data.get("min_seeds", 0),
            expires_at=data.get("expires_at"),
        )
        await message.answer(
            f"✅ <b>تم إنشاء الكود بنجاح!</b>\n\n{_coupon_card(coupon)}",
            reply_markup=_coupon_detail_kb(coupon), parse_mode="HTML",
        )
    except ValueError:
        await message.answer(
            f"❌ الكود <code>{data.get('code', '?')}</code> موجود مسبقاً.", parse_mode="HTML"
        )


@router.callback_query(F.data == "adm_newcode_cancel")
async def cancel_newcode(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ تم إلغاء إنشاء الكود.")
    await callback.answer()


# ── /listcodes ────────────────────────────────────────────────────────────────

@router.message(Command("listcodes"))
async def cmd_listcodes(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    coupons = await get_all_coupons()
    if not coupons:
        await message.answer("🎫 لا توجد كودات بعد. أنشئ واحداً بـ /newcode")
        return
    await message.answer(
        f"🎫 <b>جميع الكودات ({len(coupons)}):</b>",
        reply_markup=_coupons_list_kb(coupons),
        parse_mode="HTML",
    )


# ── /togglecode ────────────────────────────────────────────────────────────────

@router.message(Command("togglecode"))
async def cmd_togglecode(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("الاستخدام: <code>/togglecode CODE</code>", parse_mode="HTML")
        return
    coupon = await toggle_coupon(parts[1])
    if not coupon:
        await message.answer(f"❌ الكود <code>{parts[1].upper()}</code> غير موجود.", parse_mode="HTML")
        return
    status = "🟢 مفعَّل" if coupon.is_active else "🔴 معطَّل"
    await message.answer(
        f"✅ الكود <code>{coupon.code}</code> أصبح <b>{status}</b>.", parse_mode="HTML"
    )
    await log_action(message.from_user.id, "coupon_toggle",
                     details={"code": coupon.code, "active": coupon.is_active})


# ── /deletecode ────────────────────────────────────────────────────────────────

@router.message(Command("deletecode"))
async def cmd_deletecode(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("الاستخدام: <code>/deletecode CODE</code>", parse_mode="HTML")
        return
    code   = parts[1].upper()
    coupon = await get_coupon_by_code(code)
    if not coupon:
        await message.answer(f"❌ الكود <code>{code}</code> غير موجود.", parse_mode="HTML")
        return
    await message.answer(
        f"⚠️ هل تريد حذف الكود <code>{code}</code> نهائياً؟",
        reply_markup=_delete_confirm_kb(code), parse_mode="HTML",
    )


# ── Admin panel callbacks ──────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_coupons")
async def adm_coupons(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("🚫 غير مصرح", show_alert=True)
        return
    coupons = await get_all_coupons()
    active  = sum(1 for c in coupons if c.is_active)
    total_uses = sum(c.uses_count for c in coupons)
    text = (
        f"🎫 <b>إدارة الكودات</b>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>الإجمالي:</b>      {len(coupons)} كود\n"
        f"🟢 <b>مفعَّلة:</b>      {active}\n"
        f"🔴 <b>معطَّلة:</b>      {len(coupons) - active}\n"
        f"🎟 <b>إجمالي الاستخدامات:</b>  {total_uses}\n\n"
        f"اختر كوداً للإدارة أو أنشئ جديداً:"
    )
    if not coupons:
        text += "\n\n<i>لا توجد كودات بعد.</i>"
    await callback.message.edit_text(
        text, reply_markup=_coupons_list_kb(coupons), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_coupon_detail_"))
async def adm_coupon_detail(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    raw = callback.data.split("adm_coupon_detail_", 1)[1]

    # Can be either an ID (int) or a code (str) — handle both
    coupon = None
    if raw.isdigit():
        coupons = await get_all_coupons()
        coupon  = next((c for c in coupons if c.id == int(raw)), None)
    else:
        coupon = await get_coupon_by_code(raw)

    if not coupon:
        await callback.answer("الكود غير موجود", show_alert=True)
        return

    uses = await get_coupon_stats(coupon.id)
    uses_line = f"\n\n👥 <b>آخر الاستخدامات ({len(uses)}):</b>"
    for u in uses[:5]:
        dt = u.used_at.strftime("%d/%m %H:%M") if u.used_at else "—"
        uses_line += f"\n  • user_id={u.user_id}  |  {dt}"

    await callback.message.edit_text(
        _coupon_card(coupon) + uses_line,
        reply_markup=_coupon_detail_kb(coupon),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_coupon_toggle_"))
async def adm_toggle(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    code   = callback.data.split("adm_coupon_toggle_", 1)[1]
    coupon = await toggle_coupon(code)
    if not coupon:
        await callback.answer("الكود غير موجود", show_alert=True)
        return
    status = "🟢 مفعَّل" if coupon.is_active else "🔴 معطَّل"
    await callback.answer(f"{status}")
    await log_action(callback.from_user.id, "coupon_toggle",
                     details={"code": coupon.code, "active": coupon.is_active})
    # Refresh detail
    callback.data = f"adm_coupon_detail_{coupon.code}"
    await adm_coupon_detail(callback)


@router.callback_query(
    F.data.startswith("adm_coupon_delete_")
    & ~F.data.startswith("adm_coupon_delete_confirm_")
)
async def adm_delete_ask(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    code = callback.data.split("adm_coupon_delete_", 1)[1]
    await callback.message.edit_text(
        f"⚠️ هل تريد حذف الكود <code>{code}</code> نهائياً؟\n"
        "سيُحذف سجل جميع استخداماته أيضاً.",
        reply_markup=_delete_confirm_kb(code),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_coupon_delete_confirm_"))
async def adm_delete_confirm(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    code    = callback.data.split("adm_coupon_delete_confirm_", 1)[1]
    deleted = await delete_coupon(code)
    if not deleted:
        await callback.answer("الكود غير موجود", show_alert=True)
        return
    await log_action(callback.from_user.id, "coupon_delete", details={"code": code})
    await callback.answer("🗑 تم الحذف")
    callback.data = "adm_coupons"
    await adm_coupons(callback)
