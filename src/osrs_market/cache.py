from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION
from .models import MappingItem


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"cache file is not an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_mapping(cache_dir: Path) -> tuple[dict[int, MappingItem], int | None] | None:
    payload = _read_json(cache_dir / "mapping.json")
    if payload is None:
        return None
    rows = payload.get("items")
    if not isinstance(rows, list):
        raise ValueError("mapping cache items must be a list")
    mapping = {item.id: item for item in (MappingItem.from_api(row) for row in rows)}
    return mapping, _optional_int(payload.get("generatedAt"))


def save_mapping(cache_dir: Path, mapping: dict[int, MappingItem], generated_at: int) -> None:
    _write_json(
        cache_dir / "mapping.json",
        {
            "schemaVersion": SCHEMA_VERSION,
            "generatedAt": int(generated_at),
            "source": "osrs-wiki",
            "status": "ok",
            "items": [mapping[item_id].to_dict() for item_id in sorted(mapping)],
        },
    )


def load_history(cache_dir: Path) -> dict[str, Any]:
    payload = _read_json(cache_dir / "historical.json")
    if payload is None:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "shortGeneratedAt": None,
            "longGeneratedAt": None,
            "items": {},
        }
    if not isinstance(payload.get("items"), dict):
        raise ValueError("historical cache items must be an object")
    payload.setdefault("shortGeneratedAt", None)
    payload.setdefault("longGeneratedAt", None)
    return payload


def save_history(cache_dir: Path, payload: dict[str, Any]) -> None:
    normalized = {
        "schemaVersion": SCHEMA_VERSION,
        "source": "osrs-wiki",
        "status": "ok",
        "shortGeneratedAt": payload.get("shortGeneratedAt"),
        "longGeneratedAt": payload.get("longGeneratedAt"),
        "items": payload.get("items", {}),
    }
    _write_json(cache_dir / "historical.json", normalized)


def item_windows(history: dict[str, Any], item_id: int) -> dict[str, dict[str, Any]]:
    items = history.get("items") or {}
    windows = items.get(str(int(item_id))) or {}
    return dict(windows) if isinstance(windows, dict) else {}


def put_item_windows(history: dict[str, Any], item_id: int, windows: dict[str, dict[str, Any]]) -> None:
    items = history.setdefault("items", {})
    current = items.setdefault(str(int(item_id)), {})
    current.update(windows)


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None
