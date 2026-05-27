import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from keyboards.main_kb import main_menu_kb
from keyboards.source_tree_kb import source_browse_kb
from data.fake_sources import FAKE_SOURCES

logger = logging.getLogger(__name__)
router = Router(name="commands")


@router.message(Command("search"))
async def cmd_search(message: Message) -> None:
    args = message.text.strip().split(maxsplit=1)
    query = args[1].lower() if len(args) > 1 else ""

    if query:
        results = [
            s for s in FAKE_SOURCES
            if query in s["name"].lower()
            or query in s["category"].lower()
            or query in s["description"].lower()
        ]
    else:
        results = []

    if not results and not query:
        await message.answer(
            "🔍 <b>البحث في Source Tree</b>\n\n"
            "أرسل الأمر مع كلمة البحث:\n"
            "<code>/search chatbot</code>\n"
            "<code>/search shop</code>",
            parse_mode="HTML",
        )
        return

    if not results:
        await message.answer(
            f"🔍 لا توجد نتائج لـ «<b>{query}</b>»\n\n"
            "جرّب كلمة أخرى.",
            parse_mode="HTML",
        )
        return

    lines = [f"🔍 <b>نتائج البحث عن:</b> «{query}»\n"]
    for s in results:
        lines.append(
            f"━━━━━━━━━━━━━━\n"
            f"📦 <b>{s['name']}</b>  {s['category']}\n"
            f"🌱 {s['points']:,} بذرة  |  ⭐ {s['rating']}  |  📥 {s['installs']:,}\n"
        )
    lines.append("\nاضغط 🌲 Source Tree للتصفح الكامل.")

    first = results[0]
    first_idx = next(i for i, s in enumerate(FAKE_SOURCES) if s["id"] == first["id"])
    await message.answer(
        "\n".join(lines),
        reply_markup=source_browse_kb(first["id"], first_idx, len(FAKE_SOURCES)),
        parse_mode="HTML",
    )


@router.message(Command("top"))
async def cmd_top(message: Message) -> None:
    sorted_sources = sorted(FAKE_SOURCES, key=lambda s: s["installs"], reverse=True)

    lines = ["🏆 <b>أفضل المصادر — Top Charts</b>\n"]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣"]
    for i, s in enumerate(sorted_sources):
        lines.append(
            f"{medals[i]} <b>{s['name']}</b>  {s['category']}\n"
            f"    📥 {s['installs']:,} تثبيت  |  ⭐ {s['rating']}  |  🌱 {s['points']:,} بذرة\n"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")



@router.message(Command("donate"))
async def cmd_donate(message: Message) -> None:
    await message.answer(
        "💚 <b>ادعم SourceFarm</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "مساهمتك تساعدنا على:\n"
        "  🌱 تطوير مصادر جديدة\n"
        "  ⚡ تحسين الأداء\n"
        "  🛡 تعزيز الأمان\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "💳 <b>طرق الدعم:</b>\n"
        "  • USDT (TRC20):\n"
        "    <code>TXxxxxxxxxxxxxxxxxxxxx</code>\n\n"
        "  • BTC:\n"
        "    <code>1Xxxxxxxxxxxxxxxxxxxxx</code>\n\n"
        "كل مبلغ مهما صغر يُحدث فرقاً ❤️\n"
        "شكراً لدعمك!",
        parse_mode="HTML",
    )
