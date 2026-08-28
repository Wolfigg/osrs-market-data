from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from .api import ApiSettings


def load_yaml(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return payload or {}


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def api_settings(settings: dict[str, Any]) -> ApiSettings:
    raw = settings["api"]
    user_agent = os.environ.get("OSRS_MARKET_USER_AGENT") or str(raw["user_agent"])
    if "set OSRS_MARKET_USER_AGENT" in user_agent:
        raise ValueError("set OSRS_MARKET_USER_AGENT to a descriptive contact/repository User-Agent before collecting")
    return ApiSettings(
        base_url=str(raw["base_url"]),
        user_agent=user_agent,
        request_spacing_ms=int(raw.get("request_spacing_ms", 250)),
        timeout_seconds=int(raw.get("timeout_seconds", 20)),
        retries=int(raw.get("retries", 4)),
    )
