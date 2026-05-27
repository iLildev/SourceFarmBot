import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import ADMIN_IDS
from services.stats_service import get_platform_stats, get_recent_users
from services.user_service import add_seeds, get_user

logger = logging.getLogger(__name__)
router = Router(name="admin")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 الإحصائيات",     callback_data="adm_stats")],
            [InlineKeyboardButton(text="👥 آخر المستخدمين", callback_data="adm_users")],
            [InlineKeyboardButton(text="🔄 تحديث",          callback_data="adm_refresh")],
        ]
    )


def _format_stats(s: dict) -> str:
    top = ""
    for row in s["top_referrers"]:
        name  = row[0]
        uname = f"@{row[1]}" if row[1] else f"id:{row[2]}"
        count = row[3]
        if count > 0:
            top += f"  • {name} ({uname}) — <b>{count}</b> إحالة\n"

    top_section = (
        "\n🏅 <b>أكثر المحيلين:</b>\n" + top
        if top else "\n🏅 <b>أكثر المحيلين:</b> لا توجد إحالات بعد\n"
    )

    return (
        "🛡 <b>لوحة الأدمن — SourceFarm</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "👥 <b>المستخدمون:</b>\n"
        f"  • الإجمالي:        <b>{s['total_users']:,}</b>\n"
        f"  • جدد اليوم:       <b>{s['new_today']}</b>\n"
        f"  • جدد هذا الأسبوع: <b>{s['new_week']}</b>\n\n"
        "🌱 <b>البذور:</b>\n"
        f"  • إجمالي الموزَّع: <b>{s['total_seeds']:,} بذرة</b>\n"
        f"  ≈ <b>{s['total_seeds'] / 100:.2f}$</b>\n\n"
        "🔗 <b>الإحالات:</b>\n"
        f"  • مستخدمون مُحالون: <b>{s['total_referrals']}</b>\n"
        f"{top_section}"
        "\n━━━━━━━━━━━━━━━━━\n"
        "💡 الأوامر: /addseeds — /giveme"
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    logger.info("Admin panel accessed by tg_id=%s", message.from_user.id)
    stats = await get_platform_stats()
    await message.answer(_format_stats(stats), reply_markup=admin_panel_kb(), parse_mode="HTML")


@router.message(Command("giveme"))
async def cmd_giveme(message: Message) -> None:
    """Admin only — give yourself seeds. Usage: /giveme [amount]"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    amount = 10_000
    if len(parts) >= 2 and parts[1].isdigit():
        amount = int(parts[1])
    user = await add_seeds(message.from_user.id, amount)
    if not user:
        await message.answer("❌ لم يُعثر على حسابك في DB — أرسل /start أولاً.")
        return
    await message.answer(
        f"✅ <b>تمت إضافة {amount:,} بذرة إلى حسابك.</b>\n\n"
        f"🌱 رصيدك الآن: <code>{user.points:,} بذرة</code>",
        parse_mode="HTML",
    )
    logger.info("giveme: admin tg_id=%s +%s seeds → balance=%s", message.from_user.id, amount, user.points)


@router.message(Command("addseeds"))
async def cmd_addseeds(message: Message) -> None:
    """Admin only — add seeds to any user. Usage: /addseeds <tg_id> <amount>"""
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
        await message.answer(f"❌ المستخدم <code>{target_id}</code> غير موجود في قاعدة البيانات.", parse_mode="HTML")
        return
    user = await add_seeds(target_id, amount)
    name = target.first_name
    await message.answer(
        f"✅ <b>تمت إضافة {amount:,} بذرة للمستخدم {name}.</b>\n\n"
        f"🌱 رصيده الآن: <code>{user.points:,} بذرة</code>",
        parse_mode="HTML",
    )
    logger.info("addseeds: admin→tg_id=%s +%s seeds → balance=%s", target_id, amount, user.points)


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
        ref   = " 🔗" if u.referred_by else ""
        lines.append(
            f"• <b>{u.first_name}</b> ({uname}){ref}\n"
            f"  🌱 {u.points:,} بذرة  |  📅 {date}\n"
        )
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة", callback_data="adm_stats")]]
    )
    await callback.message.edit_text("\n".join(lines), reply_markup=back_kb, parse_mode="HTML")
    await callback.answer()
