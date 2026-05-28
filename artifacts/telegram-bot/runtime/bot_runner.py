"""
Subprocess entry point — runs a single installed bot in an isolated process.
Called by BotManager with environment variables:
  SF_BOT_ID      — integer bot DB id
  SF_SOURCE_ID   — integer source id
  SF_BOT_TOKEN   — plaintext bot token (passed via env, never via argv)
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure the telegram-bot package root is on sys.path
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def _setup_logging(bot_id: int) -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format=f"%(asctime)s | %(levelname)-8s | bot={bot_id} | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )


def main() -> None:
    bot_id    = int(os.environ["SF_BOT_ID"])
    source_id = int(os.environ["SF_SOURCE_ID"])
    token     = os.environ["SF_BOT_TOKEN"]

    _setup_logging(bot_id)
    logger = logging.getLogger(__name__)
    logger.info("Bot subprocess started (source_id=%s)", source_id)

    from runtime.source_registry import get_plugin_class

    PluginClass = get_plugin_class(source_id)
    if PluginClass is None:
        logger.error("No plugin class for source_id=%s — exiting.", source_id)
        sys.exit(1)

    plugin = PluginClass(token=token, bot_id=bot_id, config={})
    try:
        plugin.run()
    except KeyboardInterrupt:
        logger.info("Bot subprocess stopped by signal.")
    except Exception as exc:
        logger.critical("Bot subprocess crashed: %s", exc, exc_info=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
