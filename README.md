# OSRS Market Board

A Python 3.12 market-analysis pipeline for Old School RuneScape using the OSRS Wiki / RuneLite Real-time Prices API.

The public application intentionally contains two tools:

1. **AFK Money Makers**: ranks genuinely AFK or low-interaction processing methods using live prices, 6H/24H/7D/30D/6M historical VWAPs, GE tax, buy limits, liquidity, audited game mechanics, AFK interval metrics and a conservative Expected GP/hour model.
2. **High Alch**: a standalone active buy-and-alch scanner with the same historical price horizons. It is deliberately not used as an exit for AFK methods.

There is no public Market Explorer, raw API browser, diagnostics page or dashboard branch.

## Public and internal artifacts

Collection writes two explicitly separated artifact trees:

```text
build/
├── public-site/
│   ├── index.html
│   ├── alchemy.html
│   ├── assets/
│   │   ├── app.css
│   │   └── app.js
│   └── data/
│       ├── afk.json
│       ├── alchemy.json
│       └── status.json
└── internal-report/
    ├── health.json
    ├── market/
    ├── afk/
    └── alchemy/
```

GitHub Pages uploads **only** `build/public-site`. Anything in `build/internal-report` is maintainer diagnostics and must never be included in the Pages artifact.

`validate_public_site(...)` rejects known internal paths and fields if they appear under the public artifact tree.

## Refresh architecture

Current profitability and historical analysis have different freshness requirements, so they no longer share one all-or-nothing collection job.

### Live mode

```bash
python -m osrs_market.cli collect --mode live --output build --cache-dir .market-cache
```

Live mode:

- loads cached mapping, falling back to `/mapping` only when needed
- fetches `/latest`
- recalculates current AFK profitability
- reruns the High Alch preliminary scan and current margins
- combines current values with cached historical metrics
- makes **zero** `/timeseries` requests
- rebuilds the public and internal artifacts

The scheduled live workflow uses explicit ten-minute slots (`7,17,27,37,47,57`). GitHub Actions scheduling is best-effort, so the UI derives freshness from the actual `generatedAt` timestamp rather than assuming the cron fired on time.

### Short-history mode

```bash
python -m osrs_market.cli collect --mode short --output build --cache-dir .market-cache
```

Short mode refreshes:

| Public metric | API timestep |
| --- | --- |
| 6H | 5m |
| 24H | 5m |
| 7D | 1h |

It runs hourly.

### Long-history mode

```bash
python -m osrs_market.cli collect --mode long --output build --cache-dir .market-cache
```

Long mode refreshes:

| Public metric | API timestep |
| --- | --- |
| 30D | 6h |

It runs every six hours.

The six-month reference uses the API's `24h` time series and refreshes in the daily full collection. One-year Market Explorer data remains outside the public product.

### Full mode

```bash
python -m osrs_market.cli collect --mode full --output build --cache-dir .market-cache
```

Full mode is intended for bootstrap, recovery and validation. It refreshes mapping plus the 5m, 1h, 6h and 24h historical sources and rewrites the derived cache.

A daily full workflow keeps mapping current and provides a recovery point.

## Derived historical cache

The collector persists only derived metrics needed by the application:

```text
.market-cache/
├── mapping.json
└── historical.json
```

The history cache records provenance plus overall and per-tier timestamps:

```text
generatedAt
source
status
shortGeneratedAt
longGeneratedAt
```

Live refreshes read these metrics but do not overwrite them. A failed time-series request never replaces a previously valid cached window with an empty failed result.

GitHub Actions restores the newest historical cache for live/history jobs and saves a new cache only after historical refreshes.

## Market data semantics

`high` and `low` from `/latest` are independent observed transaction streams, not a live order book. The application does not present them as guaranteed GE buy/sell prices.

The timestamp of a site refresh and the timestamp of an item's latest observed trade are separate concepts. Current calculations continue to use transaction-side freshness checks.

Historical observed volume is a liquidity proxy, not executable market depth.

## AFK branch

The AFK branch uses Grand Exchange exits only. High Alchemy is intentionally excluded as an AFK output strategy.

Public AFK data includes:

- current GP/hour
- Recommended GP/hour
- weighted historical reference GP/hour
- 24H, 7D and 30D reference GP/hour
- stability state and current-vs-history deviations
- AFK interval
- GP per interaction
- one-hour and four-hour capital, including fixed coin costs
- membership
- method tags
- requirements
- risk state

### Mechanically audited catalogue

Every enabled method must pass structural validation and carry an OSRS Wiki-backed `audit.status: verified`. Collection fails rather than publishing an enabled method without verified audit provenance.

The completion audit covers the generated and hand-tuned families, including cannonballs, bolt tips, dart tips, Plank Make, longbows, cooking, jewellery, glassblowing, battlestaves and gathering methods. Detailed assumptions and corrections are recorded in:

```text
config/method_audit.yaml
docs/AFK_METHOD_CATALOG_AUDIT.md
```

Reusable equipment is represented as a requirement, not as a consumed input. Fixed coin charges such as Plank Make fees are included in capital calculations.

### Stability model

The first version intentionally uses explicit constants instead of an opaque score.

Historical reference weights are:

```text
24H: 50%
7D:  30%
30D: 20%
```

Public stability states are:

```text
Stable
Watch
Volatile
Thin market
Stale
Unavailable
```

Current-vs-history deviation thresholds are intentionally conservative:

```text
Stable band:       under 15%
Volatile trigger:  35% or more
```

Historical-reference spread also contributes to the state. Missing historical windows cannot produce `Stable`.

### Recommended GP/hour

Recommended GP/hour does not replace raw current profitability. Both remain visible.

The initial formula is deliberately simple and auditable:

```text
Stable:
    50% current + 50% historical reference

Watch:
    25% current + 75% historical reference

Volatile:
    min(current, historical reference * 1.15)

Thin market:
    (25% current + 75% historical reference) * 0.80

Stale / Unavailable:
    null
```

Negative-profit cases are kept conservative by choosing the lower of current and reference rather than blending a loss upward.

Recommended GP/hour is the default AFK sort, while raw Current GP/hour remains available as an explicit sort option.

### Optional eligibility filtering

The AFK page allows users to enter relevant skill levels and enable:

```text
Only show methods I can do by skill level
```

The values are lightweight local eligibility controls only. There is no account, login, or server-side profile.

The controls include skills currently used by the catalogue, including Sailing for current content such as camphor logging.

Skill matching does not imply that quest or equipment requirements are satisfied. Those remain visible separately.

The frontend also supports capital, method-type and stability filtering.

## High Alch branch

The High Alch scanner first performs a cheap universe scan using `/mapping` and `/latest` and then uses cached historical metrics for selected candidates.

Public High Alch data includes:

- current profit/cast
- 24H profit/cast
- 7D profit/cast
- 30D profit/cast
- ROI
- practical four-hour quantity and profit
- capital required
- membership
- price freshness
- recent volume context

Historical item and rune prices use matching windows.

## Freshness contract

The public header uses actual dataset age:

```text
< 90 minutes       Current
90m through 2.5h   Delayed
> 2.5 hours        Stale
```

Short-history and 30D-history ages are shown separately from live data freshness. Exactly 2.5 hours remains `Delayed`.

## Run locally

```bash
python -m venv .venv
pip install -r requirements.txt
pip install -e .
pytest
python -m osrs_market.cli collect --mode full --output build --cache-dir .market-cache
python -m http.server --directory build/public-site 8000
```

Set a descriptive User-Agent before collection:

```bash
export OSRS_MARKET_USER_AGENT="osrs-market-data/0.3 - github.com/Wolfigg/osrs-market-data"
```

## GitHub Actions

The responsibilities are intentionally separated:

- `ci.yml`: Python regression tests plus deterministic Chromium/Firefox browser acceptance on pull requests and pushes
- `refresh-live.yml`: lightweight `/latest` refresh and Pages deployment at explicit ten-minute schedule slots
- `refresh-history.yml`: hourly short history, six-hour 30D history and daily full/bootstrap refresh

The browser acceptance suite uses a synthetic static dataset. It tests the actual generated HTML/CSS/JS without making live market API calls and covers 360, 390, 768 and desktop widths, filters, URL restoration, local skill storage, details, capital boundaries, unavailable rows and freshness boundaries.

Both deployment workflows upload exactly:

```text
build/public-site
```

Maintainer diagnostics are uploaded separately as Actions artifacts.

No OSRS/Jagex credentials or API key are required.

## Completion documentation

`docs/IMPLEMENTATION_CHECKLIST.md` is the current definition-of-done checklist for the two-tool product. The obsolete Market Explorer-era checklist has been removed.
