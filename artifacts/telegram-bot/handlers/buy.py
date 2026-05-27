"""
/buy — Seeds store via Telegram Stars.
Package price in Stars; seeds added on successful_payment.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery,
)

from services.user_service import add_seeds, get_user

logger = logging.getLogger(__name__)
router  = Router(name="buy")

# ── Packages: (stars, seeds_bonus_total, label) ───────────────────────────────
# 1 Star ≈ $0.02   |   100 Seeds = $1   |   1 Star → 4 Seeds base rate
PACKAGES: list[dict] = [
    {"id": 1, "stars": 50,   "seeds": 100,  "bonus": 0,   "label": "🌱 Starter"},
    {"id": 2, "stars": 100,  "seeds": 220,  "bonus": 20,  "label": "🌿 Growth"},
    {"id": 3, "stars": 250,  "seeds": 600,  "bonus": 100, "label": "🌳 Pro"},
    {"id": 4, "stars": 500,  "seeds": 1300, "bonus": 300, "label": "🚀 Elite"},
    {"id": 5, "stars": 1000, "seeds": 2800, "bonus": 800, "label": "💎 Legend"},
]

STARS_PER_DOLLAR = 50  # display only


def _pkg_by_id(pkg_id: int) -> dict | None:
    return next((p for p in PACKAGES if p["id"] == pkg_id), None)


# ── Keyboards ─────────────────────────────────────────────────────────────────

def _store_kb() -> InlineKeyboardMarkup:
    rows = []
    for p in PACKAGES:
        bonus_tag = f" (+{p['bonus']} مكافأة)" if p["bonus"] else ""
        rows.append([InlineKeyboardButton(
            text=f"{p['label']}  ⭐{p['stars']} → 🌱{p['seeds']}{bonus_tag}",
            callback_data=f"buy_pkg_{p['id']}",
        )])
    rows.append([InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _confirm_pkg_kb(pkg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💫 ادفع الآن",    callback_data=f"buy_pay_{pkg_id}")],
        [InlineKeyboardButton(text="🔙 العودة للمتجر", callback_data="buy_store")],
    ])


def _back_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_main"),
    ]])


# ── Store landing page ─────────────────────────────────────────────────────────

STORE_TEXT = (
    "🌱 <b>متجر البذور</b>\n"
    "━━━━━━━━━━━━━━━━━\n\n"
    "اشحن رصيدك بالبذور للتثبيت والمميزات.\n\n"
    f"💡 <b>سعر الصرف:</b>  <code>100 بذرة = $1</code>\n"
    f"⭐ <b>قيمة النجمة:</b>  <code>{STARS_PER_DOLLAR} ⭐ = $1</code>\n\n"
    "اختر الباقة المناسبة 👇"
)


@router.message(Command("buy"))
async def cmd_buy(message: Message) -> None:
    db_user = await get_user(message.from_user.id)
    seeds   = db_user.points if db_user else 0
    text    = STORE_TEXT + f"\n\n💰 <b>رصيدك الحالي:</b>  <code>{seeds:,} بذرة</code>"
    await message.answer(text, reply_markup=_store_kb(), parse_mode="HTML")


@router.callback_query(F.data == "buy_store")
async def show_store(callback: CallbackQuery) -> None:
    db_user = await get_user(callback.from_user.id)
    seeds   = db_user.points if db_user else 0
    text    = STORE_TEXT + f"\n\n💰 <b>رصيدك الحالي:</b>  <code>{seeds:,} بذرة</code>"
    await callback.message.edit_text(text, reply_markup=_store_kb(), parse_mode="HTML")
    await callback.answer()


# ── Package detail ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("buy_pkg_"))
async def pkg_detail(callback: CallbackQuery) -> None:
    pkg_id = int(callback.data.split("_")[-1])
    pkg    = _pkg_by_id(pkg_id)
    if not pkg:
        await callback.answer("الباقة غير موجودة", show_alert=True)
        return

    usd_val    = f"${pkg['stars'] / STARS_PER_DOLLAR:.2f}"
    bonus_line = f"🎁 <b>المكافأة:</b>     +{pkg['bonus']} بذرة إضافية\n" if pkg["bonus"] else ""

    text = (
        f"{pkg['label']}\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"⭐ <b>التكلفة:</b>      {pkg['stars']} نجمة  <i>({usd_val})</i>\n"
        f"🌱 <b>البذور:</b>      {pkg['seeds'] - pkg['bonus']:,} بذرة\n"
        f"{bonus_line}"
        f"━━━━━━━━━━━━━━━━━\n"
        f"✅ <b>المجموع:</b>     <code>{pkg['seeds']:,} بذرة</code>\n\n"
        f"اضغط <b>ادفع الآن</b> للمتابعة عبر نجوم Telegram."
    )
    await callback.message.edit_text(text, reply_markup=_confirm_pkg_kb(pkg_id), parse_mode="HTML")
    await callback.answer()


# ── Send invoice ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("buy_pay_"))
async def send_buy_invoice(callback: CallbackQuery, bot: Bot) -> None:
    pkg_id = int(callback.data.split("_")[-1])
    pkg    = _pkg_by_id(pkg_id)
    if not pkg:
        await callback.answer("الباقة غير موجودة", show_alert=True)
        return

    await callback.message.edit_text(
        f"⭐ <b>جارٍ إنشاء فاتورة {pkg['stars']} نجمة...</b>",
        reply_markup=None, parse_mode="HTML",
    )
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"🌱 {pkg['label']} — {pkg['seeds']:,} بذرة",
        description=(
            f"احصل على {pkg['seeds']:,} بذرة"
            + (f" (يشمل +{pkg['bonus']} مكافأة)" if pkg["bonus"] else "")
        ),
        payload=f"buy_{callback.from_user.id}_{pkg_id}",
        currency="XTR",
        prices=[LabeledPrice(label=f"⭐ {pkg['stars']} نجمة", amount=pkg["stars"])],
        provider_token="",
    )
    await callback.answer()


# ── Payment handlers ───────────────────────────────────────────────────────────

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, bot: Bot) -> None:
    await bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
async def payment_success(message: Message) -> None:
    payment = message.successful_payment
    payload = payment.invoice_payload

    # Only handle buy_ payloads (donate_ handled in donate.py)
    if not payload.startswith("buy_"):
        return

    try:
        parts  = payload.split("_")
        tg_id  = int(parts[1])
        pkg_id = int(parts[2])
    except (IndexError, ValueError):
        logger.error("Malformed buy payload: %s", payload)
        return

    pkg = _pkg_by_id(pkg_id)
    if not pkg:
        logger.error("Unknown pkg_id=%s in buy payload", pkg_id)
        return

    seeds = pkg["seeds"]
    user  = await add_seeds(tg_id, seeds)
    balance = user.points if user else seeds

    logger.info(
        "Seeds purchased: tg_id=%s pkg=%s stars=%s seeds=%s balance=%s",
        tg_id, pkg_id, pkg["stars"], seeds, balance,
    )
    await message.answer(
        f"✅ <b>تمت عملية الشراء بنجاح!</b>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"⭐ <b>دفعت:</b>         {pkg['stars']} نجمة\n"
        f"🌱 <b>حصلت على:</b>    <code>{seeds:,} بذرة</code>\n"
        f"💰 <b>رصيدك الآن:</b>  <code>{balance:,} بذرة</code>\n\n"
        f"شكراً لدعمك! ابدأ بتثبيت بوتاتك 🚀",
        reply_markup=_back_to_main_kb(),
        parse_mode="HTML",
    )
