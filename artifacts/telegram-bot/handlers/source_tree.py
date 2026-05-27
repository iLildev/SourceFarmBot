import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from data.fake_sources import FAKE_SOURCES
from keyboards.source_tree_kb import source_detail_kb, source_nav_kb

logger = logging.getLogger(__name__)
router = Router(name="source_tree")


def _render_source(source: dict, index: int, total: int) -> str:
    stars = "⭐" * round(source["rating"])
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>{source['name']}</b>  <code>v{source['version']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷  <b>الفئة:</b>   {source['category']}\n"
        f"💎 <b>السعر:</b>   <code>{source['points']:,} نقطة</code>\n"
        f"📥 <b>التثبيت:</b> <code>{source['installs']:,}</code>\n"
        f"⭐ <b>التقييم:</b> {stars} <code>({source['rating']})</code>\n"
        f"👤 <b>المطوّر:</b> {source['author']}\n\n"
        f"📝 {source['description']}\n\n"
        f"<i>المصدر {index + 1} من {total}</i>"
    )


@router.message(F.text == "🌲 Source Tree")
async def show_source_tree_msg(message: Message) -> None:
    source = FAKE_SOURCES[0]
    text = _render_source(source, 0, len(FAKE_SOURCES))
    await message.answer(text, reply_markup=source_detail_kb(source["id"]), parse_mode="HTML")


@router.callback_query(F.data == "source_tree")
async def show_source_tree(callback: CallbackQuery) -> None:
    source = FAKE_SOURCES[0]
    text = _render_source(source, 0, len(FAKE_SOURCES))
    await callback.message.edit_text(
        text, reply_markup=source_detail_kb(source["id"]), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("src_page_"))
async def paginate_sources(callback: CallbackQuery) -> None:
    page = int(callback.data.split("_")[-1])
    page = max(0, min(page, len(FAKE_SOURCES) - 1))
    source = FAKE_SOURCES[page]
    text = _render_source(source, page, len(FAKE_SOURCES))
    await callback.message.edit_text(
        text, reply_markup=source_detail_kb(source["id"]), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("details_"))
async def show_details(callback: CallbackQuery) -> None:
    source_id = int(callback.data.split("_")[-1])
    source = next((s for s in FAKE_SOURCES if s["id"] == source_id), None)
    if not source:
        await callback.answer("المصدر غير موجود", show_alert=True)
        return

    current_idx = next(i for i, s in enumerate(FAKE_SOURCES) if s["id"] == source_id)
    text = (
        f"🔍 <b>تفاصيل: {source['name']}</b>\n\n"
        f"📌 <b>الإصدار:</b> {source['version']}\n"
        f"👤 <b>المطوّر:</b> {source['author']}\n"
        f"🏷  <b>الفئة:</b> {source['category']}\n"
        f"💎 <b>السعر:</b> {source['points']:,} نقطة\n"
        f"📥 <b>التثبيتات:</b> {source['installs']:,}\n"
        f"⭐ <b>التقييم:</b> {source['rating']}/5.0\n\n"
        f"📝 <b>الوصف:</b>\n{source['description']}\n\n"
        f"✅ هذا المصدر متاح للتثبيت الآن."
    )
    await callback.message.edit_text(
        text,
        reply_markup=source_nav_kb(current_idx, len(FAKE_SOURCES)),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("install_"))
async def install_source(callback: CallbackQuery) -> None:
    source_id = int(callback.data.split("_")[-1])
    source = next((s for s in FAKE_SOURCES if s["id"] == source_id), None)
    if not source:
        await callback.answer("المصدر غير موجود", show_alert=True)
        return
    await callback.answer(
        f"📦 يتم تثبيت «{source['name']}» ...\n💎 سيُخصم {source['points']:,} نقطة",
        show_alert=True,
    )
