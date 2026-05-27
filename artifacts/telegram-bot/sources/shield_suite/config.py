"""
Shield Suite runtime config — merges manifest defaults with per-bot overrides.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

_MANIFEST_PATH = Path(__file__).parent / "manifest.json"


def load_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = json.loads(_MANIFEST_PATH.read_text())
    schema   = manifest.get("config_schema", {})
    cfg      = {k: v["default"] for k, v in schema.items()}
    if overrides:
        for k, v in overrides.items():
            if k in cfg:
                cfg[k] = v
    return cfg
