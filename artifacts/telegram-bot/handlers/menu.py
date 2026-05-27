import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from keyboards.menu_kb import menu_kb, back_to_menu_kb
from services.user_service import get_user, get_referral_count, REFERRAL_BONUS_REFERRER, REFERRAL_BONUS_NEW_USER

logger = logging.getLogger(__name__)
router = Router(name="menu")

MENU_TEXT = (
    "☰ <b>القائمة الرئيسية</b>\n"
    "━━━━━━━━━━━━━━━━━\n\n"
    "اختر القسم الذي تريد الوصول إليه:"
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
    usd = seeds / 100
    return f"{usd:.2f}$"


@router.message(F.text == "☰ Menu")
async def show_menu_msg(message: Message) -> None:
    await message.answer(MENU_TEXT, reply_markup=menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(MENU_TEXT, reply_markup=menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery) -> None:
    tg = callback.from_user
    db_user = await get_user(tg.id)

    username = f"@{tg.username}" if tg.username else "—"
    seeds = db_user.points if db_user else 0
    joined = _format_date(db_user.created_at) if db_user else "—"
    usd_value = _seeds_to_usd(seeds)

    text = (
        "👤 <b>الملف الشخصي</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"🪪 <b>الاسم:</b>      {tg.full_name}\n"
        f"🔗 <b>المعرف:</b>    {username}\n"
        f"🆔 <b>ID:</b>        <code>{tg.id}</code>\n"
        f"📋 <b>الخطة:</b>     <b>Free</b>\n"
        f"🌱 <b>البذور:</b>    <code>{seeds:,} بذرة</code>  <i>≈ {usd_value}</i>\n"
        f"📅 <b>الانضمام:</b>  {joined}\n\n"
        "🔒 <i>الحساب موثَّق وآمن</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_plan")
async def show_plan(callback: CallbackQuery) -> None:
    text = (
        "📋 <b>خطتك الحالية</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "🆓 <b>Free Plan</b>\n\n"
        "✅ بوت واحد\n"
        "✅ 3 إضافات\n"
        "✅ دعم أساسي\n"
        "❌ Studio Mode متقدم\n"
        "❌ RealDev بلا حدود\n"
        "❌ تحليلات متقدمة\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "⬆️ <b>ترقية الخطة قريباً</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_wallet")
async def show_wallet(callback: CallbackQuery) -> None:
    db_user = await get_user(callback.from_user.id)
    seeds = db_user.points if db_user else 0
    usd_value = _seeds_to_usd(seeds)

    text = (
        "🌱 <b>محفظة البذور</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>رصيدك الحالي:</b>\n"
        f"   <code>{seeds:,} بذرة</code>  <i>≈ {usd_value}</i>\n\n"
        "💡 <b>سعر الصرف:</b>    <code>1$ = 100 بذرة</code>\n\n"
        "📊 <b>سجل المعاملات:</b>\n"
        "   لا توجد معاملات بعد.\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🛒 <i>شراء البذور قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_referral")
async def show_referral(callback: CallbackQuery) -> None:
    tg = callback.from_user
    db_user = await get_user(tg.id)
    seeds = db_user.points if db_user else 0
    ref_count = await get_referral_count(tg.id)
    earned_from_refs = ref_count * REFERRAL_BONUS_REFERRER

    bot_info = await callback.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{tg.id}"

    text = (
        "👥 <b>نظام الإحالة</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>رابط الإحالة الخاص بك:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "📊 <b>إحصائياتك:</b>\n"
        f"  • الأصدقاء المدعوون:  <b>{ref_count}</b>\n"
        f"  • البذور المكتسبة:   <code>{earned_from_refs:,} بذرة</code>\n"
        f"  • رصيدك الحالي:      <code>{seeds:,} بذرة</code>\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"🎁 <b>مكافآت الإحالة:</b>\n"
        f"  • أنت تحصل على:   <b>+{REFERRAL_BONUS_REFERRER} بذرة</b> لكل صديق\n"
        f"  • صديقك يحصل على: <b>+{REFERRAL_BONUS_NEW_USER} بذرة</b> إضافية\n\n"
        "شارك الرابط وابدأ الكسب! 🚀"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_codes")
async def show_codes(callback: CallbackQuery) -> None:
    text = (
        "🎫 <b>أكواد التفعيل</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "لديك كود خصم أو تفعيل؟\n"
        "أدخله هنا للحصول على مكافأتك.\n\n"
        "📥 <b>الأكواد المستخدمة:</b>  لا يوجد\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "<i>إدخال الكود قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_help")
async def show_help(callback: CallbackQuery) -> None:
    text = (
        "❓ <b>المساعدة والدعم</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📚 <b>دليل الاستخدام:</b>\n"
        "  • /start — القائمة الرئيسية\n\n"
        "💬 <b>التواصل مع الدعم:</b>\n"
        "  @sourcefarm_support\n\n"
        "📢 <b>قناة التحديثات:</b>\n"
        "  @sourcefarm_news\n\n"
        "🌐 <b>الموقع الرسمي:</b>\n"
        "  sourcefarm.io (قريباً)"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


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
