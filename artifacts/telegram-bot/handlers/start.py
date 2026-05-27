import logging
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.main_kb import main_menu_kb
from services.user_service import get_or_create_user, add_seeds, WELCOME_SEEDS, REFERRAL_BONUS_NEW_USER

logger = logging.getLogger(__name__)
router = Router(name="start")


WELCOME_TEXT = (
    "╔══════════════════════════╗\n"
    "║   🌿  <b>SourceFarm</b>          ║\n"
    "║   Your Bot Control Panel ║\n"
    "╚══════════════════════════╝\n\n"
    "مرحباً بك مجدداً، <b>{name}</b>! 👋\n\n"
    "<b>SourceFarm</b> هو مركز التحكم الكامل لبوتاتك —\n"
    "أنشئ، أدِر، وطوِّر بوتاتك بسهولة من داخل تيليجرام.\n\n"
    "اختر من القائمة أدناه للبدء 👇"
)

WELCOME_NEW_TEXT = (
    "╔══════════════════════════╗\n"
    "║   🌿  <b>SourceFarm</b>          ║\n"
    "║   Your Bot Control Panel ║\n"
    "╚══════════════════════════╝\n\n"
    "أهلاً وسهلاً، <b>{name}</b>! 🎉\n\n"
    "تم تسجيل حسابك بنجاح.\n"
    "لقد حصلت على <b>🌱 {seeds} بذرة</b> كهدية ترحيبية!\n\n"
    "اختر من القائمة أدناه للبدء 👇"
)

WELCOME_REFERRED_TEXT = (
    "╔══════════════════════════╗\n"
    "║   🌿  <b>SourceFarm</b>          ║\n"
    "║   Your Bot Control Panel ║\n"
    "╚══════════════════════════╝\n\n"
    "أهلاً وسهلاً، <b>{name}</b>! 🎉\n\n"
    "تم تسجيل حسابك بنجاح عبر رابط إحالة.\n"
    "🌱 هدية الترحيب:   <b>{welcome} بذرة</b>\n"
    "🎁 مكافأة الإحالة:  <b>+{bonus} بذرة</b>\n"
    "━━━━━━━━━━━━━━━━━\n"
    "💰 إجمالي رصيدك:   <b>{total} بذرة</b>\n\n"
    "اختر من القائمة أدناه للبدء 👇"
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

    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
