from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=False, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(target)


def write_index_html(output_dir: str | Path, generated_at: int) -> None:
    path = Path(output_dir) / "index.html"
    path.write_text(
        "<!doctype html>\n"
        "<html lang=\"en\"><head><meta charset=\"utf-8\"><title>OSRS Market Data</title></head>\n"
        "<body><h1>OSRS Market Data</h1>\n"
        f"<p>Schema version {SCHEMA_VERSION}. Generated at Unix timestamp {generated_at}.</p>\n"
        "<ul>"
        '<li><a href="index.json">index.json</a></li>'
        '<li><a href="health.json">health.json</a></li>'
        '<li><a href="market.json">market.json</a></li>'
        '<li><a href="alchemy.json">alchemy.json</a></li>'
        '<li><a href="opportunities.json">opportunities.json</a></li>'
        '<li><a href="methods.json">methods.json</a></li>'
        "</ul>\n"
        "<p>Historical observed volume is a liquidity proxy, not executable market depth.</p>\n"
        "</body></html>\n",
        encoding="utf-8",
    )


def validate_site(output_dir: str | Path) -> None:
    root = Path(output_dir)
    required = ["index.json", "health.json", "market.json", "alchemy.json", "opportunities.json", "methods.json"]
    for name in required:
        path = root / name
        if not path.is_file():
            raise ValueError(f"missing generated file: {name}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"generated file is not an object: {name}")
        if payload.get("schemaVersion") != SCHEMA_VERSION:
            raise ValueError(f"invalid schemaVersion in {name}")

    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    if not index.get("generatedAt"):
        raise ValueError("index.json missing generatedAt")
    market = json.loads((root / "market.json").read_text(encoding="utf-8"))
    if not isinstance(market.get("items"), list) or not market["items"]:
        raise ValueError("market.json contains no tracked items")
