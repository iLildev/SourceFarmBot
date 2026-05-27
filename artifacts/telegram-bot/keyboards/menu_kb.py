from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Profile", callback_data="menu_profile")],
            [InlineKeyboardButton(text="📋 Plan", callback_data="menu_plan")],
            [InlineKeyboardButton(text="💎 Points Wallet", callback_data="menu_wallet")],
            [InlineKeyboardButton(text="👥 Referral System", callback_data="menu_referral")],
            [InlineKeyboardButton(text="🎫 Codes", callback_data="menu_codes")],
            [InlineKeyboardButton(text="❓ Help", callback_data="menu_help")],
            [InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings")],
            [InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_main")],
        ]
    )


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 القائمة", callback_data="menu")],
        ]
    )
