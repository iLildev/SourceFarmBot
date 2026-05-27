import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from keyboards.main_kb import main_menu_kb, welcome_inline_kb
from services.user_service import get_or_create_user, add_seeds, WELCOME_SEEDS, REFERRAL_BONUS_NEW_USER

logger = logging.getLogger(__name__)
router = Router(name="start")


WELCOME_TEXT = (
    "👋 مرحباً بعودتك، <b>{name}</b>!\n\n"
    "اختر من القائمة أدناه للبدء 👇"
)

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
    "• الوصول إلى آلاف المستخدمين النشطين يومياً.\n"
    "• تحقيق أرباح من سورساتك وخدماتك.\n"
    "━━━━━━━━━━━\n"
    "💰 كل هذا باشتراك واحد يبدأ من <b>4.99$</b> وخطة مجانية كريمة.. ماذا تنتظر؟ ابدأ الآن!\n"
)

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
    elif created:
        text = WELCOME_NEW_TEXT.format(name=name, seeds=user.points)
        logger.info("New user: tg_id=%s seeds=%s", tg_user.id, user.points)
    else:
        text = WELCOME_TEXT.format(name=name)
        logger.info("Returning user: tg_id=%s seeds=%s", tg_user.id, user.points)

    await message.answer(text, reply_markup=welcome_inline_kb(), parse_mode="HTML")
    await message.answer("👇 اختر من القائمة:", reply_markup=main_menu_kb())


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery) -> None:
    """Universal back-to-main handler — closes inline message, reminds user of the reply keyboard."""
    await callback.message.delete()
    await callback.message.answer(
        "🏠 اختر من القائمة أدناه 👇",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
