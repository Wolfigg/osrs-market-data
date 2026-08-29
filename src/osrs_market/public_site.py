from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from typing import Any

from .public_models import PUBLIC_SCHEMA_VERSION

PUBLIC_REQUIRED_FILES = (
    "index.html",
    "alchemy.html",
    "assets/app.css",
    "assets/app.js",
    "data/afk.json",
    "data/alchemy.json",
    "data/status.json",
)

FORBIDDEN_PUBLIC_KEYS = {
    "series",
    "latest",
    "quality",
    "api",
    "inputPriceBasis",
    "outputPriceBasis",
    "timeseriesRequested",
    "timeseriesSucceeded",
    "timeseriesFailed",
}


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(target)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _nav(active: str) -> str:
    links = [
        ("afk", "index.html", "AFK Money Makers", "Work Board"),
        ("alchemy", "alchemy.html", "High Alch", "Alchemist's Desk"),
    ]
    return "".join(
        f'<a class="nav-link{" active" if key == active else ""}" href="{href}"'
        f'{" aria-current=\"page\"" if key == active else ""}>'
        f'<span>{label}</span><small>{secondary}</small></a>'
        for key, href, label, secondary in links
    )


def _base(title: str, active: str, page: str, main: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light">
  <meta name="description" content="OSRS Profit Finder: live AFK money-making and High Alchemy opportunities using observed OSRS Wiki market prices.">
  <title>{_esc(title)} | OSRS Profit Finder</title>
  <link rel="stylesheet" href="assets/app.css">
  <script defer src="assets/app.js"></script>
</head>
<body data-page="{_esc(page)}">
  <a class="skip-link" href="#main">Skip to content</a>
  <div class="site-shell">
    <header class="masthead">
      <div class="masthead-title">
        <p class="eyebrow">Grand Exchange Work Board</p>
        <a class="brand" href="index.html">OSRS Profit Finder</a>
        <p class="subtitle">Live AFK money makers and High Alch opportunities</p>
      </div>
      <div class="status-line" aria-live="polite">
        <span id="health-state" class="status-plaque">Loading</span>
        <span id="update-age">Checking latest market scan</span>
      </div>
      <nav class="main-nav" aria-label="Primary">{_nav(active)}</nav>
    </header>
    <main id="main" class="page-surface">{main}</main>
    <footer class="site-footer">
      <p>Observed RuneLite/Wiki trades are market observations, not guaranteed Grand Exchange fills.</p>
      <p>Old School RuneScape and RuneScape are trademarks of Jagex. This is an independent fan tool.</p>
    </footer>
  </div>
</body>
</html>"""


def _afk_page() -> str:
    main = """
<section class="page-heading compact">
  <p class="eyebrow">Work Board</p>
  <h1>AFK Money Makers</h1>
  <p>Compare low-interaction methods using current observed prices, 24-hour, 7-day and 30-day references, capital requirements and interaction time.</p>
</section>
<section class="filter-frame" aria-label="AFK filters">
  <div class="filter-grid">
    <label class="field search-field"><span>Search</span><input id="afk-search" type="search" placeholder="Method name" autocomplete="off"></label>
    <label class="field"><span>Category</span><select id="afk-category"><option value="all">All categories</option></select></label>
    <fieldset class="segmented"><legend>Membership</legend><label><input type="radio" name="afk-membership" value="all" checked><span>All</span></label><label><input type="radio" name="afk-membership" value="f2p"><span>F2P</span></label><label><input type="radio" name="afk-membership" value="members"><span>Members</span></label></fieldset>
    <label class="field"><span>Profitability</span><select id="afk-profit"><option value="profitable" selected>Profitable only</option><option value="all">All</option></select></label>
    <label class="field"><span>AFK level</span><select id="afk-level"><option value="all">All levels</option><option>Light AFK</option><option>AFK</option><option>Very AFK</option><option>Deep AFK</option><option>Low interaction</option></select></label>
    <label class="field"><span>Sort</span><select id="afk-sort"><option value="gp-hour">Current GP/hour</option><option value="gp-24h">24H reference GP/hour</option><option value="gp-7d">7D reference GP/hour</option><option value="gp-30d">30D reference GP/hour</option><option value="gp-interaction">GP per interaction</option><option value="afk-interval">AFK interval</option><option value="capital">Lowest capital</option><option value="alphabetical">Alphabetical</option></select></label>
  </div>
</section>
<div class="ledger-toolbar"><p id="afk-count">Loading methods...</p><p class="muted">Select a row for requirements, full history and market notes.</p></div>
<section id="afk-list" class="ranking-ledger" aria-live="polite"></section>
"""
    return _base("AFK Money Makers", "afk", "afk", main)


def _alchemy_page() -> str:
    main = """
<section class="page-heading compact">
  <p class="eyebrow">Alchemist's Desk</p>
  <h1>High Alch</h1>
  <p>Active trading scanner. High Alchemy is kept separate from AFK money making.</p>
</section>
<section class="filter-frame" aria-label="High Alch filters">
  <div class="filter-grid alch-filters">
    <label class="field search-field"><span>Item search</span><input id="alch-search" type="search" placeholder="Item name" autocomplete="off"></label>
    <fieldset class="segmented"><legend>Membership</legend><label><input type="radio" name="alch-membership" value="all" checked><span>All</span></label><label><input type="radio" name="alch-membership" value="f2p"><span>F2P</span></label><label><input type="radio" name="alch-membership" value="members"><span>Members</span></label></fieldset>
    <label class="field"><span>Profitability</span><select id="alch-profit"><option value="profitable" selected>Profitable only</option><option value="all">All</option></select></label>
    <label class="field"><span>Minimum profit/cast</span><input id="alch-min-profit" type="number" value="0" min="0" step="1"></label>
    <label class="field"><span>Sort</span><select id="alch-sort"><option value="profit-4h">Practical 4H profit</option><option value="profit-cast">Profit per cast</option><option value="roi">ROI</option><option value="capital">Lowest capital</option><option value="volume">24H volume</option></select></label>
    <label class="checkbox-field"><input id="alch-unavailable" type="checkbox"><span>Show unavailable / stale</span></label>
  </div>
</section>
<div class="ledger-toolbar"><p id="alch-count">Loading candidates...</p><p class="muted">Requirement: 55 Magic.</p></div>
<section id="alch-list" class="alchemy-ledger" aria-live="polite"></section>
"""
    return _base("High Alch", "alchemy", "alchemy", main)


def write_public_site(
    output_dir: str | Path,
    afk: dict[str, Any],
    alchemy: dict[str, Any],
    status: dict[str, Any],
    assets_dir: str | Path = "web/assets",
) -> None:
    root = Path(output_dir)
    if root.exists():
        shutil.rmtree(root)
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir(parents=True, exist_ok=True)

    write_json(root / "data" / "afk.json", afk)
    write_json(root / "data" / "alchemy.json", alchemy)
    write_json(root / "data" / "status.json", status)

    (root / "index.html").write_text(_afk_page(), encoding="utf-8")
    (root / "alchemy.html").write_text(_alchemy_page(), encoding="utf-8")

    assets = Path(assets_dir)
    for filename in ("app.css", "app.js"):
        shutil.copy2(assets / filename, root / "assets" / filename)

    validate_public_site(root)


def _walk_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(str(key))
            found.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_walk_keys(child))
    return found


def validate_public_site(output_dir: str | Path) -> None:
    root = Path(output_dir)
    for name in PUBLIC_REQUIRED_FILES:
        if not (root / name).is_file():
            raise ValueError(f"missing public-site file: {name}")

    forbidden_paths = (
        "market",
        "internal",
        "raw",
        "health.json",
        "index.json",
        "about.html",
        "afk.html",
        "data/dashboard.json",
    )
    for name in forbidden_paths:
        if (root / name).exists():
            raise ValueError(f"unwanted or internal artifact leaked into public site: {name}")

    for name in ("afk.json", "alchemy.json", "status.json"):
        payload = json.loads((root / "data" / name).read_text(encoding="utf-8"))
        if payload.get("schemaVersion") != PUBLIC_SCHEMA_VERSION:
            raise ValueError(f"invalid public schemaVersion in data/{name}")
        leaked = FORBIDDEN_PUBLIC_KEYS & _walk_keys(payload)
        if leaked:
            raise ValueError(f"internal fields leaked into data/{name}: {sorted(leaked)}")

    afk = json.loads((root / "data" / "afk.json").read_text(encoding="utf-8"))
    if not isinstance(afk.get("methods"), list):
        raise ValueError("data/afk.json methods must be a list")
    alchemy = json.loads((root / "data" / "alchemy.json").read_text(encoding="utf-8"))
    if not isinstance(alchemy.get("items"), list):
        raise ValueError("data/alchemy.json items must be a list")

    for page in ("index.html", "alchemy.html"):
        text = (root / page).read_text(encoding="utf-8")
        if "Market Explorer" in text:
            raise ValueError(f"public Market Explorer found in {page}")
        if ">Ledger<" in text or ">About<" in text:
            raise ValueError(f"removed navigation item found in {page}")
