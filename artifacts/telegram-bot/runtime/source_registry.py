"""
Auto-discovers plugin classes from the sources/ directory.
Each source must have:
  - manifest.json  with an "id" integer field
  - plugin.py      with exactly one BaseSourcePlugin subclass

No manual registration needed — just drop a new source folder and restart.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.plugin_base import BaseSourcePlugin

logger = logging.getLogger(__name__)

_BASE_DIR    = Path(__file__).resolve().parent.parent
_SOURCES_DIR = _BASE_DIR / "sources"

_registry: dict[int, type] | None = None


def _build_registry() -> dict[int, type]:
    registry: dict[int, type] = {}

    for source_dir in sorted(_SOURCES_DIR.iterdir()):
        if not source_dir.is_dir() or source_dir.name.startswith("_"):
            continue

        manifest_file = source_dir / "manifest.json"
        plugin_file   = source_dir / "plugin.py"

        if not manifest_file.exists() or not plugin_file.exists():
            continue

        try:
            with open(manifest_file) as f:
                manifest = json.load(f)
            source_id = int(manifest["id"])
        except Exception as exc:
            logger.warning("[registry] Bad manifest in %s: %s — skipping", source_dir.name, exc)
            continue

        try:
            from runtime.plugin_base import BaseSourcePlugin

            module_name = f"sources.{source_dir.name}.plugin"
            module      = importlib.import_module(module_name)

            plugin_cls = next(
                (
                    getattr(module, attr)
                    for attr in dir(module)
                    if isinstance(getattr(module, attr), type)
                    and issubclass(getattr(module, attr), BaseSourcePlugin)
                    and getattr(module, attr) is not BaseSourcePlugin
                ),
                None,
            )

            if plugin_cls:
                registry[source_id] = plugin_cls
                logger.info(
                    "[registry] source_id=%s → %s (%s)",
                    source_id, plugin_cls.__name__, manifest.get("name", source_dir.name),
                )
            else:
                logger.warning("[registry] No BaseSourcePlugin subclass in %s", module_name)

        except Exception as exc:
            logger.error("[registry] Failed to load %s: %s", source_dir.name, exc)

    logger.info("[registry] %d source(s) loaded.", len(registry))
    return registry


def get_plugin_class(source_id: int) -> "type[BaseSourcePlugin] | None":
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry.get(source_id)


def reload_registry() -> None:
    """Force a full re-scan of the sources/ directory."""
    global _registry
    _registry = None
    _registry = _build_registry()
