# OSRS Profit Finder

A Python 3.12 market-analysis pipeline for Old School RuneScape using the OSRS Wiki / RuneLite Real-time Prices API.

The public application intentionally contains two tools:

1. **AFK Money Makers**: ranks genuinely AFK or low-interaction processing methods using live prices, historical VWAPs, GE tax, buy limits, liquidity, realistic rates, AFK interval metrics and a conservative Recommended GP/hour model.
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
- Recommended GP/hour
- weighted historical reference GP/hour
- 24H, 7D and 30D reference GP/hour
- stability state and current-vs-history deviations
- AFK interval
- GP per interaction
- one-hour and four-hour capital
- membership
- method tags
- requirements
- risk state

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

Recommended GP/hour is now the default AFK sort, while raw Current GP/hour remains available as an explicit sort option.

### Personal skill filtering

The AFK page allows users to enter relevant skill levels and enable:

```text
Only show methods I can do by skill level
```

The values are stored only in browser `localStorage`. No account, RuneLite login or server-side profile storage is used.

Skill matching does not imply that quest or equipment requirements are satisfied. Those remain visible separately.

The frontend also supports capital, method-type and stability filtering.

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
