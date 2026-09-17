---
status: done
---
# Flipping V3: evidence-gated calibration and ranking

## Next action

Merge PR #30 after the final documentation-only CI run is green. After merge, verify the first successful `Refresh flipping calibration` workflow saves `.flipping-cache/flipping-history.json` and that a later live build restores the resulting sample count. This is post-merge deployment verification; the workflow-run path cannot execute from the PR branch itself.

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
- Same-run calibration reapplication in the historical publish path, without a second market API fetch.

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
- The post-live calibration workflow is configured to update and save the dedicated calibration cache after a successful live publish; the historical workflow remains a persistence fallback.
- The historical publish path reapplies a newly computed summary to the current `flipping.json` before Pages upload, and snapshots the resulting published rank.
- Existing V2 history can seed the new cache, including legacy rows whose `horizonMinutes` stored actual observation age rather than a target horizon.
- The hidden page remains `noindex,nofollow` and absent from primary navigation.
- Python tests, hidden flipping JavaScript syntax check and browser acceptance pass for the PR revision.

## Results

Implemented on `feature/flipping-v3` in PR #30.

Tested code revision: `ba314dd801225a104cc34b815e25c4a2628705a2`.

Validation:
- GitHub Actions CI run `35257254968`: `229 passed` in the Python test job.
- Hidden flipping JavaScript syntax check: passed.
- Cooking backend/frontend parity check: passed.
- Deterministic browser fixture build: passed.
- Chromium and Firefox acceptance: passed.
- PR review threads covering V2 horizon migration, live-workflow cache ownership and historical same-run calibration were addressed and resolved.
- Changed-file review contains only the flipping model, history collector, three related workflows, hidden flipping UI, tests and this task note.

An earlier CI run correctly rejected cache persistence inside `refresh-live.yml`. The implementation was changed so `refresh-flipping-calibration.yml` owns post-live cache writes instead of weakening the live-workflow invariant. The live path intentionally applies newly matured calibration on the next live refresh; the hourly historical path applies its newly matured calibration in the same deployment.

Post-merge limitation: the new `workflow_run` path has not executed on the default branch yet. Its first run must be checked after merge before claiming deployment-level validation.
