import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from keyboards.main_kb import main_menu_kb

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


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    name = message.from_user.first_name or "مستخدم"
    logger.info("User %s started the bot", message.from_user.id)
    await message.answer(
        WELCOME_TEXT.format(name=name),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
