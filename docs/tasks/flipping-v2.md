---
status: done
---
# Flipping V2: execution-aware passive flip model

## Next action

Merge PR #28. After deployment, accumulate flipping backtest observations until the configured calibration sample gate is reached before applying learned ranking changes.

## Outcome and scope

Replace the hidden flipping desk's latest-spread opportunity proxy with an execution-aware passive-flip model while keeping the page unlisted.

Included:
- Current, Expected and Conservative passive-flip prices.
- Completed 5-minute execution evidence over a 30-60 minute window.
- Consistent hourly and four-hour market-capacity horizons.
- Capital-sized position planning in the browser.
- Spread survival and midpoint drift evidence.
- Snapshot persistence and matured-signal backtesting in the derived cache.

Excluded:
- Guaranteed fill predictions.
- Learned ranking changes before enough evaluated flipping snapshots exist.
- Public navigation to the flipping desk.

## Inputs

- `src/osrs_market/flipping.py`
- `src/osrs_market/execution.py`
- `src/osrs_market/flipping_site.py`
- `web/assets/flipping.js`
- `tools/recommendation_history.py` as the existing cache/backtesting pattern
- PR #26 as the original hidden flipping implementation

## Acceptance

- Expected passive buy/sell prices are calculated from completed 5-minute low/high trade evidence rather than a single latest trade.
- Conservative prices move against the flip relative to Expected.
- GE limit and observed flow use consistent hourly and four-hour quantities.
- Available GP reduces planned quantity instead of excluding an otherwise valid candidate.
- Spread survival and 30/60 minute midpoint drift are exposed.
- Historical workflow persists flipping snapshots and evaluates matured signals.
- Hidden page remains `noindex,nofollow` and absent from primary navigation.
- Repository Python tests, JavaScript syntax check and browser acceptance pass for the PR revision.

## Results

Implementation is on `feature/flipping-v2`, PR #28.

Validation:
- Local isolated Python syntax/model smoke check: passed before repository writes.
- Local `node --check` for the revised flipping client: passed before repository writes.
- Tested revision: `eb914ba3b66d5b06478ad4cea353fb39b1e0b98b`.
- GitHub Actions CI run `35246110215`: Python test job passed.
- GitHub Actions CI run `35246110215`: hidden flipping JavaScript syntax check passed.
- GitHub Actions CI run `35246110215`: deterministic browser fixture build passed.
- GitHub Actions CI run `35246110215`: Chromium and Firefox acceptance passed.
- Final diff review before this documentation update showed the branch 10 commits ahead of `master` with only the intended flipping model, site, workflow, config, tests, backtesting tool, and task note changed.
