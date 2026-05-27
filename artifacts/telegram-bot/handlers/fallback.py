import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.main_kb import main_menu_kb

logger = logging.getLogger(__name__)
router = Router(name="fallback")

KNOWN_BUTTONS = {"🌲 Source Tree", "⚡ Mode", "☰ Menu"}


@router.message(F.text & ~F.text.startswith("/"))
async def unknown_message(message: Message, state: FSMContext) -> None:
    if message.text in KNOWN_BUTTONS:
        return

    current_state = await state.get_state()
    if current_state is not None:
        return

    logger.debug("Unhandled message from tg_id=%s: %s", message.from_user.id, message.text[:50])
    await message.answer(
        "👋 استخدم القائمة أدناه للتنقّل،\n"
        "أو أرسل /start لإعادة التشغيل.",
        reply_markup=main_menu_kb(),
    )
