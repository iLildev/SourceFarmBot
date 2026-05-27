from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def mode_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧩 Studio Mode", callback_data="mode_studio")],
            [InlineKeyboardButton(text="⚡ RealDev Mode", callback_data="mode_realdev")],
            [InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_main")],
        ]
    )


def studio_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Active Bots", callback_data="studio_bots")],
            [InlineKeyboardButton(text="⚙️ Quick Settings", callback_data="studio_settings")],
            [InlineKeyboardButton(text="🟢 Bot Status", callback_data="studio_status")],
            [InlineKeyboardButton(text="🔙 اختيار الوضع", callback_data="mode")],
        ]
    )


def realdev_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🖥 Runtime", callback_data="dev_runtime")],
            [InlineKeyboardButton(text="🔌 Plugins", callback_data="dev_plugins")],
            [InlineKeyboardButton(text="📋 Logs", callback_data="dev_logs")],
            [InlineKeyboardButton(text="⚡ Events", callback_data="dev_events")],
            [InlineKeyboardButton(text="📦 Variables", callback_data="dev_variables")],
            [InlineKeyboardButton(text="🔙 اختيار الوضع", callback_data="mode")],
        ]
    )


def back_to_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 الرجوع", callback_data="mode_studio")],
        ]
    )


def back_to_realdev_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 الرجوع", callback_data="mode_realdev")],
        ]
    )
