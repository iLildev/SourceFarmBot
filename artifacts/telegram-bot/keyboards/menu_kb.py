from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Profile",         callback_data="menu_profile")],
            [InlineKeyboardButton(text="📋 Plan",            callback_data="menu_plan")],
            [InlineKeyboardButton(text="🌱 Seed Wallet",     callback_data="menu_wallet")],
            [InlineKeyboardButton(text="👥 Referral System", callback_data="menu_referral")],
            [InlineKeyboardButton(text="🎫 Codes",           callback_data="menu_codes")],
            [InlineKeyboardButton(text="❓ Help",            callback_data="menu_help")],
            [InlineKeyboardButton(text="⚙️ Settings",        callback_data="menu_settings")],
            [InlineKeyboardButton(text="🔙 رجوع",           callback_data="back_main")],
        ]
    )


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data="menu")],
        ]
    )


def profile_kb(has_bots: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_bots:
        rows.append([InlineKeyboardButton(text="🤖 عرض بوتاتي", callback_data="menu_mybots")])
    else:
        rows.append([InlineKeyboardButton(text="🌲 ثبّت أول بوت", callback_data="source_tree")])
    rows.append([InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def mybots_kb(bots: list) -> InlineKeyboardMarkup:
    rows = []
    for bot in bots:
        status = "🟢" if bot.is_running else "🔴"
        rows.append([
            InlineKeyboardButton(
                text=f"{status} {bot.name}",
                callback_data=f"bot_detail_{bot.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="menu_profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def bot_detail_kb(bot_id: int, is_running: bool) -> InlineKeyboardMarkup:
    toggle_text = "⏹ إيقاف" if is_running else "▶️ تشغيل"
    toggle_cb   = f"bot_stop_{bot_id}" if is_running else f"bot_start_{bot_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text,    callback_data=toggle_cb)],
            [InlineKeyboardButton(text="🗑 حذف البوت", callback_data=f"bot_delete_{bot_id}")],
            [InlineKeyboardButton(text="🔙 بوتاتي",    callback_data="menu_mybots")],
        ]
    )


def bot_delete_confirm_kb(bot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ نعم، احذفه", callback_data=f"bot_delete_confirm_{bot_id}"),
                InlineKeyboardButton(text="❌ لا",         callback_data=f"bot_detail_{bot_id}"),
            ]
        ]
    )
