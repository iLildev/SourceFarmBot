import asyncio
import logging
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import BOT_TOKEN, LOG_LEVEL, WEBHOOK_HOST, WEBHOOK_PORT
from database.session import init_db
from handlers import (
    start, source_tree, mode, menu, commands,
    admin, report, donate, install, buy, fallback,
)
from middlewares.rate_limit import RateLimitMiddleware
from middlewares.activity import ActivityMiddleware

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand(command="start",  description="🏠 القائمة الرئيسية"),
    BotCommand(command="buy",    description="🌱 شراء البذور"),
    BotCommand(command="search", description="🔍 البحث في المصادر"),
    BotCommand(command="top",    description="🏆 أفضل المصادر"),
    BotCommand(command="report", description="🚨 الإبلاغ عن مشكلة"),
    BotCommand(command="donate", description="💚 دعم المنصة"),
]


def _build_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    # ── Middlewares ──────────────────────────────────────────────────────────
    # ActivityMiddleware runs first (outer) — tracks last_seen on every event
    dp.update.outer_middleware(ActivityMiddleware())
    # RateLimitMiddleware runs second — may block the event from reaching handlers
    dp.update.middleware(RateLimitMiddleware())

    # ── Routers (order matters — more specific before more general) ──────────
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(commands.router)
    dp.include_router(report.router)
    dp.include_router(donate.router)
    dp.include_router(buy.router)
    dp.include_router(install.router)
    dp.include_router(source_tree.router)
    dp.include_router(mode.router)
    dp.include_router(menu.router)
    dp.include_router(fallback.router)

    return dp


async def _run_polling(bot: Bot, dp: Dispatcher) -> None:
    logger.info("Mode: POLLING")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def _run_webhook(bot: Bot, dp: Dispatcher) -> None:
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    # Use a secret path segment so only Telegram can trigger it
    path = f"/webhook/{BOT_TOKEN}"
    url  = f"{WEBHOOK_HOST}{path}"

    await bot.set_webhook(
        url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )
    logger.info("Webhook set: %s", url)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=path)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=WEBHOOK_PORT)
    await site.start()
    logger.info("Webhook server listening on 0.0.0.0:%s", WEBHOOK_PORT)

    # Wait for shutdown signal
    shutdown = asyncio.Event()
    loop     = asyncio.get_running_loop()

    def _signal_handler():
        logger.info("Shutdown signal received.")
        shutdown.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    await shutdown.wait()
    await runner.cleanup()
    await bot.delete_webhook()
    logger.info("Webhook server stopped.")


async def main() -> None:
    logger.info("Starting SourceFarm bot ...")

    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    await bot.set_my_commands(BOT_COMMANDS)
    logger.info("Bot commands registered.")

    dp = _build_dispatcher()
    logger.info("All routers and middlewares registered.")

    if WEBHOOK_HOST:
        await _run_webhook(bot, dp)
    else:
        await _run_polling(bot, dp)


if __name__ == "__main__":
    # ── Graceful shutdown for polling mode ───────────────────────────────────
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    main_task = loop.create_task(main())

    def _terminate(*_):
        logger.info("SIGTERM/SIGINT — cancelling main task ...")
        main_task.cancel()

    signal.signal(signal.SIGTERM, _terminate)
    signal.signal(signal.SIGINT,  _terminate)

    try:
        loop.run_until_complete(main_task)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Bot stopped gracefully.")
    finally:
        loop.close()
