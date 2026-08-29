# OSRS Profit Finder

A Python 3.12 market-analysis pipeline for Old School RuneScape using the OSRS Wiki / RuneLite Real-time Prices API.

The public application intentionally contains two tools:

1. **AFK Money Makers**: ranks genuinely AFK or low-interaction processing methods using live prices, historical VWAPs, GE tax, buy limits, liquidity, realistic rates and AFK interval metrics.
2. **High Alch**: a standalone active buy-and-alch scanner. It is deliberately not used as an exit for AFK methods.

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

The scheduled live workflow targets every five minutes. GitHub Actions scheduling is best-effort, so the UI derives freshness from the actual `generatedAt` timestamp rather than assuming the cron fired on time.

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

The simplified public product does not expose 6M/1Y Market Explorer data, so ordinary collection no longer downloads a per-item `24h` time series.

### Full mode

```bash
python -m osrs_market.cli collect --mode full --output build --cache-dir .market-cache
```

Full mode is intended for bootstrap, recovery and validation. It refreshes mapping plus the 5m, 1h and 6h historical sources and rewrites the derived cache.

A daily full workflow keeps mapping current and provides a recovery point.

## Derived historical cache

The collector persists only derived metrics needed by the application:

```text
.market-cache/
├── mapping.json
└── historical.json
```

The history cache tracks separate timestamps for short and long analysis:

```text
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
- 24H, 7D and 30D reference GP/hour
- AFK interval
- GP per interaction
- one-hour and four-hour capital
- membership
- method tags
- requirements
- risk state

The frontend also supports capital and method-type filtering.

The method catalogue remains configuration-driven in `config/methods.yaml`.

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

- `ci.yml`: tests on pushes and pull requests
- `refresh-live.yml`: lightweight `/latest` refresh and Pages deployment every five minutes
- `refresh-history.yml`: hourly short history, six-hour 30D history and daily full/bootstrap refresh

Both deployment workflows upload exactly:

```text
build/public-site
```

Maintainer diagnostics are uploaded separately as Actions artifacts.

No OSRS/Jagex credentials or API key are required.
