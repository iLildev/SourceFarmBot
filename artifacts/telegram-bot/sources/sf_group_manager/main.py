"""
SF Group Manager — entry point.

Usage:
    python -m sources.sf_group_manager.main --bot-id <id> --token <token>
"""
import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sources.sf_group_manager.plugin import GroupManagerPlugin


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SF Group Manager Bot")
    parser.add_argument("--bot-id", type=int, required=True)
    parser.add_argument("--token",  type=str, required=True)
    return parser.parse_args()


def main() -> None:
    args   = _parse_args()
    plugin = GroupManagerPlugin(token=args.token, bot_id=args.bot_id, config={})
    plugin.run()


if __name__ == "__main__":
    main()
