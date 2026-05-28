from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def source_browse_kb(
    source_id: int,
    current: int,
    total: int,
    available: bool = True,
) -> InlineKeyboardMarkup:
    """Unified keyboard: install + details + prev/counter/next + back."""
    nav_row = []
    if current > 0:
        nav_row.append(
            InlineKeyboardButton(text="◀️", callback_data=f"src_page_{current - 1}")
        )
    nav_row.append(
        InlineKeyboardButton(text=f"🌿 {current + 1}/{total}", callback_data="noop")
    )
    if current < total - 1:
        nav_row.append(
            InlineKeyboardButton(text="▶️", callback_data=f"src_page_{current + 1}")
        )

    install_btn = (
        InlineKeyboardButton(text="📦 تثبيت", callback_data=f"install_{source_id}")
        if available
        else InlineKeyboardButton(text="🔒 قريباً", callback_data="coming_soon")
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                install_btn,
                InlineKeyboardButton(text="🔍 التفاصيل", callback_data=f"details_{source_id}"),
            ],
            nav_row,
            [InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_main")],
        ]
    )


def source_detail_full_kb(
    source_id: int,
    current: int,
    total: int,
    available: bool = True,
) -> InlineKeyboardMarkup:
    """Detail view keyboard: install + prev/counter/next + back to browse."""
    nav_row = []
    if current > 0:
        nav_row.append(
            InlineKeyboardButton(text="◀️", callback_data=f"src_page_{current - 1}")
        )
    nav_row.append(
        InlineKeyboardButton(text=f"🌿 {current + 1}/{total}", callback_data="noop")
    )
    if current < total - 1:
        nav_row.append(
            InlineKeyboardButton(text="▶️", callback_data=f"src_page_{current + 1}")
        )

    install_btn = (
        InlineKeyboardButton(text="📦 تثبيت", callback_data=f"install_{source_id}")
        if available
        else InlineKeyboardButton(text="🔒 قريباً", callback_data="coming_soon")
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [install_btn],
            nav_row,
            [InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_main")],
        ]
    )
