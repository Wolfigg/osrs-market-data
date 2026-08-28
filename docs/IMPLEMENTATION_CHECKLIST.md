# V1 implementation checklist

This checklist maps the supplied developer handoff acceptance criteria to the implementation.

- [x] `/mapping` fetched and parsed in `api.py`.
- [x] `/latest` fetched in bulk in `api.py`.
- [x] Descriptive User-Agent required. GitHub Actions derives the repository URL automatically.
- [x] Tracked items fetch 5m, 1h, 6h and 24h time series.
- [x] 6H, 24H, 7D, 30D, 6M and 1Y windows are sliced by timestamp.
- [x] High-side and low-side volume is preserved.
- [x] High-side and low-side VWAP is calculated.
- [x] Current high/low ages and freshness labels are exposed.
- [x] Crossed current prices are flagged without swapping values.
- [x] Null market prices remain null.
- [x] GE tax uses 2% floor rounding, 5,000,000 gp per-item cap and external exemptions.
- [x] Old school bond ID 13190 exemption is unit tested.
- [x] Current exemption configuration contains 48 canonical item variants reviewed 2026-08-28.
- [x] User-defined multi-input/multi-output processing methods are supported.
- [x] Current instant and patient-order-proxy scenarios are separate.
- [x] 6H, 24H, 7D and 30D historical instant-execution proxies are supported.
- [x] Liquidity warnings and planned market-share indicators are included.
- [x] High Level Alchemy full-universe preliminary scan is implemented.
- [x] Nature rune cost is included.
- [x] Fire staff assumption is configurable. Fire rune collection/cost is automatic when disabled.
- [x] 1,200 casts/hour and 65 XP/cast are exposed.
- [x] Alch item buy limit and optional capital limit are calculated.
- [x] GE and High Alch exits can be compared for produced outputs.
- [x] Sequential processing plus alching time is supported.
- [x] `index.json`, `health.json`, `market.json`, `alchemy.json`, `opportunities.json`, `methods.json` and tracked-item JSON are generated.
- [x] Generated JSON schemaVersion is validated before a successful run completes.
- [x] Tests cover windows, VWAP, tax, freshness, crossed prices, alchemy, methods and generated-site validation.
- [x] GitHub Pages artifact deployment is included.
- [x] Generated `site/` is excluded from Git history.
- [x] Manual workflow trigger is included.
- [x] Hourly workflow runs at minute 17.
- [x] Concurrency cancellation prevents stale runs racing newer runs.
- [x] Critical collection/test/build failure prevents the deploy job from replacing the last good Pages deployment.

## Validation performed in the implementation sandbox

- `pytest -q`: 45 tests passed.
- `python -m compileall -q src`: passed.
- Editable package install with existing local build dependencies: passed.
- `osrs-market --help`: passed.
- JSON and YAML configuration parse checks: passed.

A live Prices API collection could not be executed in the implementation sandbox because outbound DNS/network access is disabled there. The GitHub Actions workflow is designed to perform the real live integration run in GitHub's hosted runner environment.
