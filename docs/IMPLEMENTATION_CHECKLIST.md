# V2 implementation checklist

This checklist reflects the current product split: shared market core, AFK Money Makers, standalone High Alch, and Market Explorer.

## Shared market core

- [x] `/mapping` fetched and parsed.
- [x] `/latest` fetched in bulk.
- [x] Descriptive User-Agent required.
- [x] Tracked/configured items fetch 5m, 1h, 6h and 24h time series.
- [x] 6H, 24H, 7D, 30D, 6M and 1Y windows are reconstructed by timestamp.
- [x] High-side and low-side volume is preserved.
- [x] High-side and low-side VWAP is calculated.
- [x] Current observation ages and freshness labels are exposed.
- [x] Crossed observations are flagged without swapping values.
- [x] Null prices remain null.
- [x] GE tax uses 2% floor rounding, 5,000,000 gp per-item cap and external exemptions.
- [x] Liquidity warnings, market share, volatility, spread and data-quality diagnostics are exposed.

## AFK Money Makers

- [x] AFK profitability is a separate branch from High Alch.
- [x] High Alch cannot be configured as an AFK method exit.
- [x] AFK outputs are sold through the GE and seller tax is applied.
- [x] Current instant, current patient proxy, and 6H/24H/7D/30D historical instant scenarios are separate.
- [x] Mechanical and GE-buy-limit sustainable rates are exposed separately.
- [x] AFK interval is exposed.
- [x] Interaction windows/hour is exposed.
- [x] GP per interaction window is exposed.
- [x] Requirements, notes and source references are part of each configured method.
- [x] Initial catalog contains double-mould steel cannonballs, Mahogany Plank Make autocast and Camphor Plank Make autocast.
- [x] AFK rankings are published independently under `afk/`.

## High Alch

- [x] Standalone full-universe preliminary scan is implemented.
- [x] Historical validation is limited to the configured top candidate count.
- [x] Nature rune cost is included.
- [x] Fire staff assumption is configurable.
- [x] Fire rune cost is included automatically when a fire staff is disabled.
- [x] 1,200 casts/hour and 65 XP/cast are exposed.
- [x] GE item buy limits and optional capital constraints are calculated.
- [x] Current-price freshness and historical liquidity are included.
- [x] Alchemy has no dependency on the AFK method engine.
- [x] High Alch is not used as an exit for AFK methods.

## Publishing

- [x] Schema version 2 separates `market/`, `afk/` and `alchemy/` outputs.
- [x] `index.json` is the machine-readable discovery entry point.
- [x] `health.json` reports collection status.
- [x] `market/summary.json` powers Market Explorer consumers.
- [x] `afk/methods.json` contains complete AFK calculations.
- [x] `afk/rankings.json` contains compact sortable AFK results.
- [x] `alchemy/candidates.json` and `alchemy/rankings.json` contain standalone High Alch data.
- [x] `index.html` provides a simple human entry point to each branch.
- [x] Generated `site/` remains outside Git history.

## CI / deployment

- [x] Tests run before market collection.
- [x] Live Prices API collection has run successfully on GitHub-hosted runners.
- [x] Manual workflow trigger is available.
- [x] Push validation on `master` is available.
- [x] Hourly collection runs at minute 17.
- [x] Concurrency cancellation prevents stale runs racing newer runs.
- [x] Critical collection/build failures prevent deployment of a bad dataset.
- [x] GitHub Pages artifact deployment is configured.

## Live validation history

The first GitHub-hosted integration run confirmed that the application can reach the live OSRS Wiki Prices API. That run fetched 4,652 mapping items and 4,520 latest-price records, performed 208 time-series requests with zero time-series failures, and completed collection successfully. The initial deployment issue was repository Pages configuration rather than market-data or Python code.
