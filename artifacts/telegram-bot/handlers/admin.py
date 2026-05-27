import json
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import ADMIN_IDS, WEBHOOK_HOST, RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW
from services.stats_service import get_platform_stats, get_recent_users
from services.user_service import add_seeds, get_user
from services.audit_service import log_action, get_recent_logs

logger = logging.getLogger(__name__)
router = Router(name="admin")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


# ── Keyboards ─────────────────────────────────────────────────────────────────

def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 الإحصائيات",     callback_data="adm_stats"),
                InlineKeyboardButton(text="🤖 البوتات",         callback_data="adm_bots"),
            ],
            [
                InlineKeyboardButton(text="👥 المستخدمون",      callback_data="adm_users"),
                InlineKeyboardButton(text="📋 سجل الأدمن",      callback_data="adm_audit"),
            ],
            [
                InlineKeyboardButton(text="⚙️ النظام",          callback_data="adm_system"),
                InlineKeyboardButton(text="🔄 تحديث",            callback_data="adm_refresh"),
            ],
        ]
    )


def _back_to_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 لوحة الأدمن", callback_data="adm_refresh"),
    ]])


# ── Stats formatter ───────────────────────────────────────────────────────────

def _format_stats(s: dict) -> str:
    top = ""
    for row in s["top_referrers"]:
        name  = row[0]
        uname = f"@{row[1]}" if row[1] else f"id:{row[2]}"
        count = row[3]
        if count > 0:
            top += f"  • {name} ({uname}) — <b>{count}</b>\n"

    top_section = (
        "\n🏅 <b>أكثر المحيلين:</b>\n" + top
        if top else "\n🏅 <b>أكثر المحيلين:</b> لا توجد إحالات بعد\n"
    )

    return (
        "🛡 <b>لوحة الأدمن — SourceFarm</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "👥 <b>المستخدمون:</b>\n"
        f"  • الإجمالي:          <b>{s['total_users']:,}</b>\n"
        f"  • نشطون (24 ساعة): <b>{s['active_24h']}</b>\n"
        f"  • جدد اليوم:         <b>{s['new_today']}</b>\n"
        f"  • جدد هذا الأسبوع:  <b>{s['new_week']}</b>\n\n"
        "🤖 <b>البوتات:</b>\n"
        f"  • الإجمالي:  <b>{s['total_bots']:,}</b>\n"
        f"  • شغّالة:    <b>{s['running_bots']}</b>\n"
        f"  • جديدة اليوم: <b>{s['bots_today']}</b>\n\n"
        "🌱 <b>البذور:</b>\n"
        f"  • إجمالي الموزَّع: <b>{s['total_seeds']:,} بذرة</b>\n"
        f"  ≈ <b>{s['total_seeds'] / 100:.2f}$</b>\n\n"
        "🔗 <b>الإحالات:</b>\n"
        f"  • مستخدمون مُحالون: <b>{s['total_referrals']}</b>\n"
        f"{top_section}"
        "\n━━━━━━━━━━━━━━━━━\n"
        "💡 الأوامر: /addseeds  /giveme"
    )


# ── /admin ────────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await log_action(message.from_user.id, "admin_panel_open")
    logger.info("Admin panel accessed by tg_id=%s", message.from_user.id)
    stats = await get_platform_stats()
    await message.answer(_format_stats(stats), reply_markup=admin_panel_kb(), parse_mode="HTML")


# ── /giveme ───────────────────────────────────────────────────────────────────

@router.message(Command("giveme"))
async def cmd_giveme(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    parts  = message.text.strip().split()
    amount = 10_000
    if len(parts) >= 2 and parts[1].isdigit():
        amount = int(parts[1])
    user = await add_seeds(message.from_user.id, amount)
    if not user:
        await message.answer("❌ لم يُعثر على حسابك في DB — أرسل /start أولاً.")
        return
    await log_action(
        message.from_user.id, "giveme",
        target_id=message.from_user.id,
        details={"amount": amount, "balance": user.points},
    )
    await message.answer(
        f"✅ <b>تمت إضافة {amount:,} بذرة إلى حسابك.</b>\n\n"
        f"🌱 رصيدك الآن: <code>{user.points:,} بذرة</code>",
        parse_mode="HTML",
    )
    logger.info("giveme: admin tg_id=%s +%s seeds → balance=%s", message.from_user.id, amount, user.points)


# ── /addseeds ─────────────────────────────────────────────────────────────────

@router.message(Command("addseeds"))
async def cmd_addseeds(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 3 or not parts[1].lstrip("-").isdigit() or not parts[2].isdigit():
        await message.answer(
            "⚙️ <b>الاستخدام:</b>\n"
            "<code>/addseeds &lt;telegram_id&gt; &lt;amount&gt;</code>\n\n"
            "مثال: <code>/addseeds 123456789 500</code>",
            parse_mode="HTML",
        )
        return
    target_id = int(parts[1])
    amount    = int(parts[2])
    target    = await get_user(target_id)
    if not target:
        await message.answer(
            f"❌ المستخدم <code>{target_id}</code> غير موجود في قاعدة البيانات.",
            parse_mode="HTML",
        )
        return
    user = await add_seeds(target_id, amount)
    await log_action(
        message.from_user.id, "addseeds",
        target_id=target_id,
        details={"amount": amount, "balance": user.points, "target_name": target.first_name},
    )
    await message.answer(
        f"✅ <b>تمت إضافة {amount:,} بذرة للمستخدم {target.first_name}.</b>\n\n"
        f"🌱 رصيده الآن: <code>{user.points:,} بذرة</code>",
        parse_mode="HTML",
    )
    logger.info("addseeds: admin→tg_id=%s +%s seeds → balance=%s", target_id, amount, user.points)


# ── Callbacks ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.in_({"adm_stats", "adm_refresh"}))
async def adm_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("🚫 غير مصرح", show_alert=True)
        return
    stats = await get_platform_stats()
    await callback.message.edit_text(_format_stats(stats), reply_markup=admin_panel_kb(), parse_mode="HTML")
    await callback.answer("✅ تم التحديث")


@router.callback_query(F.data == "adm_users")
async def adm_users(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("🚫 غير مصرح", show_alert=True)
        return
    users = await get_recent_users(limit=8)
    lines = ["👥 <b>آخر المستخدمين المسجَّلين:</b>\n"]
    for u in users:
        uname = f"@{u.username}" if u.username else f"id:{u.telegram_id}"
        date  = u.created_at.strftime("%d/%m %H:%M") if u.created_at else "—"
        seen  = u.last_seen.strftime("%d/%m %H:%M") if u.last_seen else "—"
        ref   = " 🔗" if u.referred_by else ""
        lines.append(
            f"• <b>{u.first_name}</b> ({uname}){ref}\n"
            f"  🌱 {u.points:,} بذرة  |  📅 {date}  |  👁 {seen}\n"
        )
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=_back_to_admin_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "adm_bots")
async def adm_bots(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("🚫 غير مصرح", show_alert=True)
        return
    from database.models import Bot
    from database.session import async_session_maker
    from sqlalchemy import select
    async with async_session_maker() as session:
        result = await session.execute(
            select(Bot).order_by(Bot.created_at.desc()).limit(10)
        )
        bots = result.scalars().all()
    lines = ["🤖 <b>آخر البوتات المثبّتة:</b>\n"]
    if not bots:
        lines.append("لا توجد بوتات بعد.")
    for b in bots:
        status = "🟢" if b.is_running else "🔴"
        date   = b.created_at.strftime("%d/%m %H:%M") if b.created_at else "—"
        lines.append(f"{status} <b>{b.name}</b>  |  📅 {date}\n")
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=_back_to_admin_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "adm_audit")
async def adm_audit(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("🚫 غير مصرح", show_alert=True)
        return
    logs = await get_recent_logs(limit=12)
    lines = ["📋 <b>سجل عمليات الأدمن:</b>\n"]
    if not logs:
        lines.append("لا توجد عمليات مسجَّلة بعد.")
    for entry in logs:
        dt      = entry.created_at.strftime("%d/%m %H:%M") if entry.created_at else "—"
        target  = f" → <code>{entry.target_id}</code>" if entry.target_id else ""
        details = ""
        if entry.details:
            try:
                d = json.loads(entry.details)
                details = "  " + "  ".join(f"{k}={v}" for k, v in d.items())
            except Exception:
                details = f"  {entry.details[:40]}"
        lines.append(
            f"• <b>{entry.action}</b>{target}\n"
            f"  👤 <code>{entry.admin_id}</code>  |  🕐 {dt}\n"
            f"{details}\n"
        )
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=_back_to_admin_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "adm_system")
async def adm_system(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("🚫 غير مصرح", show_alert=True)
        return

    mode      = "Webhook 🌐" if WEBHOOK_HOST else "Polling 🔄"
    hook_line = f"<code>{WEBHOOK_HOST}/webhook/…</code>" if WEBHOOK_HOST else "<i>غير مفعّل</i>"
    admin_ids = ", ".join(f"<code>{a}</code>" for a in ADMIN_IDS) or "—"

    text = (
        "⚙️ <b>معلومات النظام</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"📡 <b>وضع الاستقبال:</b>  {mode}\n"
        f"🔗 <b>Webhook URL:</b>\n   {hook_line}\n\n"
        f"⚡ <b>Rate Limit:</b>\n"
        f"   {RATE_LIMIT_MESSAGES} رسالة / {RATE_LIMIT_WINDOW}ث\n\n"
        f"🛡 <b>المشرفون:</b>  {admin_ids}\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "<i>Python 3.12 | aiogram 3 | PostgreSQL | SQLAlchemy 2</i>"
    )
    await callback.message.edit_text(text, reply_markup=_back_to_admin_kb(), parse_mode="HTML")
    await callback.answer()
