import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from keyboards.menu_kb import menu_kb, back_to_menu_kb

logger = logging.getLogger(__name__)
router = Router(name="menu")

MENU_TEXT = (
    "☰ <b>القائمة الرئيسية</b>\n"
    "━━━━━━━━━━━━━━━━━\n\n"
    "اختر القسم الذي تريد الوصول إليه:"
)


@router.message(F.text == "☰ Menu")
async def show_menu_msg(message: Message) -> None:
    await message.answer(MENU_TEXT, reply_markup=menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(MENU_TEXT, reply_markup=menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery) -> None:
    user = callback.from_user
    username = f"@{user.username}" if user.username else "—"
    text = (
        "👤 <b>الملف الشخصي</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"🪪 <b>الاسم:</b>     {user.full_name}\n"
        f"🔗 <b>المعرف:</b>   {username}\n"
        f"🆔 <b>ID:</b>       <code>{user.id}</code>\n"
        f"📋 <b>الخطة:</b>    <b>Free</b>\n"
        f"💎 <b>النقاط:</b>   <code>0</code>\n"
        f"📅 <b>الانضمام:</b> منذ قليل\n\n"
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
    text = (
        "💎 <b>محفظة النقاط</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "💰 <b>رصيدك الحالي:</b>  <code>0 نقطة</code>\n\n"
        "📊 <b>سجل المعاملات:</b>\n"
        "   لا توجد معاملات بعد.\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🛒 <i>شراء النقاط قريباً</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_referral")
async def show_referral(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    text = (
        "👥 <b>نظام الإحالة</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>رابط الإحالة الخاص بك:</b>\n"
        f"<code>https://t.me/sourcefarm_bot?start=ref{user_id}</code>\n\n"
        "📊 <b>إحصائياتك:</b>\n"
        "  • الأصدقاء المدعوون:  <code>0</code>\n"
        "  • النقاط المكتسبة:   <code>0</code>\n\n"
        "🎁 اكسب <b>50 نقطة</b> عن كل صديق يسجّل!"
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
