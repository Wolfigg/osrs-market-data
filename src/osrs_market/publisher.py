from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(target)


def write_dashboard(output_dir: str | Path, generated_at: int) -> None:
    path = Path(output_dir) / "index.html"
    path.write_text(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>OSRS Profit Finder</title><style>body{font-family:system-ui;max-width:900px;margin:40px auto;padding:0 18px;background:#101217;color:#eee}"
        "a{color:#8ab4f8}.card{background:#191c22;border:1px solid #30343c;border-radius:10px;padding:18px;margin:14px 0}.muted{color:#aaa}</style></head><body>"
        "<h1>OSRS Profit Finder</h1><p class='muted'>Three separate data surfaces built from the same real-time market core.</p>"
        "<div class='card'><h2>AFK Money Makers</h2><p>Grand Exchange exits only. High Alchemy is deliberately excluded.</p>"
        "<p><a href='afk/rankings.json'>AFK rankings</a> · <a href='afk/methods.json'>Full AFK method results</a></p></div>"
        "<div class='card'><h2>High Alch</h2><p>Standalone active money-making scanner.</p>"
        "<p><a href='alchemy/rankings.json'>High Alch rankings</a> · <a href='alchemy/candidates.json'>Candidate data</a></p></div>"
        "<div class='card'><h2>Market Explorer</h2><p>Current prices, historical windows, volume, VWAP, spread, volatility and freshness.</p>"
        "<p><a href='market/summary.json'>Market summary</a> · <a href='index.json'>Machine-readable index</a> · <a href='health.json'>Collector health</a></p></div>"
        f"<p class='muted'>Generated at Unix timestamp {generated_at}. Historical volume is a liquidity proxy, not executable market depth.</p>"
        "</body></html>",
        encoding="utf-8",
    )


def validate_site(output_dir: str | Path) -> None:
    root = Path(output_dir)
    required = ["index.json", "health.json", "market/summary.json", "afk/methods.json", "afk/rankings.json", "alchemy/candidates.json", "alchemy/rankings.json"]
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
    market = json.loads((root / "market" / "summary.json").read_text(encoding="utf-8"))
    if not isinstance(market.get("items"), list) or not market["items"]:
        raise ValueError("market/summary.json contains no items")
    afk = json.loads((root / "afk" / "methods.json").read_text(encoding="utf-8"))
    if not isinstance(afk.get("results"), list) or not afk["results"]:
        raise ValueError("afk/methods.json contains no evaluated methods")
