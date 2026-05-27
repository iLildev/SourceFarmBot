"""
Shield Suite — entry point.

Invoked by BotManager as:
    python -m sources.shield_suite.main --bot-id <id> --token <token>
"""
import argparse
import sys
from pathlib import Path

# Ensure the telegram-bot root is on sys.path when run as subprocess
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sources.shield_suite.plugin import ShieldSuitePlugin


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shield Suite Bot")
    parser.add_argument("--bot-id", type=int, required=True)
    parser.add_argument("--token",  type=str, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    plugin = ShieldSuitePlugin(
        token=args.token,
        bot_id=args.bot_id,
        config={},          # loaded from DB / manifest defaults in future
    )
    plugin.run()


if __name__ == "__main__":
    main()
