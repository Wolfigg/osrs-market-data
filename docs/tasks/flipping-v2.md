---
status: in-progress
---
# Flipping V2: execution-aware passive flip model

## Next action

Run repository CI for PR #28. If all required checks pass, review the final diff and merge.

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

Validation status:
- Local isolated Python syntax/model smoke check: passed before repository writes.
- Local `node --check` for the revised flipping client: passed before repository writes.
- Repository CI: queued for PR #28.
