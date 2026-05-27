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
)
from keyboards.main_kb import main_menu_kb

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
            [InlineKeyboardButton(text="🌲 تصفح المزيد", callback_data="source_tree")],
            [InlineKeyboardButton(text="🔙 الرئيسية",    callback_data="back_main")],
        ]
    )


@router.callback_query(F.data.startswith("install_") & ~F.data.in_({"install_cancel"}))
async def start_install(callback: CallbackQuery, state: FSMContext) -> None:
    source_id = int(callback.data.split("_")[-1])
    source = next((s for s in SOURCES if s["id"] == source_id), None)

    if not source:
        await callback.answer("المصدر غير موجود", show_alert=True)
        return

    cost = source["points"]
    seeds = await get_user_seeds(callback.from_user.id)

    if seeds < cost:
        shortage = cost - seeds
        await callback.answer(
            f"🌱 رصيدك غير كافٍ!\n\n"
            f"السعر:   {cost:,} بذرة\n"
            f"رصيدك:  {seeds:,} بذرة\n"
            f"يُنقصك: {shortage:,} بذرة",
            show_alert=True,
        )
        return

    await state.set_state(InstallStates.waiting_for_token)
    await state.update_data(source_id=source_id, source_name=source["name"], cost=cost)

    await callback.message.answer(
        f"📦 <b>تثبيت: {source['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷  الفئة:   {source['category']}\n"
        f"🌱 السعر:   <code>{cost:,} بذرة</code>\n"
        f"💰 رصيدك:  <code>{seeds:,} بذرة</code>\n\n"
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

    data = await state.get_data()
    source_id: int  = data["source_id"]
    source_name: str = data["source_name"]
    cost: int        = data["cost"]
    tg_id = message.from_user.id

    bot_username = bot_info.get("username", "")
    bot_first_name = bot_info.get("first_name", source_name)

    try:
        saved_bot = await install_bot(
            telegram_id=tg_id,
            token=token,
            bot_name=bot_first_name,
            source_cost=cost,
            source_name=source_name,
        )
    except InstallError as e:
        await wait_msg.delete()
        err = str(e)
        if err == "insufficient_seeds":
            await message.answer(
                "🌱 <b>رصيد غير كافٍ.</b>\n\nالبذور نقصت بعد التحقق. اشحن رصيدك وحاول مجدداً.",
                reply_markup=_cancel_kb(),
                parse_mode="HTML",
            )
        elif err == "duplicate_token":
            await message.answer(
                "⚠️ <b>هذا البوت مسجّل مسبقاً.</b>\n\nلا يمكن تثبيت نفس البوت مرتين.",
                reply_markup=_cancel_kb(),
                parse_mode="HTML",
            )
        else:
            await message.answer(
                "❌ حدث خطأ أثناء التثبيت. حاول مجدداً.",
                reply_markup=_cancel_kb(),
                parse_mode="HTML",
            )
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

    await state.clear()
    await wait_msg.delete()

    seeds_left = await get_user_seeds(tg_id)

    await message.answer(
        f"✅ <b>تم التثبيت بنجاح!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 <b>البوت:</b>       @{bot_username}\n"
        f"📛 <b>الاسم:</b>       {bot_first_name}\n"
        f"📦 <b>السورس:</b>      {source_name}\n"
        f"🌱 <b>خُصم:</b>        <code>{cost:,} بذرة</code>\n"
        f"💰 <b>رصيدك الآن:</b>  <code>{seeds_left:,} بذرة</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 بوتك جاهز! يمكنك الآن إدارته من ⚡ Mode.",
        reply_markup=_installed_kb(),
        parse_mode="HTML",
    )
    logger.info("Install complete: tg_id=%s bot=@%s source=%s", tg_id, bot_username, source_name)
