import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import BOT_TOKEN, LOG_LEVEL
from database.session import init_db
from handlers import start, source_tree, mode, menu, commands, admin, report, donate, fallback

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand(command="start",  description="🏠 القائمة الرئيسية"),
    BotCommand(command="search", description="🔍 البحث في المصادر"),
    BotCommand(command="top",    description="🏆 أفضل المصادر"),
    BotCommand(command="report", description="🚨 الإبلاغ عن مشكلة"),
    BotCommand(command="donate", description="💚 دعم المنصة"),
]


async def main() -> None:
    logger.info("Starting SourceFarm bot ...")

    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    await bot.set_my_commands(BOT_COMMANDS)
    logger.info("Bot commands registered.")

    dp = Dispatcher()

    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(commands.router)
    dp.include_router(report.router)
    dp.include_router(donate.router)
    dp.include_router(source_tree.router)
    dp.include_router(mode.router)
    dp.include_router(menu.router)
    dp.include_router(fallback.router)

    logger.info("All routers registered. Launching polling ...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
