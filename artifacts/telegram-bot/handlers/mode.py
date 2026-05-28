import json
import logging
import platform
import sys

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from data.sources import SOURCES
from keyboards.mode_kb import (
    mode_select_kb,
    studio_mode_kb,
    realdev_mode_kb,
    user_mode_kb,
    back_to_mode_kb,
    back_to_realdev_kb,
)
from services.bot_service import get_user_bots
from services.bot_config_service import get_schema, parse_config, resolve, toggle

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

# ── Source name lookup ────────────────────────────────────────────────────────
_SOURCE_NAMES: dict[int, str] = {s["id"]: s["name"] for s in SOURCES}


def _source_name(source_id: int | None) -> str:
    if source_id is None:
        return "غير معروف"
    return _SOURCE_NAMES.get(source_id, f"Source #{source_id}")


# ── Mode entry points ─────────────────────────────────────────────────────────

@router.message(F.text == "⚡ Mode")
async def show_mode_msg(message: Message) -> None:
    await message.answer(MODE_TEXT, reply_markup=mode_select_kb(), parse_mode="HTML")


@router.callback_query(F.data == "mode")
async def show_mode(callback: CallbackQuery) -> None:
    await callback.message.edit_text(MODE_TEXT, reply_markup=mode_select_kb(), parse_mode="HTML")
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
#  🧩  ADMIN MODE (Studio)
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "mode_studio")
async def show_studio(callback: CallbackQuery) -> None:
    text = (
        "🧩 <b>Admin Mode</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "وضع بدون كود — أدِر بوتاتك بنقرة واحدة."
    )
    await callback.message.edit_text(text, reply_markup=studio_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "studio_bots")
async def studio_bots(callback: CallbackQuery) -> None:
    bots = await get_user_bots(callback.from_user.id)

    if not bots:
        text = (
            "🤖 <b>بوتاتي</b>\n\n"
            "لا يوجد لديك بوتات مثبّتة بعد.\n\n"
            "📦 تصفّح <b>🌲 Source Tree</b> واختر سورساً لتثبيته."
        )
        await callback.message.edit_text(text, reply_markup=back_to_mode_kb(), parse_mode="HTML")
    else:
        lines = ["🤖 <b>بوتاتي</b>\n"]
        for bot in bots:
            icon   = "🟢" if bot.is_running else "🔴"
            source = _source_name(bot.source_id)
            uname  = f"@{bot.username}" if bot.username else bot.name
            lines.append(f"{icon} <b>{uname}</b>  <i>({source})</i>")
        lines.append("\n<i>للتحكم بالبوتات (تشغيل/إيقاف/حذف) — افتح ☰ Menu ← 🤖 بوتاتي</i>")
        text = "\n".join(lines)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 إدارة البوتات", callback_data="menu_mybots")],
            [InlineKeyboardButton(text="🔙 الرجوع",        callback_data="mode_studio")],
        ])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "studio_status")
async def studio_status(callback: CallbackQuery) -> None:
    from runtime.bot_manager import get_manager
    bots    = await get_user_bots(callback.from_user.id)
    running = sum(1 for b in bots if b.is_running)
    total   = len(bots)
    manager = get_manager()

    lines = [
        "🟢 <b>Bot Status</b>\n",
        f"البوتات المسجّلة:  <b>{total}</b>",
        f"شغّالة الآن:       <b>{running}</b>",
        f"متوقفة:            <b>{total - running}</b>",
    ]

    if bots:
        lines.append("")
        for bot in bots:
            icon   = "🟢" if bot.is_running else "🔴"
            uname  = f"@{bot.username}" if bot.username else bot.name
            status = manager.status(bot.id)
            restarts = status.get("restarts", 0)
            rst_txt  = f"  ↩ {restarts} إعادة تشغيل" if restarts else ""
            lines.append(f"{icon} <b>{uname}</b>{rst_txt}")

    text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=back_to_mode_kb(), parse_mode="HTML")
    await callback.answer()


# ── Studio Settings (per-bot config) ─────────────────────────────────────────

def _bot_config_kb(bot_id: int, source_id: int, config: dict) -> InlineKeyboardMarkup:
    """Build a keyboard with toggle buttons for each config key."""
    schema = get_schema(source_id)
    rows = []
    for key, (label, default) in schema.items():
        val  = bool(config.get(key, default))
        icon = "✅" if val else "❌"
        rows.append([InlineKeyboardButton(
            text=f"{icon} {label}",
            callback_data=f"studio_cfg_t_{bot_id}_{key}",
        )])
    rows.append([InlineKeyboardButton(text="🔙 الرجوع", callback_data="studio_settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "studio_settings")
async def studio_settings(callback: CallbackQuery) -> None:
    bots = await get_user_bots(callback.from_user.id)

    if not bots:
        text = (
            "⚙️ <b>الإعدادات</b>\n\n"
            "ثبّت سورساً أولاً لتظهر إعداداته هنا."
        )
        await callback.message.edit_text(text, reply_markup=back_to_mode_kb(), parse_mode="HTML")
        await callback.answer()
        return

    if len(bots) == 1:
        bot    = bots[0]
        config = parse_config(bot)
        schema = get_schema(bot.source_id or 0)
        uname  = f"@{bot.username}" if bot.username else bot.name

        if not schema:
            text = (
                f"⚙️ <b>إعدادات:</b> <b>{uname}</b>\n\n"
                "لا توجد إعدادات قابلة للتخصيص لهذا السورس بعد."
            )
            await callback.message.edit_text(text, reply_markup=back_to_mode_kb(), parse_mode="HTML")
        else:
            text = (
                f"⚙️ <b>إعدادات:</b> <b>{uname}</b>\n"
                f"━━━━━━━━━━━━━━━━━\n\n"
                f"اضغط على أي خيار لتبديله — يُحفظ فوراً:"
            )
            await callback.message.edit_text(
                text,
                reply_markup=_bot_config_kb(bot.id, bot.source_id or 0, config),
                parse_mode="HTML",
            )
        await callback.answer()
        return

    # Multiple bots → selector
    rows = []
    for bot in bots:
        uname = f"@{bot.username}" if bot.username else bot.name
        icon  = "🟢" if bot.is_running else "🔴"
        rows.append([InlineKeyboardButton(
            text=f"{icon} {uname}",
            callback_data=f"studio_cfg_{bot.id}",
        )])
    rows.append([InlineKeyboardButton(text="🔙 الرجوع", callback_data="mode_studio")])

    await callback.message.edit_text(
        "⚙️ <b>إعدادات</b>\n\nاختر البوت:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("studio_cfg_") & ~F.data.startswith("studio_cfg_t_"))
async def studio_cfg_bot(callback: CallbackQuery) -> None:
    """Show config screen for a specific bot."""
    try:
        bot_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer()
        return

    bots = await get_user_bots(callback.from_user.id)
    bot  = next((b for b in bots if b.id == bot_id), None)
    if not bot:
        await callback.answer("البوت غير موجود", show_alert=True)
        return

    config = parse_config(bot)
    schema = get_schema(bot.source_id or 0)
    uname  = f"@{bot.username}" if bot.username else bot.name

    if not schema:
        await callback.answer("لا توجد إعدادات لهذا السورس بعد.", show_alert=True)
        return

    text = (
        f"⚙️ <b>إعدادات:</b> <b>{uname}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"اضغط على أي خيار لتبديله — يُحفظ فوراً:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=_bot_config_kb(bot.id, bot.source_id or 0, config),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("studio_cfg_t_"))
async def studio_cfg_toggle(callback: CallbackQuery) -> None:
    """Toggle a config key: studio_cfg_t_{bot_id}_{key}"""
    parts = callback.data.split("_", 5)
    # parts: ['studio', 'cfg', 't', bot_id, key]
    if len(parts) < 5:
        await callback.answer()
        return
    try:
        bot_id = int(parts[3])
        key    = parts[4]
    except (ValueError, IndexError):
        await callback.answer()
        return

    new_val = await toggle(bot_id, key)
    if new_val is None:
        await callback.answer("خطأ أثناء الحفظ", show_alert=True)
        return

    icon = "✅" if new_val else "❌"
    await callback.answer(f"{icon} تم الحفظ", show_alert=False)

    # Re-render the config screen
    bots = await get_user_bots(callback.from_user.id)
    bot  = next((b for b in bots if b.id == bot_id), None)
    if not bot:
        return

    config = parse_config(bot)
    uname  = f"@{bot.username}" if bot.username else bot.name
    text = (
        f"⚙️ <b>إعدادات:</b> <b>{uname}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"اضغط على أي خيار لتبديله — يُحفظ فوراً:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=_bot_config_kb(bot.id, bot.source_id or 0, config),
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ⚡  DEV MODE
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "mode_realdev")
async def show_realdev(callback: CallbackQuery) -> None:
    text = (
        "⚡ <b>Dev Mode</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "وضع المطورين المتقدم — تحكم كامل في كل شيء."
    )
    await callback.message.edit_text(text, reply_markup=realdev_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "dev_runtime")
async def dev_runtime(callback: CallbackQuery) -> None:
    from runtime.bot_manager import get_manager
    py_ver  = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    manager = get_manager()
    active  = sum(1 for s in manager.all_statuses().values() if s.get("running"))

    text = (
        "🖥 <b>Runtime</b>\n\n"
        f"<code>Python       {py_ver}</code>\n"
        "<code>aiogram      3.x</code>\n"
        "<code>SQLAlchemy   2.x</code>\n"
        "<code>asyncpg      0.x</code>\n\n"
        f"<code>Platform:    {platform.system()} {platform.machine()}</code>\n\n"
        f"<b>بوتات نشطة:</b>  <code>{active}</code>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "dev_plugins")
async def dev_plugins(callback: CallbackQuery) -> None:
    from runtime.bot_manager import get_manager
    bots    = await get_user_bots(callback.from_user.id)
    manager = get_manager()

    if not bots:
        text = (
            "🔌 <b>Plugins</b>\n\n"
            "لا يوجد لديك بوتات مثبّتة بعد.\n\n"
            "<i>ثبّت سورساً من 🌲 Source Tree لتظهر هنا.</i>"
        )
    else:
        lines = ["🔌 <b>Plugins</b>\n"]
        for bot in bots:
            icon    = "🟢" if bot.is_running else "🔴"
            uname   = f"@{bot.username}" if bot.username else bot.name
            source  = _source_name(bot.source_id)
            status  = manager.status(bot.id)
            restarts = status.get("restarts", 0)
            rst_txt  = f"  ↩ {restarts}" if restarts else ""
            lines.append(f"{icon} <b>{uname}</b>  <code>{source}</code>{rst_txt}")
        text = "\n".join(lines)

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
            body = "<i>لا توجد سجلات بعد — شغّل البوت أولاً.</i>"
        else:
            safe = [_html.escape(ln) for ln in lines]
            body = "\n".join(f"<code>{ln}</code>" for ln in safe)

        bot_names = "، ".join(
            (f"@{b.username}" if b.username else b.name) for b in bots[:3]
        )
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
    import html as _html
    from runtime.log_buffer import get_log_buffer

    bots = await get_user_bots(callback.from_user.id)

    if not bots:
        text = (
            "⚡ <b>Events</b>\n\n"
            "لا توجد بوتات مثبّتة — لا يوجد أحداث بعد."
        )
    else:
        buf   = get_log_buffer()
        lines = buf.get_for_bots([b.id for b in bots], limit=10)
        if not lines:
            body = "<i>لا أحداث بعد — شغّل البوت أولاً.</i>"
        else:
            # Keep only ERROR/WARN/INFO level lines
            safe = [_html.escape(ln) for ln in lines[-10:]]
            body = "\n".join(f"<code>{ln}</code>" for ln in safe)
        text = f"⚡ <b>Events</b>\n━━━━━━━━━━━━━━━━━\n\n{body}"

    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "dev_variables")
async def dev_variables(callback: CallbackQuery) -> None:
    bots = await get_user_bots(callback.from_user.id)
    bot_count = len(bots)
    running   = sum(1 for b in bots if b.is_running)

    text = (
        "📦 <b>Variables</b>\n\n"
        "<code>BOT_TOKEN      = ****hidden****</code>\n"
        "<code>DATABASE_URL   = ****hidden****</code>\n"
        "<code>LOG_LEVEL      = INFO</code>\n"
        f"<code>BOTS_TOTAL     = {bot_count}</code>\n"
        f"<code>BOTS_RUNNING   = {running}</code>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
#  👤  USER MODE
# ══════════════════════════════════════════════════════════════════════════════

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
        lines = ["🔍 <b>معاينة البوتات</b>\n"]
        for bot in bots:
            icon  = "🟢" if bot.is_running else "🔴"
            if bot.username:
                link = f't.me/{bot.username}'
                lines.append(
                    f"{icon} <b>{bot.name}</b>\n"
                    f"   <a href='https://{link}'>@{bot.username}</a> — اضغط لفتح البوت\n"
                )
            else:
                status = "شغّال" if bot.is_running else "متوقف"
                lines.append(f"{icon} <b>{bot.name}</b>  <i>({status})</i>\n")
        text = "\n".join(lines)
    await callback.message.edit_text(
        text, reply_markup=_back_to_user_kb(), parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data == "user_list")
async def user_list(callback: CallbackQuery) -> None:
    bots = await get_user_bots(callback.from_user.id)
    running_count = sum(1 for b in bots if b.is_running)

    text = (
        "👥 <b>مستخدمو البوت</b>\n\n"
        f"<b>بوتات شغّالة:</b>  {running_count}\n\n"
        "📊 إحصاءات المستخدمين (إجمالي الأعضاء، آخر نشاط، "
        "معدل الاحتفاظ) ستتوفر في الإصدار القادم.\n\n"
        "<i>تأكد من تشغيل بوتاتك أولاً لبدء جمع البيانات.</i>"
    )
    await callback.message.edit_text(text, reply_markup=_back_to_user_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "user_broadcast")
async def user_broadcast(callback: CallbackQuery) -> None:
    text = (
        "📨 <b>بث رسالة</b>\n\n"
        "أرسل رسالة لجميع مستخدمي بوتاتك دفعة واحدة.\n\n"
        "• نص / صورة / فيديو / ملف\n"
        "• جدولة بوقت محدد\n"
        "• استهداف مجموعة بعينها\n"
        "• معدل إرسال آمن (anti-flood)\n\n"
        "<b>ستُطلق هذه الميزة مع SF Broadcast قريباً.</b>"
    )
    await callback.message.edit_text(text, reply_markup=_back_to_user_kb(), parse_mode="HTML")
    await callback.answer()
