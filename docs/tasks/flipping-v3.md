---
status: in-progress
---
# Flipping V3: evidence-gated calibration and ranking

## Next action

Run repository CI and browser acceptance for the branch, fix any failures, then mark this task done only if the acceptance checks pass.

## Outcome and scope

Extend Flipping V2 with a calibration loop that observes how its signals behave after 15, 30 and 60 minutes, without treating market observations as guaranteed fills.

Included:
- 15, 30 and 60 minute follow-up backtests from live refreshes.
- Expected-margin error, positive-margin survival, conservative survival, ranking stability and midpoint drift diagnostics.
- A dedicated small calibration cache, with migration from the V2 history cache.
- Global and per-item 60-minute calibration summaries.
- Evidence-gated ranking: expected opportunity remains the ranking basis until the global sample gate passes. After that gate, the ranking score applies observed 60-minute positive-margin survival, using item history when its own sample gate passes and global history otherwise.
- Browser visibility into calibration state and the ranking inputs.

Excluded:
- Claims that observed Wiki volume equals the user's fill probability.
- Learned price targets or regression weights.
- Guaranteed profit or guaranteed fill estimates.
- Public navigation to the flipping desk.

## Inputs

- `src/osrs_market/flipping.py`
- `src/osrs_market/flipping_site.py`
- `tools/flipping_history.py`
- `web/flipping.html`
- `web/assets/flipping.js`
- `.github/workflows/refresh-live.yml`
- `.github/workflows/refresh-history.yml`
- `tests/test_hidden_flipping.py`
- `tests/test_flipping_history.py`
- [Flipping V2](flipping-v2.md)

## Acceptance

- History records separate 15, 30 and 60 minute evaluations and records actual evaluation age.
- Backtests expose expected-margin error, conservative survival, positive-margin survival, ranking stability and midpoint drift.
- Calibration readiness is gated on the configured 60-minute sample count.
- Per-item calibration is separately sample-gated.
- Before the calibration gate, ranking remains expected-opportunity ranking.
- After the gate, the ranking score applies empirical 60-minute margin survival, preferring item evidence when ready and otherwise using global evidence.
- Live and historical refresh workflows restore, update and save the dedicated calibration cache.
- Existing V2 history can seed the new cache.
- The hidden page remains `noindex,nofollow` and absent from primary navigation.
- Python tests, hidden flipping JavaScript syntax check and browser acceptance pass for the PR revision.

## Results

Implementation is in progress on `feature/flipping-v3`.

Validation: not run yet. GitHub Actions will be used for repository and browser checks after the branch diff is complete.
