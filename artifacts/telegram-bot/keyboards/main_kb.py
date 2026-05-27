from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌲 Source Tree")],
            [KeyboardButton(text="☰ Menu"), KeyboardButton(text="⚡ Mode")],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def welcome_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ البدء بدون كود",   callback_data="mode_studio"),
            InlineKeyboardButton(text="👨‍💻 رفع سورس كود",   callback_data="mode_realdev"),
        ],
        [
            InlineKeyboardButton(text="🛒 سوق السورسات",    callback_data="source_tree"),
            InlineKeyboardButton(text="💎 الخطة والأسعار",  callback_data="menu_plan"),
        ],
        [
            InlineKeyboardButton(text="📚 دليل الاستخدام",  callback_data="menu_help"),
            InlineKeyboardButton(text="⚙️ الإعدادات",       callback_data="menu_settings"),
        ],
        [
            InlineKeyboardButton(text="ℹ️ معلومات المنصة",  callback_data="platform_info"),
            InlineKeyboardButton(text="الداعمين 🎖️",        callback_data="supporters"),
        ],
        [
            InlineKeyboardButton(text="🌐 تغيير اللغة / Language", callback_data="lang_select"),
        ],
    ])
