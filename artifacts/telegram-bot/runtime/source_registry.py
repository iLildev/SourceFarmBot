"""
Maps source_id → plugin class for in-process bot launching.
Add every new source here.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.plugin_base import BaseSourcePlugin


def get_plugin_class(source_id: int) -> "type[BaseSourcePlugin] | None":
    """Return the plugin class for the given source_id, or None if unknown."""
    if source_id == 1:
        from sources.shield_suite.plugin import ShieldSuitePlugin
        return ShieldSuitePlugin
    if source_id == 2:
        from sources.sf_group_manager.plugin import GroupManagerPlugin
        return GroupManagerPlugin
    return None
