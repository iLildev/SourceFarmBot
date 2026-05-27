from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌲 Source Tree")],
            [KeyboardButton(text="☰ Menu"), KeyboardButton(text="⚡ Mode")],
        ],
        resize_keyboard=True,
        persistent=True,
    )
