---
status: done
---
# Flipping V3: evidence-gated calibration and ranking

## Next action

Merge PR #30 after the final documentation-only CI run is green. After merge, verify the first successful post-live calibration workflow writes `.flipping-cache/flipping-history.json` and that later live builds report the restored calibration sample count.

## Outcome and scope

Extend Flipping V2 with a calibration loop that observes how its signals behave after 15, 30 and 60 minutes, without treating market observations as guaranteed fills.

Included:
- 15, 30 and 60 minute follow-up backtests from deployed live flipping snapshots.
- Expected-margin error, positive-margin survival, conservative survival, ranking stability and midpoint drift diagnostics.
- A dedicated small calibration cache, with migration from the V2 history cache.
- Global and per-item 60-minute calibration summaries.
- Evidence-gated ranking: expected opportunity remains the ranking basis until the global sample gate passes. After that gate, the ranking score applies observed 60-minute positive-margin survival, using item history when its own sample gate passes and global history otherwise.
- Browser visibility into calibration state and the ranking inputs.
- A separate post-live calibration workflow so `refresh-live.yml` remains public-only and does not save caches.

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
- `.github/workflows/refresh-flipping-calibration.yml`
- `tests/test_hidden_flipping.py`
- `tests/test_flipping_history.py`
- `tests/test_workflows.py`
- [Flipping V2](flipping-v2.md)

## Acceptance

- History records separate 15, 30 and 60 minute evaluations and records actual evaluation age.
- Backtests expose expected-margin error, conservative survival, positive-margin survival, ranking stability and midpoint drift.
- Calibration readiness is gated on the configured 60-minute sample count.
- Per-item calibration is separately sample-gated.
- Before the calibration gate, ranking remains expected-opportunity ranking.
- After the gate, the ranking score applies empirical 60-minute margin survival, preferring item evidence when ready and otherwise using global evidence.
- Live refresh restores calibration for ranking but remains public-only and does not write caches.
- The post-live calibration workflow updates and saves the dedicated calibration cache after a successful live publish; the historical workflow remains a persistence fallback.
- Existing V2 history can seed the new cache, including legacy rows whose `horizonMinutes` stored actual observation age rather than a target horizon.
- The hidden page remains `noindex,nofollow` and absent from primary navigation.
- Python tests, hidden flipping JavaScript syntax check and browser acceptance pass for the PR revision.

## Results

Implemented on `feature/flipping-v3` in PR #30.

Tested code revision: `75ee6b67b5066122b14b07e9af6ccdaaa4341fc8`.

Validation:
- GitHub Actions CI run `35256649232`: `228 passed` in the Python test job.
- Hidden flipping JavaScript syntax check: passed.
- Cooking backend/frontend parity check: passed.
- Deterministic browser fixture build: passed.
- Chromium and Firefox acceptance: passed.
- Diff review against `master`: branch was 16 commits ahead, 0 behind, with only the intended flipping model, history, workflows, UI, tests and task note changed at the tested revision.

A preceding CI run correctly rejected cache persistence inside `refresh-live.yml`. The implementation was changed so a separate `refresh-flipping-calibration.yml` owns the post-live cache write instead of weakening the live-workflow invariant.
