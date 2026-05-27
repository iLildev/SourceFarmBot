import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from data.sources import SOURCES
from keyboards.source_tree_kb import source_browse_kb, source_detail_full_kb

logger = logging.getLogger(__name__)
router = Router(name="source_tree")


def _render_source(source: dict, index: int, total: int) -> str:
    stars = "⭐" * round(source["rating"])
    tags_line = "  ".join(f"#{t}" for t in source.get("tags", [])[:4])
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>{source['name']}</b>  <code>v{source['version']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷  <b>الفئة:</b>   {source['category']}\n"
        f"🌱 <b>السعر:</b>   <code>{source['points']:,} بذرة</code>\n"
        f"📥 <b>التثبيت:</b> <code>{source['installs']:,}</code>\n"
        f"⭐ <b>التقييم:</b> {stars} <code>({source['rating']})</code>\n"
        f"👤 <b>المطوّر:</b> {source['author']}\n\n"
        f"📝 {source['description']}\n\n"
        f"<i>{tags_line}</i>"
    )


def _render_detail(source: dict) -> str:
    features = source.get("features", [])
    features_text = "\n".join(f"  {f}" for f in features)
    tags_line = "  ".join(f"#{t}" for t in source.get("tags", []))
    return (
        f"🔍 <b>{source['name']}</b>  <code>v{source['version']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 <b>الإصدار:</b>    {source['version']}\n"
        f"👤 <b>المطوّر:</b>    {source['author']}\n"
        f"🏷  <b>الفئة:</b>     {source['category']}\n"
        f"🌱 <b>السعر:</b>     <code>{source['points']:,} بذرة</code>\n"
        f"📥 <b>التثبيتات:</b> <code>{source['installs']:,}</code>\n"
        f"⭐ <b>التقييم:</b>   <code>{source['rating']}/5.0</code>\n\n"
        f"📝 <b>الوصف:</b>\n{source['description']}\n\n"
        f"✨ <b>الميزات الرئيسية:</b>\n{features_text}\n\n"
        f"<i>{tags_line}</i>\n\n"
        f"✅ متاح للتثبيت الآن."
    )


def _source_index(source_id: int) -> int:
    return next((i for i, s in enumerate(SOURCES) if s["id"] == source_id), 0)


@router.message(F.text == "🌲 Source Tree")
async def show_source_tree_msg(message: Message) -> None:
    source = SOURCES[0]
    total = len(SOURCES)
    await message.answer(
        _render_source(source, 0, total),
        reply_markup=source_browse_kb(source["id"], 0, total),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "source_tree")
async def show_source_tree(callback: CallbackQuery) -> None:
    source = SOURCES[0]
    total = len(SOURCES)
    await callback.message.edit_text(
        _render_source(source, 0, total),
        reply_markup=source_browse_kb(source["id"], 0, total),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("src_page_"))
async def paginate_sources(callback: CallbackQuery) -> None:
    page = int(callback.data.split("_")[-1])
    page = max(0, min(page, len(SOURCES) - 1))
    source = SOURCES[page]
    total = len(SOURCES)
    await callback.message.edit_text(
        _render_source(source, page, total),
        reply_markup=source_browse_kb(source["id"], page, total),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("details_"))
async def show_details(callback: CallbackQuery) -> None:
    source_id = int(callback.data.split("_")[-1])
    source = next((s for s in SOURCES if s["id"] == source_id), None)
    if not source:
        await callback.answer("المصدر غير موجود", show_alert=True)
        return
    idx = _source_index(source_id)
    total = len(SOURCES)
    await callback.message.edit_text(
        _render_detail(source),
        reply_markup=source_detail_full_kb(source_id, idx, total),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("install_"))
async def install_source(callback: CallbackQuery) -> None:
    source_id = int(callback.data.split("_")[-1])
    source = next((s for s in SOURCES if s["id"] == source_id), None)
    if not source:
        await callback.answer("المصدر غير موجود", show_alert=True)
        return
    await callback.answer(
        f"📦 يتم تثبيت «{source['name']}»\n🌱 سيُخصم {source['points']:,} بذرة",
        show_alert=True,
    )


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()
