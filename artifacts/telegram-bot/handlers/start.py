import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.main_kb import main_menu_kb, welcome_inline_kb
from keyboards.mode_kb import studio_mode_kb, realdev_mode_kb
from keyboards.source_tree_kb import source_browse_kb
from keyboards.menu_kb import back_to_menu_kb
from data.sources import SOURCES
from services.user_service import (
    get_or_create_user,
    WELCOME_SEEDS, REFERRAL_BONUS_NEW_USER, REFERRAL_BONUS_REFERRER,
)

logger = logging.getLogger(__name__)
router = Router(name="start")


_WELCOME_BODY = (
    "👋 مرحبًا بك في <b>SourceFarm</b>\n\n"
    "🤔 <b>ماذا ستجد هنا؟</b>\n"
    "━━━━━━━━━━━\n"
    "⚡ <b>لغير المبرمجين</b>\n"
    "• إنشاء بوتات بدون كتابة كود.\n"
    "• تثبيت سورسات جاهزة بضغطة واحدة.\n"
    "• إدارة وحماية متقدمة للبوتات.\n"
    "• الوصول إلى سورسات يطورها مطورون مستقلون.\n"
    "━━━━━━━━━━━\n"
    "🧠 <b>للمبرمجين</b>\n"
    "• رفع ونشر سورساتك بسهولة.\n"
    "• تشغيل واستضافة مستقرة للأكواد.\n"
    "• الوصول إلى آلاف المستخدمين\nالنشطين يومياً.\n"
    "• تحقيق أرباح من سورساتك وخدماتك.\n"
    "━━━━━━━━━━━\n"
    "💰 كل هذا باشتراك واحد يبدأ من <b>4.99$</b>\nوخطة مجانية كريمة.. ماذا تنتظر؟ ابدأ الآن!\n"
)

WELCOME_TEXT = _WELCOME_BODY

WELCOME_NEW_TEXT = (
    _WELCOME_BODY
    + "\n🎁 هدية ترحيبية: <b>🌱 {seeds} بذرة</b> أُضيفت لرصيدك!\n"
)

WELCOME_REFERRED_TEXT = (
    _WELCOME_BODY
    + "\n🌱 هدية الترحيب:   <b>{welcome} بذرة</b>\n"
    "🎁 مكافأة الإحالة:  <b>+{bonus} بذرة</b>\n"
    "━━━━━━━━━━━\n"
    "💰 إجمالي رصيدك:   <b>{total} بذرة</b>\n"
)


def _parse_referrer(text: str | None) -> int | None:
    if not text:
        return None
    parts = text.strip().split()
    if len(parts) < 2:
        return None
    arg = parts[1]
    if arg.startswith("ref") and arg[3:].isdigit():
        return int(arg[3:])
    return None


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    tg_user = message.from_user
    referred_by = _parse_referrer(message.text)

    if referred_by == tg_user.id:
        referred_by = None

    user, created = await get_or_create_user(
        telegram_id=tg_user.id,
        first_name=tg_user.first_name or "مستخدم",
        last_name=tg_user.last_name,
        username=tg_user.username,
        referred_by=referred_by,
    )

    name = tg_user.first_name or "مستخدم"

    if created and user.referred_by:
        text = WELCOME_REFERRED_TEXT.format(
            name=name,
            welcome=WELCOME_SEEDS,
            bonus=REFERRAL_BONUS_NEW_USER,
            total=user.points,
        )
        logger.info("New referred user: tg_id=%s ref_by=%s", tg_user.id, user.referred_by)

        # ── Notify referrer ──────────────────────────────────────────────────
        try:
            await message.bot.send_message(
                chat_id=user.referred_by,
                text=(
                    "🎉 <b>إحالة جديدة!</b>\n\n"
                    f"<b>{name}</b> انضم لـ SourceFarm عبر رابطك للتو.\n\n"
                    f"💰 <b>+{REFERRAL_BONUS_REFERRER} بذرة</b> أُضيفت لرصيدك تلقائياً! 🌱"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass  # المستخدم قد يكون حظر البوت — لا نوقف التسجيل بسببه

    elif created:
        text = WELCOME_NEW_TEXT.format(name=name, seeds=user.points)
        logger.info("New user: tg_id=%s seeds=%s", tg_user.id, user.points)
    else:
        text = WELCOME_TEXT.format(name=name)
        logger.info("Returning user: tg_id=%s seeds=%s", tg_user.id, user.points)

    await message.answer(text, reply_markup=welcome_inline_kb(), parse_mode="HTML")
    await message.answer("☰", reply_markup=main_menu_kb())


# ── Welcome inline button handlers (open new message, never touch welcome) ──

@router.callback_query(F.data == "w_studio")
async def w_studio(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "🧩 <b>Admin Mode</b>\n"
        "━━━━━━━━━━━\n\n"
        "وضع بدون كود — أدِر بوتاتك بنقرة واحدة.",
        reply_markup=studio_mode_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "w_realdev")
async def w_realdev(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "⚡ <b>Dev Mode</b>\n"
        "━━━━━━━━━━━\n\n"
        "وضع المطورين المتقدم — تحكم كامل في كل شيء.",
        reply_markup=realdev_mode_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "w_source_tree")
async def w_source_tree(callback: CallbackQuery) -> None:
    source = SOURCES[0]
    total = len(SOURCES)
    await callback.message.answer(
        _render_source_brief(source, 0, total),
        reply_markup=source_browse_kb(source["id"], 0, total),
        parse_mode="HTML",
    )
    await callback.answer()


def _render_source_brief(source: dict, index: int, total: int) -> str:
    tags_line = "  ".join(f"#{t}" for t in source.get("tags", [])[:4])
    installs = source["installs"]
    inst_text = f"<code>{installs:,}</code>" if installs > 0 else "<i>جديد — كن أول مثبِّت!</i>"
    rating = source.get("rating")
    stars = ("⭐" * round(rating) + f" <code>({rating})</code>") if rating else "<i>لا يوجد بعد</i>"
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>{source['name']}</b>  <code>v{source['version']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷  <b>الفئة:</b>   {source['category']}\n"
        f"🌱 <b>السعر:</b>   <code>{source['points']:,} بذرة</code>\n"
        f"📥 <b>التثبيت:</b> {inst_text}\n"
        f"⭐ <b>التقييم:</b> {stars}\n"
        f"👤 <b>المطوّر:</b> {source['author']}\n\n"
        f"📝 {source['description']}\n\n"
        f"<i>{tags_line}</i>"
    )


@router.callback_query(F.data == "w_plan")
async def w_plan(callback: CallbackQuery) -> None:
    await callback.message.answer(
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
        "⬆️ <b>ترقية الخطة قريباً</b>",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "w_help")
async def w_help(callback: CallbackQuery) -> None:
    await callback.message.answer(
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
        "  sourcefarm.io (قريباً)",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "w_settings")
async def w_settings(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "⚙️ <b>الإعدادات</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "🌐 <b>اللغة:</b>          العربية 🇸🇦\n"
        "🔔 <b>الإشعارات:</b>      مفعّلة ✅\n"
        "🕶 <b>وضع الخصوصية:</b>  مفعّل ✅\n"
        "🔐 <b>المصادقة الثنائية:</b> معطّلة ❌\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "<i>تعديل الإعدادات قريباً</i>",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "w_platform_info")
async def w_platform_info(callback: CallbackQuery) -> None:
    await callback.message.answer(
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
        "<i>بُنيت بـ ❤️ لمجتمع Telegram العربي</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✖️ إغلاق", callback_data="close_msg")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "w_supporters")
async def w_supporters(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "🎖️ <b>داعمو المنصة</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "شكراً لكل من دعم SourceFarm وساهم في نموّها.\n\n"
        "🥇 <b>الداعمون الذهبيون</b>\n"
        "   <i>لا يوجد بعد — كن أول داعم!</i>\n\n"
        "🥈 <b>الداعمون الفضيون</b>\n"
        "   <i>لا يوجد بعد</i>\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "💚 للدعم: /donate",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✖️ إغلاق", callback_data="close_msg")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "w_lang")
async def w_lang(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "🌐 <b>اللغة / Language</b>\n"
        "━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🇸🇦 العربية ✅",        callback_data="lang_ar"),
                InlineKeyboardButton(text="🇬🇧 English (قريباً)", callback_data="lang_en_soon"),
            ],
            [InlineKeyboardButton(text="✖️ إغلاق", callback_data="close_msg")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "close_msg")
async def close_msg(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.message.answer(
        "🏠 القائمة الرئيسية",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
