import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.menu_kb import (
    menu_kb, back_to_menu_kb, profile_kb,
    mybots_kb, bot_detail_kb, bot_delete_confirm_kb,
)
from aiogram.types import InlineKeyboardButton
from services.user_service import get_user, get_referral_count, REFERRAL_BONUS_REFERRER, REFERRAL_BONUS_NEW_USER
from services.bot_service import get_user_bots, get_bot_by_id, toggle_bot_running, delete_bot

logger = logging.getLogger(__name__)
router = Router(name="menu")

MENU_TEXT = (
    "☰ <b>القائمة الرئيسية</b>\n"
    "━━━━━━━━━━━━━━━━━"
)

ARABIC_MONTHS = [
    "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]


def _format_date(dt) -> str:
    if not dt:
        return "—"
    return f"{dt.day} {ARABIC_MONTHS[dt.month]} {dt.year}"


def _seeds_to_usd(seeds: int) -> str:
    return f"{seeds / 100:.2f}$"


# ──────────────────────────── Menu root ──────────────────────────────

@router.message(F.text == "☰ Menu")
async def show_menu_msg(message: Message) -> None:
    await message.answer(MENU_TEXT, reply_markup=menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "platform_info")
async def show_platform_info(callback: CallbackQuery) -> None:
    text = (
        "ℹ️ <b>معلومات المنصة</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "🌿 <b>SourceFarm</b>\n"
        "منصة تحكم كاملة للبوتات داخل Telegram.\n\n"
        "📌 <b>الإصدار:</b>       <code>0.1.0 Beta</code>\n"
        "🌐 <b>الموقع:</b>        sourcefarm.io (قريباً)\n"
        "📢 <b>قناة الأخبار:</b>  @sourcefarm_news\n"
        "💬 <b>الدعم:</b>         @sourcefarm_support\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "💰 <b>عملة المنصة:</b>   🌱 بذرة\n"
        "💱 <b>سعر الصرف:</b>    <code>1$ = 100 بذرة</code>\n\n"
        "<i>بُنيت بـ ❤️ لمجتمع Telegram العربي</i>"
    )
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_main")],
    ])
    await callback.message.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "supporters")
async def show_supporters(callback: CallbackQuery) -> None:
    text = (
        "🎖️ <b>داعمو المنصة</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "شكراً لكل من دعم SourceFarm وساهم في نموّها.\n\n"
        "🥇 <b>الداعمون الذهبيون</b>\n"
        "   <i>لا يوجد بعد — كن أول داعم!</i>\n\n"
        "🥈 <b>الداعمون الفضيون</b>\n"
        "   <i>لا يوجد بعد</i>\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "💚 للدعم: /donate"
    )
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_main")],
    ])
    await callback.message.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "lang_select")
async def show_lang_select(callback: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇸🇦 العربية ✅",          callback_data="lang_ar"),
            InlineKeyboardButton(text="🇬🇧 English (قريباً)",    callback_data="lang_en_soon"),
        ],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_main")],
    ])
    await callback.message.edit_text(
        "🌐 <b>اللغة / Language</b>\n"
        "━━━━━━━━━━━━━━━━━",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "lang_ar")
async def lang_ar(callback: CallbackQuery) -> None:
    await callback.answer("✅ اللغة العربية مفعّلة بالفعل", show_alert=False)


@router.callback_query(F.data == "lang_en_soon")
async def lang_en_soon(callback: CallbackQuery) -> None:
    await callback.answer("🚧 اللغة الإنجليزية قيد التطوير — قريباً!", show_alert=True)


@router.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(MENU_TEXT, reply_markup=menu_kb(), parse_mode="HTML")
    await callback.answer()


# ──────────────────────────── Profile ────────────────────────────────

@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery) -> None:
    tg      = callback.from_user
    db_user = await get_user(tg.id)
    bots    = await get_user_bots(tg.id)

    username  = f"@{tg.username}" if tg.username else "—"
    seeds     = db_user.points if db_user else 0
    joined    = _format_date(db_user.created_at) if db_user else "—"
    usd_value = _seeds_to_usd(seeds)
    running   = sum(1 for b in bots if b.is_running)

    bots_line = (
        f"<b>{len(bots)}</b>  (🟢 {running} شغّال)"
        if bots else "لا يوجد بوتات بعد"
    )

    text = (
        "👤 <b>الملف الشخصي</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"🪪 <b>الاسم:</b>      {tg.full_name}\n"
        f"🔗 <b>المعرف:</b>    {username}\n"
        f"🆔 <b>ID:</b>        <code>{tg.id}</code>\n"
        f"📋 <b>الخطة:</b>     Free\n"
        f"🌱 <b>البذور:</b>    <code>{seeds:,} بذرة</code>  <i>≈ {usd_value}</i>\n"
        f"🤖 <b>بوتاتي:</b>   {bots_line}\n"
        f"📅 <b>الانضمام:</b>  {joined}\n\n"
        "🔒 <i>الحساب موثَّق وآمن</i>"
    )
    await callback.message.edit_text(
        text, reply_markup=profile_kb(has_bots=bool(bots)), parse_mode="HTML"
    )
    await callback.answer()


# ──────────────────────────── My Bots ────────────────────────────────

@router.callback_query(F.data == "menu_mybots")
async def show_mybots(callback: CallbackQuery) -> None:
    bots = await get_user_bots(callback.from_user.id)

    if not bots:
        empty_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌲 تثبيت أول بوت",    callback_data="source_tree")],
            [InlineKeyboardButton(text="🔙 رجوع للبروفايل", callback_data="menu_profile")],
        ])
        await callback.message.edit_text(
            "🤖 <b>بوتاتي</b>\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "لا يوجد لديك بوتات مثبّتة بعد.\n\n"
            "📦 تصفّح Source Tree واختر سورساً لتثبيته.",
            reply_markup=empty_kb,
            parse_mode="HTML",
        )
        await callback.answer()
        return

    running = sum(1 for b in bots if b.is_running)
    stopped = len(bots) - running

    text = (
        f"🤖 <b>بوتاتي</b>  <code>({len(bots)})</code>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"🟢 شغّال: <b>{running}</b>   🔴 متوقف: <b>{stopped}</b>\n\n"
        "اضغط على أي بوت لإدارته:"
    )
    await callback.message.edit_text(text, reply_markup=mybots_kb(bots), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("bot_detail_"))
async def show_bot_detail(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split("_")[-1])
    bot = await get_bot_by_id(bot_id, callback.from_user.id)

    if not bot:
        await callback.answer("البوت غير موجود", show_alert=True)
        return

    status_icon = "🟢 شغّال" if bot.is_running else "🔴 متوقف"
    mode_label  = "🧩 Admin Mode" if bot.mode == "studio" else "⚡ Dev Mode"
    created     = _format_date(bot.created_at)
    hint        = bot.token_hint or "—"

    text = (
        f"🤖 <b>{bot.name}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"📡 <b>الحالة:</b>    {status_icon}\n"
        f"⚙️ <b>الوضع:</b>    {mode_label}\n"
        f"🔑 <b>التوكن:</b>   <code>{hint}…</code>\n"
        f"📅 <b>التثبيت:</b>  {created}\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"<i>💡 إطلاق البوت الفعلي وإدارة الإضافات قيد التطوير — قريباً</i>"
    )
    await callback.message.edit_text(
        text, reply_markup=bot_detail_kb(bot_id, bot.is_running), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot_start_"))
async def bot_start(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split("_")[-1])
    bot = await toggle_bot_running(bot_id, callback.from_user.id, running=True)
    if not bot:
        await callback.answer("البوت غير موجود", show_alert=True)
        return
    await callback.answer("▶️ تم تشغيل البوت", show_alert=False)
    callback.data = f"bot_detail_{bot_id}"
    await show_bot_detail(callback)


@router.callback_query(F.data.startswith("bot_stop_"))
async def bot_stop(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split("_")[-1])
    bot = await toggle_bot_running(bot_id, callback.from_user.id, running=False)
    if not bot:
        await callback.answer("البوت غير موجود", show_alert=True)
        return
    await callback.answer("⏹ تم إيقاف البوت", show_alert=False)
    callback.data = f"bot_detail_{bot_id}"
    await show_bot_detail(callback)


@router.callback_query(F.data.startswith("bot_delete_") & ~F.data.startswith("bot_delete_confirm_"))
async def bot_delete_ask(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split("_")[-1])
    bot = await get_bot_by_id(bot_id, callback.from_user.id)
    if not bot:
        await callback.answer("البوت غير موجود", show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 <b>حذف البوت</b>\n\n"
        f"هل أنت متأكد من حذف <b>{bot.name}</b>؟\n"
        "لا يمكن التراجع عن هذا الإجراء.",
        reply_markup=bot_delete_confirm_kb(bot_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot_delete_confirm_"))
async def bot_delete_confirm(callback: CallbackQuery) -> None:
    bot_id  = int(callback.data.split("_")[-1])
    deleted = await delete_bot(bot_id, callback.from_user.id)
    if not deleted:
        await callback.answer("البوت غير موجود", show_alert=True)
        return
    await callback.answer("🗑 تم حذف البوت", show_alert=True)
    callback.data = "menu_mybots"
    await show_mybots(callback)


# ──────────────────────────── Plan ───────────────────────────────────

@router.callback_query(F.data == "menu_plan")
async def show_plan(callback: CallbackQuery) -> None:
    text = (
        "📋 <b>خطتك الحالية</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "🆓 <b>Free Plan</b>\n\n"
        "✅ بوت واحد\n"
        "✅ 3 إضافات\n"
        "✅ دعم أساسي\n"
        "❌ Admin Mode متقدم\n"
        "❌ Dev بلا حدود\n"
        "❌ تحليلات متقدمة\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "⬆️ <b>ترقية الخطة قريباً</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


# ──────────────────────────── Wallet ─────────────────────────────────

@router.callback_query(F.data == "menu_wallet")
async def show_wallet(callback: CallbackQuery) -> None:
    db_user   = await get_user(callback.from_user.id)
    seeds     = db_user.points if db_user else 0
    usd_value = _seeds_to_usd(seeds)

    text = (
        "🌱 <b>محفظة البذور</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>رصيدك الحالي:</b>\n"
        f"   <code>{seeds:,} بذرة</code>  <i>≈ {usd_value}</i>\n\n"
        "💡 <b>سعر الصرف:</b>    <code>1$ = 100 بذرة</code>\n\n"
        "📊 <b>سجل المعاملات:</b>\n"
        "   لا توجد معاملات بعد.\n\n"
        "━━━━━━━━━━━━━━━━━"
    )
    buy_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌱 شراء البذور", callback_data="buy_store")],
        [InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data="menu")],
    ])
    await callback.message.edit_text(text, reply_markup=buy_kb, parse_mode="HTML")
    await callback.answer()


# ──────────────────────────── Referral ───────────────────────────────

@router.callback_query(F.data == "menu_referral")
async def show_referral(callback: CallbackQuery) -> None:
    tg        = callback.from_user
    db_user   = await get_user(tg.id)
    seeds     = db_user.points if db_user else 0
    ref_count = await get_referral_count(tg.id)
    earned    = ref_count * REFERRAL_BONUS_REFERRER

    bot_info = await callback.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{tg.id}"

    text = (
        "👥 <b>نظام الإحالة</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>رابط الإحالة الخاص بك:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "📊 <b>إحصائياتك:</b>\n"
        f"  • الأصدقاء المدعوون:  <b>{ref_count}</b>\n"
        f"  • البذور المكتسبة:   <code>{earned:,} بذرة</code>\n"
        f"  • رصيدك الحالي:      <code>{seeds:,} بذرة</code>\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"🎁 <b>مكافآت الإحالة:</b>\n"
        f"  • أنت تحصل على:   <b>+{REFERRAL_BONUS_REFERRER} بذرة</b> لكل صديق\n"
        f"  • صديقك يحصل على: <b>+{REFERRAL_BONUS_NEW_USER} بذرة</b> إضافية\n\n"
        "شارك الرابط وابدأ الكسب! 🚀"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


# ──────────────────────────── Codes → delegated to codes.py ─────────


# ──────────────────────────── Help ───────────────────────────────────

@router.callback_query(F.data == "menu_help")
async def show_help(callback: CallbackQuery) -> None:
    text = (
        "❓ <b>المساعدة والدعم</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📚 <b>دليل الاستخدام:</b>\n"
        "  • /start — القائمة الرئيسية\n"
        "  • /search — البحث في المصادر\n"
        "  • /top — أفضل المصادر\n"
        "  • 🌱 شراء البذور — من ☰ Menu ← Seed Wallet\n\n"
        "💬 <b>التواصل مع الدعم:</b>\n"
        "  @sourcefarm_support\n\n"
        "📢 <b>قناة التحديثات:</b>\n"
        "  @sourcefarm_news\n\n"
        "🌐 <b>الموقع الرسمي:</b>\n"
        "  sourcefarm.io (قريباً)"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


# ──────────────────────────── Settings ───────────────────────────────

@router.callback_query(F.data == "menu_settings")
async def show_settings(callback: CallbackQuery) -> None:
    text = (
        "⚙️ <b>الإعدادات</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "🌐 <b>اللغة:</b>          العربية 🇸🇦\n"
        "🔔 <b>الإشعارات:</b>      مفعّلة ✅\n"
        "🕶 <b>وضع الخصوصية:</b>  مفعّل ✅\n"
        "🔐 <b>المصادقة الثنائية:</b> معطّلة ❌\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "<i>تعديل الإعدادات قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()
