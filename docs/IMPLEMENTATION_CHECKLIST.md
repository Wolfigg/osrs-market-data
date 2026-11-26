# OSRS Market Board - Completion Checklist

Updated: 2026-08-29

This checklist supersedes the obsolete V2 checklist that described the removed public Market Explorer and monolithic hourly publisher.

The public product has two tools:

1. Money Makers at `/`
2. High Alch at `/alchemy.html`

## Public product boundary

- [x] Money Makers is the homepage.
- [x] High Alch is the only secondary public tool.
- [x] High Alch is not an AFK method or AFK exit strategy.
- [x] Market Explorer is removed from the public product.
- [x] Ledger and About navigation are removed.
- [x] Public generation is restricted to `build/public-site`.
- [x] Maintainer diagnostics are restricted to `build/internal-report` and Actions artifacts.
- [x] Public-site validation rejects internal fields and forbidden paths.
- [x] Pages workflows upload exactly `build/public-site`.

Expected public artifact:

```text
index.html
alchemy.html
assets/app.css
assets/app.js
data/afk.json
data/alchemy.json
data/status.json
```

## Refresh architecture

- [x] `collect --mode live|short|long|full` exists.
- [x] Live refresh uses `/latest` and performs zero time-series requests.
- [x] Mapping is cached and refreshed by full/recovery collection.
- [x] 6H/24H use 5m data.
- [x] 7D uses 1h data.
- [x] 30D uses 6h data.
- [x] Derived history is persisted between runs.
- [x] Cache metadata records source, status, generated time and separate short/long timestamps.
- [x] Failed time-series fetches retain the previously valid derived window.
- [x] CI is separate from scheduled market collection.
- [x] Live workflow uses explicit ten-minute schedule slots (`7,17,27,37,47,57`).
- [x] Short history is scheduled hourly.
- [x] Long history is scheduled every six hours.
- [x] Full/mapping recovery is scheduled daily.
- [x] Shared `(item_id, timestep)` requests are deduplicated by `SeriesCollector`.
- [x] Obsolete per-item 24h time-series requests were removed from the public 30D-only product.

## Money-maker catalogue

- [x] Every enabled method has positive throughput and interaction interval.
- [x] Every enabled method has valid input/output quantities and item IDs, with an NPC shop sale allowed as the revenue path.
- [x] Every enabled method has an OSRS Wiki source.
- [x] Every enabled method has a verified audit marker.
- [x] Realistic and theoretical throughput are separate.
- [x] Method type is explicit/inferred from catalogue semantics, not frontend copy.
- [x] Category is skill/domain while method type is interaction pattern.
- [x] Reusable equipment is represented as requirements rather than consumed capital.
- [x] Fixed coin costs are included in public capital calculations.
- [x] GE buy-limit sustainable throughput is used for public profit/capital calculations.
- [x] Jewellery F2P/members access is corrected.
- [x] Onyx bolt tips produce 24 tips per onyx.
- [x] Battlestaff practical/theoretical rates are 2,450/2,625 per hour.
- [x] Cooking uses conservative 1,300/hour zero-burn modelling with Make-X timing.
- [x] Karambwan includes Tai Bwo Wannai Trio.
- [x] Camphor logging includes current Sailing/Troubled Tortugans access requirements.
- [x] Gathering equipment assumptions are published with the method.
- [x] Shop-hopping methods expose their method type and do not use the AFK classification.
- [x] NPC shop sale proceeds are shown separately from GE output proceeds and tax.

See `docs/AFK_METHOD_CATALOG_AUDIT.md` and `config/method_audit.yaml`.

## Money-maker ranking and confidence

- [x] Current, 24H, 7D and 30D GP/hour are retained separately.
- [x] Stability states are Stable, Watch, Volatile, Thin market, Stale and Unavailable.
- [x] Current-vs-history deviation metrics are calculated.
- [x] Historical reference spread is calculated.
- [x] Missing historical windows do not produce a Stable classification.
- [x] High liquidity pressure is surfaced as high market risk.
- [x] Recommended GP/hour uses explicit 50/30/20 historical weights.
- [x] Stable/Watch/Volatile/Thin-market behavior is deterministic and tested.
- [x] Stale/Unavailable recommendation is null.
- [x] Expected GP/hour is the default Money Makers ranking while Current remains visible/sortable.

## Money-maker filtering

- [x] Search.
- [x] Skill/category.
- [x] F2P/Members.
- [x] Profitable/all.
- [x] Interaction classification.
- [x] Bankstanding/Make-X/Autocast/Gathering/Shop hopping.
- [x] Stability state.
- [x] Strict-under capital filters.
- [x] Exact one-hour input-capital ceiling, shareable in the URL.
- [x] Summary rows show price stability beside market capacity.
- [x] Sort by Recommended, Current, 24H, 7D, 30D, GP/interaction, interval, capital and name.
- [x] Optional browser-local eligibility levels, without an account/profile concept.
- [x] Skill gate checks all published skill requirements.
- [x] Sailing is included in optional eligibility filtering for current content.
- [x] Quest and equipment requirements remain visible and are never inferred as completed.

## High Alch

- [x] Independent preliminary scanner over current `/mapping` + `/latest` data.
- [x] Nature rune cost is included.
- [x] Fire-rune cost is included when a fire staff is disabled.
- [x] Current profit/cast and 4H batch profit are exposed when the GE buy limit is known.
- [x] 24H, 7D and 30D profit/cast use matching historical item/rune windows.
- [x] Candidate history can be unavailable without blocking current scanning.
- [x] Capital filtering uses strict-under semantics.
- [x] Optional four-hour buy-list budget recalculates affordable quantity, capital and profit.
- [x] Market-risk label is visible in each High Alch summary row.
- [x] Missing GE buy limits leave four-hour quantity, batch profit and required capital unknown.
- [x] Unbudgeted totals are labelled maximum batch estimates and disclose the current-quote assumption.
- [x] Search, membership, profitability, minimum-profit and unavailable filters exist.
- [x] Current/24H/7D/30D and maximum batch-profit sorting exists.

## Freshness and reliability

- [x] Public status uses actual dataset timestamps rather than assumed cron timing.
- [x] Under 90 minutes is Current.
- [x] 90 minutes through exactly 2.5 hours is Delayed.
- [x] Older than 2.5 hours is Stale.
- [x] Exact local market-scan time and relative age are displayed in the browser.
- [x] Short- and long-history ages are displayed separately.
- [x] Individual stale/crossed observations invalidate unsafe current calculations.
- [x] A failed collector/build does not deploy a replacement Pages artifact.
- [x] A partial history failure does not erase previously valid cached history.

## Repository cleanup

- [x] README describes the current two-tool architecture.
- [x] Obsolete dashboard helpers are removed.
- [x] Obsolete legacy publisher and its tests are removed.
- [x] Old public dashboard/Market Explorer output contracts are removed.
- [x] Generated build/cache directories remain outside Git history.

## Automated acceptance

- [x] Unit tests cover price windows, tax, liquidity, methods, alchemy, cache and recommendations.
- [x] Catalogue tests enforce verified source provenance and corrected method mechanics.
- [x] Public leakage validation is tested.
- [x] Capital boundary behavior is tested.
- [x] Recommendation/stability boundaries are tested.
- [x] Chromium browser acceptance is part of CI.
- [x] Firefox browser acceptance is part of CI.
- [x] Responsive browser acceptance covers 360, 390, 768 and desktop widths.
- [x] Browser tests cover search, filters, URL restoration, local skill storage, details, unavailable rows and unknown-limit High Alch batches.
- [x] Browser tests verify the exactly-2.5-hour Delayed boundary.

## Explicit non-goals

These are not unfinished backlog items:

- public Market Explorer
- public raw market/API diagnostics
- account/authentication system
- RuneLite or Jagex account integration
- High Alch as an AFK exit strategy
- 6M/1Y public history while the simplified product does not expose it
- bulk `/5m`/`/1h` rolling-store replacement for per-item time series, which remains a future infrastructure optimization only if API scale requires it
