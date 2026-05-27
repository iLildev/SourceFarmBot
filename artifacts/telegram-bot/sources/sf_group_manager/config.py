"""SF Group Manager — config loader with defaults from manifest."""
from __future__ import annotations


DEFAULTS = {
    "welcome_enabled":     True,
    "welcome_text":        "👋 مرحباً {name} في {chat}!",
    "rules_text":          "📋 لا توجد قواعد محددة بعد.",
    "warn_limit":          3,
    "delete_service_msgs": True,
    "admin_only_cmds":     True,
}


def load_config(overrides: dict) -> dict:
    cfg = {**DEFAULTS}
    cfg.update({k: v for k, v in overrides.items() if k in DEFAULTS})
    return cfg
