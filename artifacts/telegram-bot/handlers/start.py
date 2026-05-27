import logging
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from keyboards.main_kb import main_menu_kb

logger = logging.getLogger(__name__)
router = Router(name="start")


WELCOME_TEXT = """
╔══════════════════════════╗
║   🌿  <b>SourceFarm</b>          ║
║   Your Bot Control Panel ║
╚══════════════════════════╝

مرحباً بك، <b>{name}</b>! 👋

<b>SourceFarm</b> هو مركز التحكم الكامل لبوتاتك —
أنشئ، أدِر، وطوِّر بوتاتك بسهولة من داخل تيليجرام.

اختر من القائمة أدناه للبدء 👇
"""


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    name = message.from_user.first_name or "مستخدم"
    logger.info("User %s started the bot", message.from_user.id)
    await message.answer(
        WELCOME_TEXT.format(name=name),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data == "back_main")
async def back_to_main(callback: CallbackQuery) -> None:
    name = callback.from_user.first_name or "مستخدم"
    await callback.message.edit_text(
        WELCOME_TEXT.format(name=name),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()
