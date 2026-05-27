import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery,
)

from config import OWNER_USERNAME
from services.user_service import add_seeds

logger = logging.getLogger(__name__)
router = Router(name="donate")

# ── Constants ────────────────────────────────────────────────────────────────
STARS_PER_DOLLAR = 50          # display: 50 ⭐ ≈ $1
SEEDS_PER_STAR   = 2           # bonus seeds per donated star

PRESETS: list[tuple[int, str]] = [
    (25,  "$0.50"),
    (50,  "$1"),
    (100, "$2"),
    (250, "$5"),
    (500, "$10"),
]


class DonateStates(StatesGroup):
    waiting_amount = State()
    waiting_custom = State()
    confirming     = State()


# ── Keyboards ────────────────────────────────────────────────────────────────

def _amount_kb() -> InlineKeyboardMarkup:
    rows = []
    row: list[InlineKeyboardButton] = []
    for stars, usd in PRESETS:
        row.append(InlineKeyboardButton(
            text=f"⭐ {stars}  ({usd})",
            callback_data=f"don_amt_{stars}",
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="✏️ مبلغ مخصص", callback_data="don_custom")])
    rows.append([InlineKeyboardButton(text="❌ إلغاء",      callback_data="don_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _confirm_kb(stars: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="💫 ادفع الآن عبر البوت", callback_data=f"don_pay_{stars}")],
    ]
    if OWNER_USERNAME:
        rows.append([InlineKeyboardButton(
            text="🎁 رابط هدية مباشر",
            callback_data=f"don_link_{stars}",
        )])
    rows.append([
        InlineKeyboardButton(text="🔙 تغيير المبلغ", callback_data="don_back"),
        InlineKeyboardButton(text="❌ إلغاء",         callback_data="don_cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ إلغاء", callback_data="don_cancel"),
    ]])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _usd(stars: int) -> str:
    return f"${stars / STARS_PER_DOLLAR:.2f}"


def _seeds_bonus(stars: int) -> int:
    return stars * SEEDS_PER_STAR


def _confirm_text(stars: int) -> str:
    bonus = _seeds_bonus(stars)
    lines = [
        "━━━━━━━━━━━━━━━━━",
        f"⭐ <b>المبلغ:</b>    {stars} نجمة",
        f"💵 <b>يعادل:</b>    {_usd(stars)}",
        f"🌱 <b>مكافأة:</b>   +{bonus} بذرة تُضاف لرصيدك",
        "━━━━━━━━━━━━━━━━━",
        "",
        "اختر طريقة الدفع 👇",
    ]
    return "🧾 <b>تأكيد التبرع</b>\n\n" + "\n".join(lines)


# ── /donate command ──────────────────────────────────────────────────────────

@router.message(Command("donate"))
async def cmd_donate(message: Message, state: FSMContext) -> None:
    await state.set_state(DonateStates.waiting_amount)
    lines = [
        "💚 <b>ادعم SourceFarm</b>",
        "",
        "مساهمتك تساعد على تطوير المنصة وتحسينها.",
        "",
        f"<i>سعر الصرف: {STARS_PER_DOLLAR} ⭐ = $1</i>",
        f"<i>مكافأة: كل نجمة = {SEEDS_PER_STAR} بذرة تُضاف لرصيدك 🌱</i>",
        "",
        "كم نجمة تريد التبرع بها؟",
    ]
    await message.answer("\n".join(lines), reply_markup=_amount_kb(), parse_mode="HTML")


# ── Preset amount picked ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("don_amt_"))
async def pick_preset(callback: CallbackQuery, state: FSMContext) -> None:
    stars = int(callback.data.split("_")[-1])
    await state.update_data(stars=stars)
    await state.set_state(DonateStates.confirming)
    await callback.message.edit_text(
        _confirm_text(stars), reply_markup=_confirm_kb(stars), parse_mode="HTML"
    )
    await callback.answer()


# ── Custom amount ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "don_custom")
async def ask_custom(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DonateStates.waiting_custom)
    await callback.message.edit_text(
        "✏️ <b>أدخل عدد النجوم</b> (رقم صحيح، الحد الأدنى 1):\n\n"
        f"<i>مثال: 75 → {_usd(75)} ≈ {_seeds_bonus(75)} بذرة مكافأة</i>",
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DonateStates.waiting_custom)
async def receive_custom(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) < 1:
        await message.answer(
            "⚠️ من فضلك أرسل <b>رقماً صحيحاً</b> أكبر من صفر.\n"
            f"<i>مثال: 75</i>",
            reply_markup=_cancel_kb(),
            parse_mode="HTML",
        )
        return

    stars = int(text)
    await state.update_data(stars=stars)
    await state.set_state(DonateStates.confirming)
    await message.answer(
        _confirm_text(stars), reply_markup=_confirm_kb(stars), parse_mode="HTML"
    )


# ── Back to amount selection ──────────────────────────────────────────────────

@router.callback_query(F.data == "don_back")
async def back_to_amount(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DonateStates.waiting_amount)
    lines = [
        "💚 <b>ادعم SourceFarm</b>",
        "",
        f"<i>سعر الصرف: {STARS_PER_DOLLAR} ⭐ = $1</i>",
        f"<i>مكافأة: كل نجمة = {SEEDS_PER_STAR} بذرة 🌱</i>",
        "",
        "كم نجمة تريد التبرع بها؟",
    ]
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=_amount_kb(), parse_mode="HTML"
    )
    await callback.answer()


# ── Pay via bot invoice ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("don_pay_"))
async def send_invoice(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    stars = int(callback.data.split("_")[-1])
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="💚 دعم SourceFarm",
        description=f"تبرع بـ {stars} نجمة ← +{_seeds_bonus(stars)} بذرة مكافأة",
        payload=f"donate_{callback.from_user.id}_{stars}",
        currency="XTR",
        prices=[LabeledPrice(label=f"⭐ {stars} نجمة", amount=stars)],
        provider_token="",
    )
    await callback.answer()


# ── Gift link (invoice link) ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("don_link_"))
async def send_gift_link(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    stars = int(callback.data.split("_")[-1])
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)

    try:
        link = await bot.create_invoice_link(
            title="💚 هدية إلى مطوّر SourceFarm",
            description=f"تبرع بـ {stars} ⭐ — شكراً لدعمك!",
            payload=f"gift_{callback.from_user.id}_{stars}",
            currency="XTR",
            prices=[LabeledPrice(label=f"⭐ {stars} نجمة", amount=stars)],
            provider_token="",
        )
        personal_note = (
            f"\n\n<i>للتبرع على الحساب الشخصي مباشرةً،\n"
            f"أرسل النجوم لـ @{OWNER_USERNAME} من داخل تيليجرام.</i>"
        ) if OWNER_USERNAME else ""

        await callback.message.answer(
            f"🎁 <b>رابط الهدية المباشر</b>\n\n"
            f"انقر الرابط أدناه لإرسال <b>{stars} ⭐</b> هدية:\n\n"
            f"<code>{link}</code>\n\n"
            f"يمكن مشاركة هذا الرابط مع أي شخص.{personal_note}",
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.warning("create_invoice_link failed: %s", exc)
        await callback.message.answer(
            "⚠️ تعذّر إنشاء رابط الهدية. جرّب «ادفع الآن عبر البوت» بدلاً من ذلك."
        )
    await callback.answer()


# ── Cancel ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "don_cancel")
async def cancel_donate(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ تم إلغاء عملية التبرع.")
    await callback.answer()


# ── Telegram payment handlers ─────────────────────────────────────────────────

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, bot: Bot) -> None:
    await bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
async def payment_done(message: Message, bot: Bot) -> None:
    payment = message.successful_payment
    stars = payment.total_amount
    bonus = _seeds_bonus(stars)
    payload = payment.invoice_payload

    try:
        user_id = int(payload.split("_")[1])
        await add_seeds(user_id, bonus)
    except Exception as exc:
        logger.warning("Could not add seeds after payment: %s", exc)

    logger.info(
        "Donation received: tg_id=%s  stars=%s  payload=%s",
        message.from_user.id, stars, payload,
    )
    await message.answer(
        f"🎉 <b>شكراً على تبرعك!</b>\n\n"
        f"⭐ <b>استلمنا:</b>   {stars} نجمة\n"
        f"🌱 <b>مكافأتك:</b>  +{bonus} بذرة أُضيفت لرصيدك\n\n"
        f"مساهمتك تصنع فرقاً حقيقياً ❤️",
        parse_mode="HTML",
    )
