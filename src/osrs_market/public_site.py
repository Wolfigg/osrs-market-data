from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from typing import Any

from .public_models import PUBLIC_SCHEMA_VERSION

PUBLIC_REQUIRED_FILES = (
    "index.html",
    "afk.html",
    "alchemy.html",
    "about.html",
    "assets/app.css",
    "assets/app.js",
    "data/dashboard.json",
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
        ("ledger", "index.html", "Ledger", "Today's Ledger"),
        ("afk", "afk.html", "AFK Methods", "Work Board"),
        ("alchemy", "alchemy.html", "High Alch", "Alchemist's Desk"),
        ("about", "about.html", "About", "Ledger Notes"),
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
        <p class="eyebrow">Merchant Ledger</p>
        <a class="brand" href="index.html">OSRS Profit Finder</a>
        <p class="subtitle">Live AFK and High Alch opportunities</p>
      </div>
      <div class="status-line" aria-live="polite">
        <span id="health-state" class="status-plaque">Loading</span>
        <span id="update-age">Checking latest ledger</span>
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


def _dashboard_page() -> str:
    main = """
<section class="page-heading">
  <p class="eyebrow">Today's Ledger</p>
  <h1>Current opportunities worth checking</h1>
  <p>The ledger separates passive or low-interaction methods from active High Alchemy trading.</p>
</section>
<section class="dashboard-grid" aria-label="Featured opportunities">
  <article id="featured-afk" class="ledger-panel featured-panel loading-panel">
    <div class="panel-heading"><span class="kicker">Featured AFK</span><h2>Loading work board...</h2></div>
  </article>
  <article id="featured-alch" class="trade-ticket loading-panel">
    <div class="ticket-heading"><span class="kicker">High Alch trade ticket</span><h2>Loading alchemist's desk...</h2></div>
  </article>
</section>
<section class="notice-board">
  <div class="section-heading"><p class="eyebrow">Notice Board</p><h2>Today's notices</h2></div>
  <div id="notices" class="notice-list" aria-live="polite"><p class="empty-state">Reading the ledger...</p></div>
</section>
<section class="route-board" aria-label="Explore tools">
  <a class="route-entry" href="afk.html"><strong>AFK Methods</strong><span>Search, filter and compare realistic low-interaction money makers.</span></a>
  <a class="route-entry" href="alchemy.html"><strong>High Alch</strong><span>Scan active buy-and-alch opportunities by practical four-hour profit.</span></a>
</section>
"""
    return _base("Ledger", "ledger", "dashboard", main)


def _afk_page() -> str:
    main = """
<section class="page-heading compact">
  <p class="eyebrow">Work Board</p>
  <h1>AFK Methods</h1>
  <p>Rank low-interaction methods using current observed prices, historical references, capital and interaction time.</p>
</section>
<section class="filter-frame" aria-label="AFK filters">
  <div class="filter-grid">
    <label class="field search-field"><span>Search</span><input id="afk-search" type="search" placeholder="Method name" autocomplete="off"></label>
    <label class="field"><span>Category</span><select id="afk-category"><option value="all">All categories</option></select></label>
    <fieldset class="segmented"><legend>Membership</legend><label><input type="radio" name="afk-membership" value="all" checked><span>All</span></label><label><input type="radio" name="afk-membership" value="f2p"><span>F2P</span></label><label><input type="radio" name="afk-membership" value="members"><span>Members</span></label></fieldset>
    <label class="field"><span>Profitability</span><select id="afk-profit"><option value="profitable" selected>Profitable only</option><option value="all">All</option></select></label>
    <label class="field"><span>AFK level</span><select id="afk-level"><option value="all">All levels</option><option>Light AFK</option><option>AFK</option><option>Very AFK</option><option>Deep AFK</option><option>Low interaction</option></select></label>
    <label class="field"><span>Sort</span><select id="afk-sort"><option value="gp-hour">Current GP/hour</option><option value="gp-24h">24H reference GP/hour</option><option value="gp-interaction">GP per interaction</option><option value="afk-interval">AFK interval</option><option value="capital">Lowest capital</option><option value="alphabetical">Alphabetical</option></select></label>
  </div>
</section>
<div class="ledger-toolbar"><p id="afk-count">Loading methods...</p><p class="muted">Select a row for requirements, history and market notes.</p></div>
<section id="afk-list" class="ranking-ledger" aria-live="polite"></section>
"""
    return _base("AFK Methods", "afk", "afk", main)


def _alchemy_page() -> str:
    main = """
<section class="page-heading compact">
  <p class="eyebrow">Alchemist's Desk</p>
  <h1>High Alch</h1>
  <p>Active trading scanner. High Alchemy is not classified or ranked as AFK.</p>
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


def _about_page() -> str:
    main = """
<section class="page-heading">
  <p class="eyebrow">Ledger Notes</p>
  <h1>About the Profit Finder</h1>
  <p>This public site is deliberately narrower than the collector behind it. It publishes decision-ready AFK and High Alch results, not raw market diagnostics.</p>
</section>
<div class="prose-ledger">
  <section><h2>What the site does</h2><p>AFK Methods ranks low-interaction money makers using current observed trade prices, sustainable throughput, Grand Exchange limits and historical reference margins. High Alch is a separate active money-making scanner ranked by practical four-hour opportunity.</p></section>
  <section><h2>Price source and fills</h2><p>Prices are derived from the OSRS Wiki real-time price service, which aggregates observed RuneLite trades. An observed high or low is evidence of recent trades, not a guarantee that your full order will fill at that price.</p></section>
  <section><h2>Historical references</h2><p>Historical comparisons use volume-weighted average prices across the supported windows. VWAP reduces the influence of isolated trades and provides a more useful reference than treating one old trade as the market.</p></section>
  <section><h2>Grand Exchange tax</h2><p>Where a method sells outputs through the Grand Exchange, the profit calculation accounts for seller tax and configured tax exemptions. Working capital covers purchased inputs, not reusable equipment.</p></section>
  <section><h2>AFK classification</h2><div class="definition-grid"><div><strong>30-44 sec</strong><span>Light AFK</span></div><div><strong>45-89 sec</strong><span>AFK</span></div><div><strong>90-179 sec</strong><span>Very AFK</span></div><div><strong>180+ sec</strong><span>Deep AFK</span></div></div><p>Bankstanding is treated as a separate method tag. These intervals describe expected interaction spacing, not a promise that every cycle is deterministic.</p></section>
  <section><h2>Why High Alch is separate</h2><p>High Alchemy requires continuous casting and is therefore active gameplay. It is not used as an exit strategy to make an AFK method appear more profitable.</p></section>
  <section><h2>Freshness and limitations</h2><p>The collector normally refreshes hourly. The masthead reports whether the public dataset is current, delayed or affected by a data issue. Thin markets, stale observations, buy limits and price movement can make realised results differ materially from the displayed calculation.</p></section>
</div>
"""
    return _base("About", "about", "about", main)


def write_public_site(
    output_dir: str | Path,
    dashboard: dict[str, Any],
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

    write_json(root / "data" / "dashboard.json", dashboard)
    write_json(root / "data" / "afk.json", afk)
    write_json(root / "data" / "alchemy.json", alchemy)
    write_json(root / "data" / "status.json", status)

    (root / "index.html").write_text(_dashboard_page(), encoding="utf-8")
    (root / "afk.html").write_text(_afk_page(), encoding="utf-8")
    (root / "alchemy.html").write_text(_alchemy_page(), encoding="utf-8")
    (root / "about.html").write_text(_about_page(), encoding="utf-8")

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

    forbidden_paths = ("market", "internal", "raw", "health.json", "index.json")
    for name in forbidden_paths:
        if (root / name).exists():
            raise ValueError(f"internal artifact leaked into public site: {name}")

    for name in ("dashboard.json", "afk.json", "alchemy.json", "status.json"):
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

    for page in ("index.html", "afk.html", "alchemy.html", "about.html"):
        text = (root / page).read_text(encoding="utf-8")
        if "Market Explorer" in text:
            raise ValueError(f"public Market Explorer found in {page}")
