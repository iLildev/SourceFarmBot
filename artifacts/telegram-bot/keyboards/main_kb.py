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
            InlineKeyboardButton(text="⚡ البدء بدون كود",   callback_data="w_studio"),
            InlineKeyboardButton(text="👨‍💻 رفع سورس كود",   callback_data="w_realdev"),
        ],
        [
            InlineKeyboardButton(text="🛒 سوق السورسات",    callback_data="w_source_tree"),
            InlineKeyboardButton(text="💎 الخطة والأسعار",  callback_data="w_plan"),
        ],
        [
            InlineKeyboardButton(text="📚 دليل الاستخدام",  callback_data="w_help"),
            InlineKeyboardButton(text="⚙️ الإعدادات",       callback_data="w_settings"),
        ],
        [
            InlineKeyboardButton(text="ℹ️ معلومات المنصة",  callback_data="w_platform_info"),
            InlineKeyboardButton(text="الداعمين 🎖️",        callback_data="w_supporters"),
        ],
        [
            InlineKeyboardButton(text="🌐 تغيير اللغة / Language", callback_data="w_lang"),
        ],
    ])
