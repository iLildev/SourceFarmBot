import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from keyboards.main_kb import main_menu_kb
from keyboards.source_tree_kb import source_browse_kb
from data.sources import SOURCES

logger = logging.getLogger(__name__)
router = Router(name="commands")


@router.message(Command("search"))
async def cmd_search(message: Message) -> None:
    args = message.text.strip().split(maxsplit=1)
    query = args[1].lower() if len(args) > 1 else ""

    if query:
        results = [
            s for s in SOURCES
            if query in s["name"].lower()
            or query in s["category"].lower()
            or query in s["description"].lower()
            or any(query in t.lower() for t in s.get("tags", []))
        ]
    else:
        results = []

    if not results and not query:
        await message.answer(
            "🔍 <b>البحث في Source Tree</b>\n\n"
            "أرسل الأمر مع كلمة البحث:\n"
            "<code>/search حماية</code>\n"
            "<code>/search متجر</code>\n"
            "<code>/search ذكاء اصطناعي</code>",
            parse_mode="HTML",
        )
        return

    if not results:
        await message.answer(
            f"🔍 لا توجد نتائج لـ «<b>{query}</b>»\n\n"
            "جرّب كلمة أخرى مثل: حماية، متجر، تواصل، دفع...",
            parse_mode="HTML",
        )
        return

    lines = [f"🔍 <b>نتائج البحث عن:</b> «{query}» — {len(results)} نتيجة\n"]
    for s in results[:8]:
        lines.append(
            f"━━━━━━━━━━━━━━\n"
            f"📦 <b>{s['name']}</b>  {s['category']}\n"
            f"🌱 {s['points']:,} بذرة  |  ⭐ {s['rating']}  |  📥 {s['installs']:,}\n"
        )
    if len(results) > 8:
        lines.append(f"\n<i>و {len(results) - 8} نتيجة أخرى — تصفّح Source Tree للمزيد.</i>")
    else:
        lines.append("\nاضغط 🌲 Source Tree للتصفح الكامل.")

    first = results[0]
    first_idx = next(i for i, s in enumerate(SOURCES) if s["id"] == first["id"])
    await message.answer(
        "\n".join(lines),
        reply_markup=source_browse_kb(first["id"], first_idx, len(SOURCES)),
        parse_mode="HTML",
    )


@router.message(Command("top"))
async def cmd_top(message: Message) -> None:
    sorted_sources = sorted(SOURCES, key=lambda s: s["installs"], reverse=True)[:10]

    lines = ["🏆 <b>أفضل 10 مصادر — Top Charts</b>\n"]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, s in enumerate(sorted_sources):
        lines.append(
            f"{medals[i]} <b>{s['name']}</b>  {s['category']}\n"
            f"    📥 {s['installs']:,} تثبيت  |  ⭐ {s['rating']}  |  🌱 {s['points']:,} بذرة\n"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")
