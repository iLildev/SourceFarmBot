import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.mode_kb import (
    mode_select_kb,
    studio_mode_kb,
    realdev_mode_kb,
    user_mode_kb,
    back_to_mode_kb,
    back_to_realdev_kb,
)
from services.bot_service import get_user_bots

logger = logging.getLogger(__name__)
router = Router(name="mode")

MODE_TEXT = (
    "⚡ <b>اختر وضع التشغيل</b>\n\n"
    "🧩 <b>Admin Mode</b>\n"
    "   واجهة بسيطة لإدارة البوتات بدون كود\n\n"
    "⚡ <b>Dev Mode</b>\n"
    "   واجهة احترافية للمطورين مع أدوات متقدمة\n\n"
    "👤 <b>User Mode</b>\n"
    "   عايش تجربة مستخدميك — شوف البوت من عينهم"
)


@router.message(F.text == "⚡ Mode")
async def show_mode_msg(message: Message) -> None:
    await message.answer(MODE_TEXT, reply_markup=mode_select_kb(), parse_mode="HTML")


@router.callback_query(F.data == "mode")
async def show_mode(callback: CallbackQuery) -> None:
    await callback.message.edit_text(MODE_TEXT, reply_markup=mode_select_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "mode_studio")
async def show_studio(callback: CallbackQuery) -> None:
    text = (
        "🧩 <b>Admin Mode</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "وضع بدون كود — أدِر بوتاتك بنقرة واحدة."
    )
    await callback.message.edit_text(text, reply_markup=studio_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "mode_realdev")
async def show_realdev(callback: CallbackQuery) -> None:
    text = (
        "⚡ <b>Dev Mode</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "وضع المطورين المتقدم — تحكم كامل في كل شيء."
    )
    await callback.message.edit_text(text, reply_markup=realdev_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "studio_bots")
async def studio_bots(callback: CallbackQuery) -> None:
    bots = await get_user_bots(callback.from_user.id)

    if not bots:
        text = (
            "🤖 <b>Active Bots</b>\n\n"
            "لا يوجد لديك بوتات مثبّتة بعد.\n\n"
            "📦 تصفّح <b>🌲 Source Tree</b> واختر سورساً لتثبيته."
        )
    else:
        lines = ["🤖 <b>Active Bots</b>\n"]
        for bot in bots:
            icon  = "🟢" if bot.is_running else "🔴"
            mode  = "Admin" if bot.mode == "studio" else "Dev"
            lines.append(f"{icon} <b>{bot.name}</b>  <i>({mode})</i>")
        lines.append("\n<i>إدارة الإضافات وتشغيل البوتات فعلياً — قريباً</i>")
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=back_to_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "studio_settings")
async def studio_settings(callback: CallbackQuery) -> None:
    text = (
        "⚙️ <b>Quick Settings</b>\n\n"
        "🔔 الإشعارات:      <b>مفعّل</b>\n"
        "🌐 اللغة:          <b>العربية</b>\n"
        "🕐 المنطقة الزمنية: <b>Asia/Riyadh</b>\n"
        "🛡 وضع الأمان:     <b>عالي</b>\n\n"
        "<i>التعديل على الإعدادات قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "studio_status")
async def studio_status(callback: CallbackQuery) -> None:
    bots    = await get_user_bots(callback.from_user.id)
    running = sum(1 for b in bots if b.is_running)
    total   = len(bots)

    text = (
        "🟢 <b>Bot Status</b>\n\n"
        f"البوتات المسجّلة: <b>{total}</b>\n"
        f"شغّالة الآن:      <b>{running}</b>\n"
        f"متوقفة:           <b>{total - running}</b>\n\n"
        "<i>مراقبة البوتات في الوقت الفعلي — قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "dev_runtime")
async def dev_runtime(callback: CallbackQuery) -> None:
    import sys
    import platform
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    text = (
        "🖥 <b>Runtime</b>\n\n"
        f"<code>Python       {py_ver}</code>\n"
        "<code>aiogram      3.13.1</code>\n"
        "<code>SQLAlchemy   2.0.36</code>\n"
        "<code>asyncpg      0.30.0</code>\n\n"
        f"<code>Platform:    {platform.system()} {platform.machine()}</code>\n"
        "<i>مراقبة الموارد (CPU/RAM) — قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "dev_plugins")
async def dev_plugins(callback: CallbackQuery) -> None:
    bots  = await get_user_bots(callback.from_user.id)
    total = len(bots)
    text = (
        "🔌 <b>Plugins</b>\n\n"
        f"البوتات المسجّلة: <b>{total}</b>\n\n"
        "<i>نظام الإضافات والبلاجنز قيد التطوير — قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "dev_logs")
async def dev_logs(callback: CallbackQuery) -> None:
    import html as _html
    from runtime.log_buffer import get_log_buffer

    bots = await get_user_bots(callback.from_user.id)

    if not bots:
        text = (
            "📋 <b>Logs</b>\n\n"
            "لا يوجد لديك بوتات مثبّتة بعد.\n\n"
            "<i>ثبّت سورساً من 🌲 Source Tree لرؤية السجلات هنا.</i>"
        )
    else:
        buf   = get_log_buffer()
        lines = buf.get_for_bots([b.id for b in bots], limit=20)

        if not lines:
            body = "<i>لا توجد سجلات بعد — البوت لم يُشغَّل أو لم يُنتج أي سجلات.</i>"
        else:
            safe = [_html.escape(ln) for ln in lines]
            body = "\n".join(f"<code>{ln}</code>" for ln in safe)

        bot_names = "، ".join(b.name for b in bots[:3])
        text = (
            f"📋 <b>Live Logs</b>\n"
            f"<i>{_html.escape(bot_names)}</i>\n"
            f"━━━━━━━━━━━━━━━━━\n\n"
            f"{body}"
        )

    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "dev_events")
async def dev_events(callback: CallbackQuery) -> None:
    text = (
        "⚡ <b>Events</b>\n\n"
        "مراقبة الأحداث والـ Webhooks لبوتاتك\n\n"
        "<i>هذه الميزة قيد التطوير — قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "dev_variables")
async def dev_variables(callback: CallbackQuery) -> None:
    text = (
        "📦 <b>Variables</b>\n\n"
        "<code>BOT_TOKEN      = ****hidden****</code>\n"
        "<code>DATABASE_URL   = ****hidden****</code>\n"
        "<code>LOG_LEVEL      = INFO</code>\n\n"
        "<i>إدارة متغيرات بوتاتك — قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


# ── User Mode ──────────────────────────────────────────────────────────────────

def _back_to_user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 الرجوع", callback_data="mode_user")],
    ])


@router.callback_query(F.data == "mode_user")
async def show_user_mode(callback: CallbackQuery) -> None:
    text = (
        "👤 <b>User Mode</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "شوف بوتك من عين مستخدميك —\n"
        "اعرف كيف يبدو لهم وتحكم فيهم."
    )
    await callback.message.edit_text(text, reply_markup=user_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "user_preview")
async def user_preview(callback: CallbackQuery) -> None:
    bots = await get_user_bots(callback.from_user.id)
    if not bots:
        text = (
            "🔍 <b>معاينة البوت</b>\n\n"
            "ليس لديك بوتات مثبّتة بعد.\n\n"
            "📦 ثبّت سورساً من <b>🌲 Source Tree</b> أولاً."
        )
    else:
        lines = [
            "🔍 <b>معاينة البوت</b>\n\n"
            "اختر بوتاً لترى كيف يبدو لمستخدميك:\n"
        ]
        for bot in bots:
            icon = "🟢" if bot.is_running else "🔴"
            lines.append(f"{icon} <b>{bot.name}</b>  <code>@{bot.username or '—'}</code>")
        lines.append("\n<i>محاكاة تجربة المستخدم الكاملة — قريباً</i>")
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=_back_to_user_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "user_list")
async def user_list(callback: CallbackQuery) -> None:
    text = (
        "👥 <b>قائمة المستخدمين</b>\n\n"
        "هنا تظهر قائمة بمستخدمي بوتاتك:\n"
        "الاسم، تاريخ الانضمام، آخر نشاط، وحالة الحظر.\n\n"
        "<i>هذه الميزة قيد التطوير — قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=_back_to_user_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "user_broadcast")
async def user_broadcast(callback: CallbackQuery) -> None:
    text = (
        "📨 <b>بث رسالة</b>\n\n"
        "أرسل رسالة لجميع مستخدمي بوتاتك دفعة واحدة.\n\n"
        "• نص / صورة / فيديو\n"
        "• جدولة الإرسال بوقت محدد\n"
        "• استهداف مجموعة بعينها\n\n"
        "<i>هذه الميزة قيد التطوير — قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=_back_to_user_kb(), parse_mode="HTML")
    await callback.answer()
