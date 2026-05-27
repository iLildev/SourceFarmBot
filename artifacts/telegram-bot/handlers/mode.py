import logging
from aiogram import Router
from aiogram.types import CallbackQuery

from keyboards.mode_kb import (
    mode_select_kb,
    studio_mode_kb,
    realdev_mode_kb,
    back_to_mode_kb,
    back_to_realdev_kb,
)

logger = logging.getLogger(__name__)
router = Router(name="mode")


@router.callback_query(lambda c: c.data == "mode")
async def show_mode(callback: CallbackQuery) -> None:
    text = (
        "⚡ <b>اختر وضع التشغيل</b>\n\n"
        "🧩 <b>Studio Mode</b>\n"
        "   واجهة بسيطة لإدارة البوتات بدون كود\n\n"
        "⚡ <b>RealDev Mode</b>\n"
        "   واجهة احترافية للمطورين مع أدوات متقدمة"
    )
    await callback.message.edit_text(text, reply_markup=mode_select_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data == "mode_studio")
async def show_studio(callback: CallbackQuery) -> None:
    text = (
        "🧩 <b>Studio Mode</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "وضع بدون كود — أدِر بوتاتك بنقرة واحدة.\n\n"
        "اختر أحد الخيارات أدناه:"
    )
    await callback.message.edit_text(text, reply_markup=studio_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data == "mode_realdev")
async def show_realdev(callback: CallbackQuery) -> None:
    text = (
        "⚡ <b>RealDev Mode</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "وضع المطورين المتقدم — تحكم كامل في كل شيء.\n\n"
        "اختر الأداة المطلوبة:"
    )
    await callback.message.edit_text(text, reply_markup=realdev_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data == "studio_bots")
async def studio_bots(callback: CallbackQuery) -> None:
    text = (
        "🤖 <b>Active Bots</b>\n\n"
        "┌─────────────────────┐\n"
        "│ 🟢 MyShopBot      ON │\n"
        "│ 🔴 SupportBot    OFF │\n"
        "│ 🟡 NewsBot   PAUSED  │\n"
        "└─────────────────────┘\n\n"
        "<i>اضغط على البوت لإدارته (قريباً)</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data == "studio_settings")
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


@router.callback_query(lambda c: c.data == "studio_status")
async def studio_status(callback: CallbackQuery) -> None:
    text = (
        "🟢 <b>Bot Status</b>\n\n"
        "الحالة العامة: <b>يعمل بشكل طبيعي</b>\n\n"
        "📊 إحصائيات اليوم:\n"
        "  • الرسائل المُستقبَلة: <code>1,247</code>\n"
        "  • الردود التلقائية:    <code>986</code>\n"
        "  • المستخدمون الجدد:   <code>43</code>\n"
        "  • وقت التشغيل:        <code>99.8%</code>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_mode_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data == "dev_runtime")
async def dev_runtime(callback: CallbackQuery) -> None:
    text = (
        "🖥 <b>Runtime</b>\n\n"
        "<code>Python 3.12.3</code>\n"
        "<code>aiogram 3.13.1</code>\n"
        "<code>Memory:  128 MB / 512 MB</code>\n"
        "<code>CPU:     2.3%</code>\n"
        "<code>Uptime:  3d 14h 22m</code>\n"
        "<code>Threads: 8</code>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data == "dev_plugins")
async def dev_plugins(callback: CallbackQuery) -> None:
    text = (
        "🔌 <b>Plugins</b>\n\n"
        "✅ <code>inline-buttons   v1.2</code>\n"
        "✅ <code>auto-reply       v2.0</code>\n"
        "⚠️ <code>analytics        v0.9</code>  <i>(تحديث متاح)</i>\n"
        "❌ <code>payments         ---</code>   <i>(غير مثبّت)</i>\n\n"
        "<i>إدارة الإضافات قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data == "dev_logs")
async def dev_logs(callback: CallbackQuery) -> None:
    text = (
        "📋 <b>Logs</b>  <i>(آخر 5 سجلات)</i>\n\n"
        "<code>[14:32:01] INFO  Bot started</code>\n"
        "<code>[14:33:45] INFO  New user: 99123</code>\n"
        "<code>[14:35:12] DEBUG Handler: /start</code>\n"
        "<code>[14:40:08] WARN  Rate limit hit</code>\n"
        "<code>[14:41:55] INFO  Session closed</code>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data == "dev_events")
async def dev_events(callback: CallbackQuery) -> None:
    text = (
        "⚡ <b>Events</b>\n\n"
        "الأحداث المسجّلة:\n\n"
        "• <code>on_message</code>       → <i>3 handlers</i>\n"
        "• <code>on_callback_query</code> → <i>12 handlers</i>\n"
        "• <code>on_inline_query</code>  → <i>1 handler</i>\n"
        "• <code>on_startup</code>       → <i>2 hooks</i>\n"
        "• <code>on_shutdown</code>      → <i>1 hook</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data == "dev_variables")
async def dev_variables(callback: CallbackQuery) -> None:
    text = (
        "📦 <b>Variables</b>\n\n"
        "<code>BOT_TOKEN      = ****hidden****</code>\n"
        "<code>DATABASE_URL   = ****hidden****</code>\n"
        "<code>LOG_LEVEL      = INFO</code>\n"
        "<code>DEBUG_MODE     = False</code>\n"
        "<code>MAX_CONNECTIONS = 10</code>\n\n"
        "<i>التعديل على المتغيرات قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_realdev_kb(), parse_mode="HTML")
    await callback.answer()
