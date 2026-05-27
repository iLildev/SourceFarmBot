import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from config import ADMIN_IDS

logger = logging.getLogger(__name__)
router = Router(name="report")


class ReportStates(StatesGroup):
    waiting_description = State()
    waiting_screenshot   = State()


# ── Keyboards ──────────────────────────────────────────────────────────────────

def _skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏭ تخطى",  callback_data="report_skip"),
        InlineKeyboardButton(text="❌ إلغاء", callback_data="report_cancel"),
    ]])


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ إلغاء", callback_data="report_cancel"),
    ]])


def _back_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_main"),
    ]])


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _extract_media(message: Message) -> tuple[str, str | None]:
    if message.photo:
        return message.caption or "(صورة بدون وصف)", message.photo[-1].file_id
    if message.video:
        return message.caption or "(فيديو)", None
    if message.document:
        fname = message.document.file_name or "ملف"
        return message.caption or f"(ملف: {fname})", None
    if message.sticker:
        return f"(ستيكر: {message.sticker.emoji or ''})", None
    if message.voice or message.audio:
        return "(رسالة صوتية)", None
    return message.text or "(رسالة غير معروفة)", None


def _replied_summary(replied: Message) -> str:
    if replied.text:
        return f"📩 ردّاً على رسالة:\n«{replied.text[:200]}»"
    if replied.caption:
        return f"📎 ردّاً على رسالة (مع ميديا):\n«{replied.caption[:200]}»"
    if replied.photo:
        return "📎 ردّاً على: صورة"
    if replied.video:
        return "📎 ردّاً على: فيديو"
    if replied.document:
        return f"📎 ردّاً على: ملف ({replied.document.file_name or ''})"
    if replied.sticker:
        return f"📎 ردّاً على: ستيكر {replied.sticker.emoji or ''}"
    return "📎 ردّاً على رسالة"


async def _notify_admins(
    bot: Bot,
    user_id: int,
    user_name: str,
    description: str,
    screenshot_id: str | None,
) -> None:
    header = (
        f"🚨 <b>بلاغ جديد — SourceFarm</b>\n"
        f"👤 <b>{user_name}</b>  <code>[{user_id}]</code>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"{description}"
    )
    for admin_id in ADMIN_IDS:
        try:
            if screenshot_id:
                await bot.send_photo(admin_id, photo=screenshot_id, caption=header, parse_mode="HTML")
            else:
                await bot.send_message(admin_id, header, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Could not notify admin %s: %s", admin_id, exc)


async def _finish_report(
    bot: Bot,
    chat_id: int,
    user_id: int,
    user_name: str,
    description: str,
    screenshot_id: str | None = None,
) -> None:
    await _notify_admins(bot, user_id, user_name, description, screenshot_id)
    await bot.send_message(
        chat_id,
        "✅ <b>تم إرسال بلاغك بنجاح!</b>\n\n"
        "📋 سيراجعه الفريق خلال <b>24 ساعة</b>.\n"
        "شكراً على مساعدتك في تحسين المنصة 🙏",
        reply_markup=_back_to_main_kb(),
        parse_mode="HTML",
    )
    logger.info("Report from tg_id=%s: %s", user_id, description[:120])


# ── /report command ────────────────────────────────────────────────────────────

@router.message(Command("report"))
async def cmd_report(message: Message, state: FSMContext, bot: Bot) -> None:
    user      = message.from_user
    user_name = user.first_name or "مستخدم"

    if message.reply_to_message:
        summary     = _replied_summary(message.reply_to_message)
        args        = (message.text or "").strip().split(maxsplit=1)
        extra       = args[1] if len(args) > 1 else ""
        description = f"{summary}\n{extra}".strip() if extra else summary
        await state.update_data(description=description, user_id=user.id, user_name=user_name)
        await state.set_state(ReportStates.waiting_screenshot)
        await message.answer(
            f"<b>البلاغ:</b>\n{description}\n\n"
            "📸 أرسل <b>screenshot</b> للمشكلة إن وجد (اختياري)",
            reply_markup=_skip_kb(), parse_mode="HTML",
        )
        return

    args = (message.text or "").strip().split(maxsplit=1)
    if len(args) > 1:
        await _finish_report(bot, message.chat.id, user.id, user_name, args[1])
        return

    if message.photo or message.video or message.document:
        description, screenshot_id = _extract_media(message)
        await _finish_report(bot, message.chat.id, user.id, user_name, description, screenshot_id)
        return

    await state.set_state(ReportStates.waiting_description)
    await message.answer(
        "🚨 <b>الإبلاغ عن مشكلة</b>\n\n"
        "صِف المشكلة بالتفصيل ✍️\n\n"
        "<i>يمكنك إرسال نص أو صورة أو فيديو أو ملف</i>",
        reply_markup=_cancel_kb(), parse_mode="HTML",
    )


# ── Step 1: receive description ────────────────────────────────────────────────

@router.message(ReportStates.waiting_description)
async def receive_description(message: Message, state: FSMContext, bot: Bot) -> None:
    user                     = message.from_user
    description, screenshot_id = _extract_media(message)
    if screenshot_id:
        await state.clear()
        await _finish_report(bot, message.chat.id, user.id, user.first_name or "مستخدم", description, screenshot_id)
        return
    await state.update_data(description=description, user_id=user.id, user_name=user.first_name or "مستخدم")
    await state.set_state(ReportStates.waiting_screenshot)
    await message.answer(
        "📸 أرسل <b>screenshot</b> للمشكلة إن وجد (اختياري)",
        reply_markup=_skip_kb(), parse_mode="HTML",
    )


# ── Step 2: receive screenshot (or skip) ──────────────────────────────────────

@router.message(ReportStates.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext, bot: Bot) -> None:
    data          = await state.get_data()
    screenshot_id = message.photo[-1].file_id
    await state.clear()
    await _finish_report(
        bot, message.chat.id,
        data["user_id"], data["user_name"],
        data.get("description", ""), screenshot_id,
    )


@router.message(ReportStates.waiting_screenshot)
async def screenshot_wrong_type(message: Message) -> None:
    await message.answer(
        "📸 من فضلك أرسل <b>صورة</b>، أو اضغط <b>تخطى</b> لإرسال البلاغ بدون screenshot.",
        reply_markup=_skip_kb(), parse_mode="HTML",
    )


# ── Inline callbacks ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "report_skip")
async def skip_screenshot(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await _finish_report(
        bot, callback.message.chat.id,
        data.get("user_id", callback.from_user.id),
        data.get("user_name", callback.from_user.first_name or "مستخدم"),
        data.get("description", ""),
    )
    await callback.answer()


@router.callback_query(F.data == "report_cancel")
async def cancel_report(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ تم إلغاء البلاغ.",
        reply_markup=_back_to_main_kb(),
    )
    await callback.answer()
