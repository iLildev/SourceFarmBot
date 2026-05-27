from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="⚡ البدء بدون كود"),
                KeyboardButton(text="👨‍💻 رفع سورس كود"),
            ],
            [
                KeyboardButton(text="🛒 سوق السورسات"),
                KeyboardButton(text="💎 الخطة والأسعار"),
            ],
            [
                KeyboardButton(text="📚 دليل الاستخدام"),
                KeyboardButton(text="⚙️ الإعدادات"),
            ],
            [
                KeyboardButton(text="ℹ️ معلومات المنصة"),
                KeyboardButton(text="الداعمين 🎖️"),
            ],
            [
                KeyboardButton(text="🌐 تغيير اللغة / Language"),
            ],
        ],
        resize_keyboard=True,
        persistent=True,
    )
