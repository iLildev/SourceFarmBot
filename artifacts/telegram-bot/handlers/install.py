import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from data.sources import SOURCES
from services.install_service import (
    InstallError,
    fetch_bot_info,
    get_user_seeds,
    install_bot,
    is_valid_token_format,
    user_has_source,
)
from services.user_service import get_user
from services.coupon_service import consume_free_install, consume_discount
from config import ADMIN_IDS, MAX_BOTS_FREE

logger = logging.getLogger(__name__)
router = Router(name="install")


class InstallStates(StatesGroup):
    waiting_for_token = State()


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء التثبيت", callback_data="install_cancel")]
        ]
    )


def _installed_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌲 تصفح المزيد",    callback_data="source_tree")],
            [InlineKeyboardButton(text="🤖 بوتاتي",         callback_data="menu_mybots")],
            [InlineKeyboardButton(text="🔙 الرئيسية",       callback_data="back_main")],
        ]
    )


@router.callback_query(F.data.startswith("install_") & ~F.data.in_({"install_cancel"}))
async def start_install(callback: CallbackQuery, state: FSMContext) -> None:
    source_id = int(callback.data.split("_")[-1])
    source    = next((s for s in SOURCES if s["id"] == source_id), None)

    if not source:
        await callback.answer("المصدر غير موجود", show_alert=True)
        return

    tg_id    = callback.from_user.id
    is_admin = tg_id in ADMIN_IDS

    # ── One copy per source check ─────────────────────────────────────────────
    if not is_admin and await user_has_source(tg_id, source_id):
        await callback.answer(
            f"✋ لديك نسخة مثبّتة مسبقاً من {source['name']}.\n\n"
            "كل سورس يُسمح بنسخة واحدة فقط لكل مستخدم.",
            show_alert=True,
        )
        return
    seeds    = await get_user_seeds(tg_id)
    db_user  = await get_user(tg_id)

    base_cost = source["points"]

    # ── Determine effective cost and benefit ─────────────────────────────────
    if is_admin:
        effective_cost = 0
        benefit_type   = "admin"
        cost_display   = "مجاني 🎁"
        benefit_note   = "\n🛡 <i>وضع الأدمن — التثبيت مجاني</i>\n"

    elif db_user and db_user.free_installs > 0:
        effective_cost = 0
        benefit_type   = "free_install"
        cost_display   = "مجاني 📦"
        benefit_note   = (
            f"\n📦 <i>لديك <b>{db_user.free_installs}</b> تثبيت مجاني — سيُستهلك واحد</i>\n"
        )

    elif db_user and db_user.discount_pct > 0:
        discount       = db_user.discount_pct
        effective_cost = max(0, int(base_cost * (1 - discount / 100)))
        benefit_type   = "discount"
        saved          = base_cost - effective_cost
        cost_display   = (
            f"<code>{effective_cost:,} بذرة</code> "
            f"<s>{base_cost:,}</s>  <i>(خصم {discount}% — وفّرت {saved:,})</i>"
        )
        benefit_note   = f"\n🏷 <i>خصم {discount}% مُطبَّق — سيُستهلك بعد التثبيت</i>\n"

    else:
        effective_cost = base_cost
        benefit_type   = "none"
        cost_display   = f"<code>{effective_cost:,} بذرة</code>"
        benefit_note   = ""

    # ── Check affordability ───────────────────────────────────────────────────
    if benefit_type not in ("admin", "free_install") and seeds < effective_cost:
        shortage = effective_cost - seeds
        await callback.answer(
            f"🌱 رصيدك غير كافٍ!\n\n"
            f"السعر:    {effective_cost:,} بذرة\n"
            f"رصيدك:   {seeds:,} بذرة\n"
            f"يُنقصك:  {shortage:,} بذرة",
            show_alert=True,
        )
        return

    # ── Override any existing FSM install state ───────────────────────────────
    if await state.get_state() == InstallStates.waiting_for_token.state:
        await state.clear()

    await state.set_state(InstallStates.waiting_for_token)
    await state.update_data(
        source_id=source_id,
        source_name=source["name"],
        cost=effective_cost,
        benefit_type=benefit_type,
    )

    await callback.message.answer(
        f"📦 <b>تثبيت: {source['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷  الفئة:   {source['category']}\n"
        f"🌱 السعر:   {cost_display}\n"
        f"💰 رصيدك:  <code>{seeds:,} بذرة</code>\n"
        f"{benefit_note}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"للمتابعة، أرسل <b>توكن البوت</b> الخاص بك:\n\n"
        f"📌 <b>كيف أحصل على التوكن؟</b>\n"
        f"  1️⃣ افتح @BotFather على تيليجرام\n"
        f"  2️⃣ أرسل /newbot وأعطِ البوت اسماً\n"
        f"  3️⃣ انسخ التوكن وأرسله هنا\n\n"
        f"<i>يبدو التوكن هكذا:</i>\n"
        f"<code>1234567890:ABCDefGhIjKlMnOpQrStUvWxYz123456789</code>",
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "install_cancel")
async def cancel_install(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>تم إلغاء التثبيت.</b>\n\n"
        "يمكنك العودة للتصفح في أي وقت.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌲 Source Tree", callback_data="source_tree")],
            [InlineKeyboardButton(text="🔙 الرئيسية",   callback_data="back_main")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(InstallStates.waiting_for_token)
async def receive_token(message: Message, state: FSMContext) -> None:
    token = (message.text or "").strip()

    if not is_valid_token_format(token):
        await message.answer(
            "⚠️ <b>صيغة التوكن غير صحيحة.</b>\n\n"
            "التوكن يجب أن يكون على الشكل:\n"
            "<code>123456789:ABCDefGhIjKlMnOpQrStUvWxYz123456789</code>\n\n"
            "أرسله مجدداً، أو اضغط إلغاء.",
            reply_markup=_cancel_kb(),
            parse_mode="HTML",
        )
        return

    wait_msg = await message.answer("🔄 جارٍ التحقق من التوكن...")

    try:
        bot_info = await fetch_bot_info(token)
    except InstallError:
        await wait_msg.delete()
        await message.answer(
            "❌ <b>التوكن غير صالح أو منتهي الصلاحية.</b>\n\n"
            "تأكد من نسخه كاملاً من @BotFather وأرسله مجدداً.",
            reply_markup=_cancel_kb(),
            parse_mode="HTML",
        )
        return
    except Exception as e:
        logger.error("Token validation error: %s", e)
        await wait_msg.delete()
        await message.answer(
            "⚠️ تعذّر التحقق من التوكن الآن. حاول مجدداً بعد لحظات.",
            reply_markup=_cancel_kb(),
            parse_mode="HTML",
        )
        return

    data         = await state.get_data()
    source_name: str = data["source_name"]
    cost: int        = data["cost"]
    benefit_type: str = data.get("benefit_type", "none")
    tg_id            = message.from_user.id

    bot_username   = bot_info.get("username", "")
    bot_first_name = bot_info.get("first_name", source_name)

    data         = await state.get_data()
    source_id_for_install: int = data.get("source_id", 0)

    try:
        await install_bot(
            telegram_id=tg_id,
            token=token,
            bot_name=bot_first_name,
            source_id=source_id_for_install,
            source_cost=cost,
            source_name=source_name,
        )
    except InstallError as e:
        await wait_msg.delete()
        err = str(e)
        if err == "insufficient_seeds":
            msg = "🌱 <b>رصيد غير كافٍ.</b>\n\nالبذور نقصت. اشحن رصيدك وحاول مجدداً."
        elif err == "duplicate_token":
            msg = "⚠️ <b>هذا البوت مسجّل مسبقاً.</b>\n\nلا يمكن تثبيت نفس البوت مرتين."
        elif err == "bot_limit_reached":
            msg = (
                f"🚫 <b>وصلت للحد الأقصى!</b>\n\n"
                f"يمكنك تثبيت <b>{MAX_BOTS_FREE} بوتات</b> كحد أقصى في الخطة المجانية.\n\n"
                f"احذف أحد بوتاتك الحالية أو قم بترقية خطتك لإضافة المزيد."
            )
        elif err == "source_already_installed":
            msg = (
                f"✋ <b>لديك نسخة مثبّتة مسبقاً من هذا السورس.</b>\n\n"
                "كل سورس يُسمح بنسخة واحدة فقط لكل مستخدم."
            )
        else:
            msg = "❌ حدث خطأ أثناء التثبيت. حاول مجدداً."
        await message.answer(msg, reply_markup=_cancel_kb(), parse_mode="HTML")
        return
    except Exception as e:
        logger.error("install_bot error: %s", e)
        await wait_msg.delete()
        await message.answer(
            "❌ حدث خطأ غير متوقع. حاول مجدداً لاحقاً.",
            reply_markup=_cancel_kb(),
            parse_mode="HTML",
        )
        return

    # ── Consume coupon benefit after successful install ───────────────────────
    if benefit_type == "free_install":
        await consume_free_install(tg_id)
    elif benefit_type == "discount":
        await consume_discount(tg_id)

    await state.clear()
    await wait_msg.delete()

    seeds_left   = await get_user_seeds(tg_id)
    db_user      = await get_user(tg_id)
    free_left    = db_user.free_installs if db_user else 0
    discount_pct = db_user.discount_pct if db_user else 0

    # ── Build success card ────────────────────────────────────────────────────
    benefit_line = ""
    if benefit_type == "free_install":
        benefit_line = f"\n📦 <b>تثبيتات مجانية متبقية:</b>  <code>{free_left}</code>"
    elif benefit_type == "discount":
        benefit_line = "\n🏷 <i>تم استهلاك الخصم</i>"
    elif benefit_type == "admin":
        benefit_line = "\n🛡 <i>تثبيت أدمن مجاني</i>"

    await message.answer(
        f"✅ <b>تم التثبيت بنجاح!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 <b>البوت:</b>       @{bot_username}\n"
        f"📛 <b>الاسم:</b>       {bot_first_name}\n"
        f"📦 <b>السورس:</b>      {source_name}\n"
        f"🌱 <b>خُصم:</b>        <code>{cost:,} بذرة</code>\n"
        f"💰 <b>رصيدك الآن:</b>  <code>{seeds_left:,} بذرة</code>"
        f"{benefit_line}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 البوت مسجَّل! أدِره من ☰ Menu ← 👤 Profile ← 🤖 بوتاتي.",
        reply_markup=_installed_kb(),
        parse_mode="HTML",
    )
    logger.info(
        "Install complete: tg_id=%s bot=@%s source=%s benefit=%s cost=%s",
        tg_id, bot_username, source_name, benefit_type, cost,
    )
