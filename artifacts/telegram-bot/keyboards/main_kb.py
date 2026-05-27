from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌲 Source Tree", callback_data="source_tree")],
            [InlineKeyboardButton(text="⚡ Mode", callback_data="mode")],
            [InlineKeyboardButton(text="☰ Menu", callback_data="menu")],
        ]
    )
