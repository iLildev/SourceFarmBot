import logging
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.main_kb import main_menu_kb
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)
router = Router(name="start")


WELCOME_TEXT = (
    "╔══════════════════════════╗\n"
    "║   🌿  <b>SourceFarm</b>          ║\n"
    "║   Your Bot Control Panel ║\n"
    "╚══════════════════════════╝\n\n"
    "مرحباً بك، <b>{name}</b>! 👋\n\n"
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
    "لقد حصلت على <b>🌱 50 بذرة</b> كهدية ترحيبية!\n\n"
    "اختر من القائمة أدناه للبدء 👇"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    tg_user = message.from_user
    user, created = await get_or_create_user(
        telegram_id=tg_user.id,
        first_name=tg_user.first_name or "مستخدم",
        last_name=tg_user.last_name,
        username=tg_user.username,
    )

    if created:
        from services.user_service import add_seeds
        await add_seeds(tg_user.id, 50)
        text = WELCOME_NEW_TEXT.format(name=tg_user.first_name or "مستخدم")
        logger.info("New user welcomed: tg_id=%s", tg_user.id)
    else:
        text = WELCOME_TEXT.format(name=tg_user.first_name or "مستخدم")
        logger.info("Returning user: tg_id=%s seeds=%s", tg_user.id, user.points)

    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
