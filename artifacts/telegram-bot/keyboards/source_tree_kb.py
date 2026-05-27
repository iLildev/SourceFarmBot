from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def source_list_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ السابق", callback_data="src_prev"),
                InlineKeyboardButton(text="التالي ▶️", callback_data="src_next"),
            ],
            [InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_main")],
        ]
    )


def source_detail_kb(source_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📦 تثبيت", callback_data=f"install_{source_id}"),
                InlineKeyboardButton(text="🔍 التفاصيل", callback_data=f"details_{source_id}"),
            ],
            [InlineKeyboardButton(text="🔙 القائمة", callback_data="source_tree")],
        ]
    )


def source_nav_kb(current: int, total: int) -> InlineKeyboardMarkup:
    buttons = []
    nav_row = []
    if current > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ السابق", callback_data=f"src_page_{current - 1}"))
    if current < total - 1:
        nav_row.append(InlineKeyboardButton(text="التالي ▶️", callback_data=f"src_page_{current + 1}"))
    if nav_row:
        buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
