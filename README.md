# OSRS Market Data, Profitability and Alchemy Engine

A deterministic Python 3.12 pipeline for collecting Old School RuneScape market data from the OSRS Wiki / RuneLite Real-time Prices API, calculating market-window statistics, evaluating processing methods and High Level Alchemy opportunities, then publishing compact JSON through GitHub Pages.

The project intentionally does not scrape the OSRS Wiki website and does not attempt to reconstruct a Grand Exchange order book.

## Core market semantics

The Prices API reports observed player transactions.

- `high` is the most recent observed transaction conventionally associated with an instant buy.
- `low` is the most recent observed transaction conventionally associated with an instant sell.
- `highTime` and `lowTime` are independent timestamps.
- `high` and `low` are not a synchronized bid/ask quote.
- `high < low` can legitimately occur. The collector flags this as `crossed: true` and does not swap the values.
- Historical observed volume is a liquidity proxy, not executable market depth.

A file generated one minute ago can still contain a price whose last transaction happened hours or days ago. For that reason, the output always preserves price timestamps and emits age/freshness diagnostics.

## What the collector produces

Tracked items fetch all four V1 time-series resolutions:

- `5m`
- `1h`
- `6h`
- `24h`

Logical windows are reconstructed by timestamp, not by blindly taking the last N array elements:

| Window | Source resolution |
| --- | --- |
| 6H | 5m |
| 24H | 5m |
| 7D | 1h |
| 30D | 6h |
| 6M | 24h |
| 1Y | 24h |

Each window contains high-side and low-side volume, VWAP, min/max values, midpoint change, median spread, descriptive log-return volatility and data coverage.

## Output files

A successful collection generates:

```text
site/
├── index.html
├── index.json
├── health.json
├── market.json
├── alchemy.json
├── opportunities.json
├── methods.json
└── items/
    └── <item_id>.json
```

`index.json` is the stable machine-readable entry point. A consumer can inspect `generatedAt` and `schemaVersion`, then request only the files it needs.

Generated `site/` data is ignored by Git and is intended to be deployed as a GitHub Pages artifact instead of committed every hour.

## Local setup

```bash
python -m venv .venv
```

Activate the environment, then install the project:

```bash
pip install -r requirements.txt
pip install -e .
```

Set a descriptive API User-Agent. The OSRS Wiki API asks clients not to use the default `python-requests` user agent.

Linux/macOS:

```bash
export OSRS_MARKET_USER_AGENT="osrs-market-data/1.0 - github.com/your-user/your-repo"
```

PowerShell:

```powershell
$env:OSRS_MARKET_USER_AGENT = "osrs-market-data/1.0 - github.com/your-user/your-repo"
```

Run tests:

```bash
pytest
```

Collect data:

```bash
python -m osrs_market.cli collect --output site
```

Serve the generated files locally:

```bash
python -m http.server --directory site 8000
```

## Adding tracked items

Edit `config/tracked_items.json`:

```json
{
  "items": [
    {"id": 13190, "label": "Old school bond"},
    {"id": 2, "label": "Cannonball"}
  ]
}
```

The canonical item name comes from `/mapping`. The optional label is informational only.

## Adding a processing method

Edit `config/methods.yaml`:

```yaml
methods:
  example_method:
    enabled: true
    name: Example processing method
    inputs:
      - item_id: 123
        quantity: 1
        buy_via_ge: true
    fixed_cost_gp_per_cycle: 0
    outputs:
      - item_id: 456
        quantity: 1
        exit: ge
    cycles_per_hour: 1200
    planned_hours_per_day: 1
    account:
      members_required: true
    notes: ""
```

Output `exit` supports:

- `ge`: use the scenario's GE output price and seller tax.
- `high_alch`: convert the produced output to coins and subtract rune cost.
- `best_immediate`: compare GE net proceeds with High Alch net proceeds and use the better exit for that scenario.

For methods that alch their output, both values are exposed:

- `profitGpPerHourAlchTimeExcluded`
- `profitGpPerHourSequentialAlchIncluded`

The sequential figure charges 3 seconds per alched output, so a processing method cannot gain alch value without paying the extra workflow time.

## Execution scenarios

Every configured method is evaluated separately under:

```text
CURRENT_INSTANT
CURRENT_PATIENT_PROXY
HISTORICAL_INSTANT_6H
HISTORICAL_INSTANT_24H
HISTORICAL_INSTANT_7D
HISTORICAL_INSTANT_30D
```

### Current instant

Inputs use current observed `high`; outputs use current observed `low`. The scenario is invalid if a required current side is missing, stale beyond the configured acceptable threshold, or crossed.

### Current patient proxy

Inputs use current observed `low`; outputs use current observed `high`. It is always labelled:

```text
NOT_GUARANTEED_TO_FILL
```

### Historical instant proxy

Inputs use the selected window's high-side VWAP; outputs use low-side VWAP. This is a historical execution proxy, not a guarantee of a future fill.

## Grand Exchange tax

The engine implements the current seller-side model configured by the handoff:

```text
tax = min(floor(sell_price * 0.02), 5,000,000)
```

The tax is applied per sold item and only to GE sales. High Level Alchemy has no GE seller tax because the item becomes coins directly.

Tax exemptions are external configuration in `config/ge_tax_exemptions.json`, not hard-coded inside the tax function. The file contains the exemption names reviewed on 2026-08-28 and explicit bond ID `13190`. At runtime the canonical `/mapping` response resolves configured names to IDs. Any unresolved name is emitted into `health.json` instead of being silently ignored.

## High Level Alchemy

The engine uses:

```text
Magic level: 55
XP per cast: 65
Cast interval: 3 seconds
Maximum continuous rate: 1,200 casts/hour
Maximum Magic XP/hour: 78,000
```

Default configuration assumes a fire-providing staff, so one Nature rune is consumed per cast.

Set:

```yaml
alchemy:
  use_fire_staff: false
```

and the collector will also collect Fire rune market data and include five Fire runes per cast. `fire_rune_item_id` and `fire_runes_per_cast` are configurable.

Alchemy discovery uses two stages:

1. Bulk `/mapping` + `/latest` preliminary scan across the item universe.
2. Historical validation only for the top configured candidate count, using `5m` data for 24H and `1h` data for 7D.

This avoids fetching four time series for every item in the game.

Each final candidate includes profit/cast, ROI, mechanical profit/hour, 4-hour capacity, capital required when configured, Magic XP, buy-price age, 24H/7D volume, 24H VWAP/change and liquidity warnings.

The 4-hour item quantity is capped by:

```text
min(4800 casts, GE buy limit, capital limit when configured)
```

Historical volume is never treated as guaranteed available inventory.

## Liquidity warnings

The default planned-volume thresholds are:

```text
> 1% of observed 24h volume: NOTICE
> 5%: CAUTION
> 10%: HIGH_LIQUIDITY_RISK
```

These values are configurable in `config/settings.yaml`.

The method engine also reports mechanical cycles/hour separately from GE-buy-limit sustainable cycles/hour. It does not silently lower the configured production rate.

## Freshness and quality warnings

Default current-price thresholds:

```yaml
fresh_seconds: 1800
acceptable_seconds: 7200
very_stale_seconds: 86400
```

Possible warnings include:

```text
CURRENT_HIGH_STALE
CURRENT_LOW_STALE
CROSSED_CURRENT_PRICE
LOW_24H_VOLUME
SPARSE_24H_DATA
NO_HIGH_SIDE_TRADES
NO_LOW_SIDE_TRADES
MISSING_BUY_LIMIT
MISSING_HIGH_ALCH
HIGH_LIQUIDITY_RISK
```

The raw ages and coverage percentages are always exposed, so consumers do not have to rely solely on categorical labels.

## GitHub Actions and Pages

The included workflow runs:

- manually through `workflow_dispatch`
- hourly at minute 17

It uses concurrency cancellation so an older delayed run cannot race a newer run.

The build job:

1. checks out the repository
2. installs Python 3.12 and dependencies
3. runs `pytest`
4. collects current market data
5. validates generated JSON
6. uploads `site/` as a GitHub Pages artifact

The deploy job only runs if the build succeeds. Therefore a critical `/mapping`, `/latest` or generated-schema failure does not replace the previously deployed good dataset.

Repository Pages configuration must use:

```text
Settings -> Pages -> Build and deployment -> Source -> GitHub Actions
```

No OSRS or Jagex credentials are required.

## Failure behavior

The run fails without deployment when:

- `/mapping` cannot be fetched
- `/latest` cannot be fetched
- required generated JSON is missing or structurally invalid
- tracked items are structurally absent from the generated market output

Individual time-series failures are non-critical. The affected item/window is published with incomplete data, `health.json` becomes `degraded`, and the failure is recorded as a warning.

## Schema stability

Every published JSON file contains:

```json
{"schemaVersion": 1}
```

Breaking output changes require incrementing the schema version. This implementation is pinned to the OSRS Prices API v1 contract and does not mix v1 and v2 behavior.

## Scope limitations

This project deliberately does not provide:

- live GE order-book depth
- exact slippage prediction
- guaranteed patient-order fills
- automated in-game trading
- account or RuneLite integration
- credentials or game automation
- ML price prediction
- a database
- a full dashboard

Its purpose is reproducible market collection and auditable profitability calculations.
