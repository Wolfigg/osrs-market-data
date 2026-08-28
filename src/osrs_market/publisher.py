from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(target)


def _gp(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.0f}"


def _pct(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value):.2f}%"


def _esc(value: Any) -> str:
    return html.escape(str(value))


def write_dashboard(
    output_dir: str | Path,
    generated_at: int,
    afk_rankings: list[dict[str, Any]] | None = None,
    alchemy_candidates: list[dict[str, Any]] | None = None,
    market_items: list[dict[str, Any]] | None = None,
) -> None:
    """Write a static, no-JavaScript dashboard from generated results."""
    root = Path(output_dir)
    if afk_rankings is None:
        afk_rankings = json.loads((root / "afk" / "rankings.json").read_text(encoding="utf-8"))["rankings"]
    if alchemy_candidates is None:
        alchemy_candidates = json.loads((root / "alchemy" / "rankings.json").read_text(encoding="utf-8"))["candidates"]
    if market_items is None:
        market_items = json.loads((root / "market" / "summary.json").read_text(encoding="utf-8"))["items"]

    generated = datetime.fromtimestamp(generated_at, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    current_afk = [row for row in afk_rankings if row["scenario"] == "CURRENT_INSTANT"]
    current_afk.sort(key=lambda row: row["profitGpPerHour"] if row["valid"] and row["profitGpPerHour"] is not None else float("-inf"), reverse=True)
    hist24_by_id = {row["methodId"]: row for row in afk_rankings if row["scenario"] == "HISTORICAL_INSTANT_24H"}

    afk_rows: list[str] = []
    for row in current_afk:
        hist = hist24_by_id.get(row["methodId"], {})
        warnings = ", ".join(row.get("warnings") or []) or "None"
        status = "OK" if row.get("valid") else "CHECK"
        afk_rows.append(
            "<tr>"
            f"<td><strong>{_esc(row['name'])}</strong><br><span class='muted'>{_esc(row.get('category', ''))}</span></td>"
            f"<td class='num'>{_gp(row.get('profitGpPerHour'))}</td>"
            f"<td class='num'>{_gp(hist.get('profitGpPerHour'))}</td>"
            f"<td class='num'>{_gp(row.get('afkIntervalSeconds'))} s</td>"
            f"<td class='num'>{_gp(row.get('gpPerInteractionWindow'))}</td>"
            f"<td class='num'>{_gp(row.get('outputUnitsPerHour'))}</td>"
            f"<td>{_esc(status)}</td><td class='muted'>{_esc(warnings)}</td></tr>"
        )

    alch_sorted = sorted(
        [c for c in alchemy_candidates if c.get("currentInstant", {}).get("valid")],
        key=lambda c: c.get("profitPer4hGeLimit") if c.get("profitPer4hGeLimit") is not None else float("-inf"),
        reverse=True,
    )[:30]
    alch_rows: list[str] = []
    for row in alch_sorted:
        cur = row.get("currentInstant", {})
        warnings = ", ".join(row.get("warnings") or []) or "None"
        alch_rows.append(
            "<tr>"
            f"<td><strong>{_esc(row['name'])}</strong><br><span class='muted'>{'F2P' if row.get('f2p') else 'P2P'}</span></td>"
            f"<td class='num'>{_gp(cur.get('buyPrice'))}</td><td class='num'>{_gp(row.get('highAlchValue'))}</td>"
            f"<td class='num'>{_gp(cur.get('profitPerCast'))}</td><td class='num'>{_pct(cur.get('roiPct'))}</td>"
            f"<td class='num'>{_gp(row.get('capacity4h', {}).get('maxQuantity'))}</td>"
            f"<td class='num'>{_gp(row.get('profitPer4hGeLimit'))}</td><td class='num'>{_gp(row.get('volume24h'))}</td>"
            f"<td class='muted'>{_esc(warnings)}</td></tr>"
        )

    market_rows: list[str] = []
    for record in sorted(market_items, key=lambda x: x["item"]["name"].lower()):
        item = record["item"]
        cur = record["current"]
        w24 = record.get("windows", {}).get("24h", {})
        w7 = record.get("windows", {}).get("7d", {})
        warnings = ", ".join(record.get("quality", {}).get("warnings") or []) or "None"
        market_rows.append(
            "<tr>"
            f"<td><strong>{_esc(item['name'])}</strong><br><span class='muted'>ID {_esc(item['id'])}</span></td>"
            f"<td class='num'>{_gp(cur.get('high'))}</td><td class='num'>{_gp(cur.get('low'))}</td><td>{_esc(cur.get('freshness'))}</td>"
            f"<td class='num'>{_gp(w24.get('highVwap'))}</td><td class='num'>{_gp(w24.get('lowVwap'))}</td>"
            f"<td class='num'>{_gp(w24.get('totalVolume'))}</td><td class='num'>{_pct(w24.get('changePct'))}</td>"
            f"<td class='num'>{_gp(w7.get('totalVolume'))}</td><td class='muted'>{_esc(warnings)}</td></tr>"
        )

    document = f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>OSRS Profit Finder</title><style>
:root{{color-scheme:dark;font-family:Inter,system-ui,sans-serif;background:#0f1115;color:#e8eaed}}body{{max-width:1450px;margin:0 auto;padding:24px}}h1{{margin-bottom:4px}}h2{{margin-top:36px}}a{{color:#8ab4f8}}.muted{{color:#9aa0a6;font-size:.9em}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:20px 0}}.card{{background:#171a20;border:1px solid #2b3038;border-radius:10px;padding:16px}}.table-wrap{{overflow-x:auto;border:1px solid #2b3038;border-radius:10px}}table{{width:100%;border-collapse:collapse;background:#15181e;font-size:14px}}th,td{{padding:10px 12px;border-bottom:1px solid #292e36;text-align:left;white-space:nowrap}}th{{background:#1c2027;position:sticky;top:0}}td.num,th.num{{text-align:right}}.note{{padding:12px 14px;border-left:3px solid #7aa2f7;background:#171a20;margin:12px 0}}
</style></head><body>
<h1>OSRS Profit Finder</h1><p class='muted'>Generated {_esc(generated)}. Prices are observed RuneLite/Wiki transactions, not executable order-book depth.</p>
<div class='cards'><div class='card'><strong>AFK Money Makers</strong><p>Realistic AFK processing profitability. GE exits only.</p><a href='afk/rankings.json'>JSON rankings</a></div><div class='card'><strong>High Alch</strong><p>Standalone active buy-and-alch opportunities.</p><a href='alchemy/rankings.json'>JSON candidates</a></div><div class='card'><strong>Market Explorer</strong><p>Current prices, VWAP, volume, trend and quality.</p><a href='market/summary.json'>JSON market data</a></div></div>
<h2>AFK Money Makers</h2><div class='note'>High Alchemy is intentionally excluded from this branch. Current instant buys inputs at observed high and sells outputs at observed low after GE tax. 24H uses historical high-side and low-side VWAPs.</div><div class='table-wrap'><table><thead><tr><th>Method</th><th class='num'>Current GP/h</th><th class='num'>24H GP/h</th><th class='num'>AFK interval</th><th class='num'>GP / interaction</th><th class='num'>Output/h</th><th>Status</th><th>Warnings</th></tr></thead><tbody>{''.join(afk_rows)}</tbody></table></div>
<h2>High Alch</h2><div class='note'>Ranked here by profit per 4-hour GE limit, rather than theoretical 1,200-cast GP/hour, so tiny buy-limit opportunities do not dominate the useful list.</div><div class='table-wrap'><table><thead><tr><th>Item</th><th class='num'>Buy</th><th class='num'>Alch</th><th class='num'>Profit/cast</th><th class='num'>ROI</th><th class='num'>4H qty</th><th class='num'>4H profit</th><th class='num'>24H volume</th><th>Warnings</th></tr></thead><tbody>{''.join(alch_rows)}</tbody></table></div>
<h2>Market Explorer</h2><div class='table-wrap'><table><thead><tr><th>Item</th><th class='num'>Current high</th><th class='num'>Current low</th><th>Freshness</th><th class='num'>24H high VWAP</th><th class='num'>24H low VWAP</th><th class='num'>24H volume</th><th class='num'>24H change</th><th class='num'>7D volume</th><th>Warnings</th></tr></thead><tbody>{''.join(market_rows)}</tbody></table></div>
<p class='muted'>Machine entry point: <a href='index.json'>index.json</a>. Collector status: <a href='health.json'>health.json</a>.</p></body></html>"""
    (root / "index.html").write_text(document, encoding="utf-8")


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
