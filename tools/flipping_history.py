from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any


DEFAULT_HORIZONS = (15, 30, 60)
DEFAULT_CALIBRATION_HORIZON = 60


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def finite(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def parse_horizons(value: str) -> tuple[int, ...]:
    horizons = sorted({int(part.strip()) for part in value.split(",") if part.strip()})
    if not horizons or any(horizon <= 0 for horizon in horizons):
        raise ValueError("horizons must contain positive comma-separated minute values")
    return tuple(horizons)


def snapshot(item: dict[str, Any], generated_at: int, rank: int) -> dict[str, Any]:
    expected = item.get("expected") or {}
    conservative = item.get("conservative") or {}
    stats = item.get("spreadStats") or {}
    drift = item.get("drift") or {}
    return {
        "generatedAt": generated_at,
        "itemId": int(item["itemId"]),
        "name": str(item.get("name") or item["itemId"]),
        "rank": rank,
        "currentMargin": finite(item.get("margin")),
        "expectedMargin": finite(expected.get("margin")),
        "conservativeMargin": finite(conservative.get("margin")),
        "expectedBuy": finite(expected.get("buyPrice")),
        "expectedSell": finite(expected.get("sellPrice")),
        "expectedOpportunity4h": finite(item.get("expectedOpportunity4h")),
        "capacityQuantity4h": finite(item.get("capacityQuantity4h")),
        "profitableBucketPct": finite(stats.get("profitableBucketPct")),
        "drift60mPct": finite(drift.get("drift60mPct")),
        "currentMidpoint": finite(drift.get("currentMidpoint")),
    }


def evaluate(
    old: dict[str, Any],
    current: dict[str, Any],
    current_rank: int,
    horizon_minutes: float,
    actual_horizon_minutes: float | None = None,
) -> dict[str, Any]:
    followup_margin = finite((current.get("expected") or {}).get("margin"))
    followup_current_margin = finite(current.get("margin"))
    predicted = finite(old.get("expectedMargin"))
    conservative = finite(old.get("conservativeMargin"))
    original_rank = int(old.get("rank") or current_rank)
    error = None if followup_margin is None or predicted is None else followup_margin - predicted
    old_midpoint = finite(old.get("currentMidpoint"))
    followup_midpoint = finite((current.get("drift") or {}).get("currentMidpoint"))
    midpoint_drift = None if old_midpoint is None or followup_midpoint is None else followup_midpoint - old_midpoint
    midpoint_drift_pct = None
    if midpoint_drift is not None and old_midpoint is not None and old_midpoint > 0:
        midpoint_drift_pct = midpoint_drift / old_midpoint * 100.0
    target_horizon = float(horizon_minutes)
    actual_horizon = target_horizon if actual_horizon_minutes is None else float(actual_horizon_minutes)
    return {
        "itemId": int(old["itemId"]),
        "name": str(old.get("name") or old["itemId"]),
        "snapshotGeneratedAt": int(old["generatedAt"]),
        "evaluatedAt": int(time.time()),
        "targetHorizonMinutes": target_horizon,
        "horizonMinutes": actual_horizon,
        "followupExpectedMargin": followup_margin,
        "followupCurrentMargin": followup_current_margin,
        "expectedMarginError": error,
        "absoluteExpectedMarginError": None if error is None else abs(error),
        "conservativeSurvived": None if followup_margin is None else conservative is None or followup_margin >= conservative,
        "marginSurvived": None if followup_margin is None else followup_margin > 0,
        "originalRank": original_rank,
        "followupRank": current_rank,
        "rankingStable": abs(current_rank - original_rank) <= 5,
        "midpointDrift": midpoint_drift,
        "midpointDriftPct": midpoint_drift_pct,
    }


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _rate(values: list[bool]) -> float | None:
    return sum(values) / len(values) if values else None


def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = [float(row["absoluteExpectedMarginError"]) for row in rows if row.get("absoluteExpectedMarginError") is not None]
    conservative = [bool(row["conservativeSurvived"]) for row in rows if row.get("conservativeSurvived") is not None]
    margins = [bool(row["marginSurvived"]) for row in rows if row.get("marginSurvived") is not None]
    rankings = [bool(row["rankingStable"]) for row in rows if row.get("rankingStable") is not None]
    drift = [abs(float(row["midpointDriftPct"])) for row in rows if row.get("midpointDriftPct") is not None]
    return {
        "sampleCount": len(rows),
        "meanAbsoluteExpectedMarginError": _mean(errors),
        "conservativeSurvivalRate": _rate(conservative),
        "marginSurvivalRate": _rate(margins),
        "rankingStabilityRate": _rate(rankings),
        "meanAbsoluteMidpointDriftPct": _mean(drift),
        "medianAbsoluteMidpointDriftPct": statistics.median(drift) if drift else None,
    }


def _row_horizon(row: dict[str, Any], fallback: int) -> int:
    value = row.get("targetHorizonMinutes")
    if value is None:
        value = row.get("horizonMinutes")
    if value is None:
        value = fallback
    return int(round(float(value)))


def summarise(
    rows: list[dict[str, Any]],
    minimum_calibration_samples: int,
    minimum_item_samples: int = 5,
    calibration_horizon_minutes: int = DEFAULT_CALIBRATION_HORIZON,
) -> dict[str, Any]:
    minimum_calibration_samples = max(1, int(minimum_calibration_samples))
    minimum_item_samples = max(1, int(minimum_item_samples))
    calibration_horizon_minutes = max(1, int(calibration_horizon_minutes))

    horizons = sorted({_row_horizon(row, calibration_horizon_minutes) for row in rows} | set(DEFAULT_HORIZONS))
    by_horizon: dict[str, Any] = {}
    for horizon in horizons:
        horizon_rows = [row for row in rows if _row_horizon(row, calibration_horizon_minutes) == horizon]
        by_horizon[str(horizon)] = _stats(horizon_rows)

    calibration_rows = [
        row for row in rows
        if _row_horizon(row, calibration_horizon_minutes) == calibration_horizon_minutes
    ]
    calibration_stats = _stats(calibration_rows)
    item_rows: dict[int, list[dict[str, Any]]] = {}
    for row in calibration_rows:
        item_id = int(row.get("itemId") or 0)
        if item_id > 0:
            item_rows.setdefault(item_id, []).append(row)

    item_calibration: dict[str, Any] = {}
    for item_id, grouped in sorted(item_rows.items()):
        stats = _stats(grouped)
        item_calibration[str(item_id)] = {
            **stats,
            "ready": stats["sampleCount"] >= minimum_item_samples,
        }

    return {
        "schemaVersion": 2,
        "generatedAt": int(time.time()),
        **calibration_stats,
        "totalBacktestCount": len(rows),
        "byHorizon": by_horizon,
        "calibrationHorizonMinutes": calibration_horizon_minutes,
        "calibrationReady": calibration_stats["sampleCount"] >= minimum_calibration_samples,
        "minimumCalibrationSamples": minimum_calibration_samples,
        "minimumItemSamples": minimum_item_samples,
        "itemCalibration": item_calibration,
    }


def _load_history(cache_path: Path, legacy_cache_path: Path | None) -> dict[str, Any]:
    if cache_path.exists():
        return read_json(cache_path, {})
    if legacy_cache_path is not None and legacy_cache_path.exists():
        return read_json(legacy_cache_path, {})
    return {"schemaVersion": 2, "snapshots": [], "backtests": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist and evaluate flipping recommendation snapshots")
    parser.add_argument("--public-flipping", default="build/public-site/data/flipping.json")
    parser.add_argument("--cache", default=".flipping-cache/flipping-history.json")
    parser.add_argument("--legacy-cache", default=None)
    parser.add_argument("--summary", default="build/internal-report/flipping-backtesting-summary.json")
    parser.add_argument("--horizons", default=",".join(str(value) for value in DEFAULT_HORIZONS))
    parser.add_argument("--calibration-horizon-minutes", type=int, default=DEFAULT_CALIBRATION_HORIZON)
    parser.add_argument("--minimum-calibration-samples", type=int, default=100)
    parser.add_argument("--minimum-item-samples", type=int, default=5)
    parser.add_argument("--maximum-horizon-lateness-minutes", type=float, default=20.0)
    parser.add_argument("--snapshot-interval-minutes", type=float, default=30.0)
    parser.add_argument("--snapshot-limit", type=int, default=50)
    parser.add_argument("--max-snapshots", type=int, default=20_000)
    args = parser.parse_args()

    horizons = parse_horizons(args.horizons)
    if args.calibration_horizon_minutes not in horizons:
        horizons = tuple(sorted(set(horizons) | {int(args.calibration_horizon_minutes)}))

    public = read_json(Path(args.public_flipping), {})
    items = [row for row in (public.get("items") or []) if (row.get("expected") or {}).get("margin") is not None]
    generated_at = int(public.get("generatedAt") or time.time())
    current_by_id = {int(row["itemId"]): (rank, row) for rank, row in enumerate(items, start=1)}

    cache_path = Path(args.cache)
    legacy_path = Path(args.legacy_cache) if args.legacy_cache else None
    history = _load_history(cache_path, legacy_path)
    snapshots = list(history.get("snapshots") or [])
    backtests = list(history.get("backtests") or [])
    already_evaluated = {
        (
            int(row.get("itemId") or 0),
            int(row.get("snapshotGeneratedAt") or 0),
            _row_horizon(row, int(args.calibration_horizon_minutes)),
        )
        for row in backtests
    }

    max_lateness = max(0.0, float(args.maximum_horizon_lateness_minutes))
    for old in snapshots:
        item_id = int(old.get("itemId") or 0)
        snapshot_at = int(old.get("generatedAt") or 0)
        if item_id not in current_by_id or snapshot_at <= 0:
            continue
        age_minutes = max(0.0, (generated_at - snapshot_at) / 60.0)
        rank, current = current_by_id[item_id]
        for horizon in horizons:
            key = (item_id, snapshot_at, horizon)
            if key in already_evaluated or age_minutes < horizon:
                continue
            if age_minutes > horizon + max_lateness:
                continue
            backtests.append(evaluate(old, current, rank, float(horizon), age_minutes))
            already_evaluated.add(key)

    interval_seconds = max(0.0, float(args.snapshot_interval_minutes)) * 60.0
    latest_snapshot_by_item: dict[int, int] = {}
    for row in snapshots:
        item_id = int(row.get("itemId") or 0)
        created = int(row.get("generatedAt") or 0)
        latest_snapshot_by_item[item_id] = max(created, latest_snapshot_by_item.get(item_id, 0))

    snapshot_limit = max(1, int(args.snapshot_limit))
    for rank, item in enumerate(items[:snapshot_limit], start=1):
        item_id = int(item["itemId"])
        previous = latest_snapshot_by_item.get(item_id, 0)
        if previous and generated_at - previous < interval_seconds:
            continue
        snapshots.append(snapshot(item, generated_at, rank))
        latest_snapshot_by_item[item_id] = generated_at

    max_rows = max(1, int(args.max_snapshots))
    snapshots = sorted(snapshots, key=lambda row: int(row.get("generatedAt") or 0))[-max_rows:]
    backtests = sorted(backtests, key=lambda row: int(row.get("evaluatedAt") or 0))[-max_rows:]
    summary = summarise(
        backtests,
        args.minimum_calibration_samples,
        args.minimum_item_samples,
        args.calibration_horizon_minutes,
    )
    write_json(cache_path, {"schemaVersion": 2, "snapshots": snapshots, "backtests": backtests, "summary": summary})
    write_json(Path(args.summary), {**summary, "recentBacktests": backtests[-100:]})
    print(
        "flipping history: "
        f"{len(snapshots)} snapshots, {len(backtests)} evaluated, "
        f"calibration_horizon={summary['calibrationHorizonMinutes']}m, "
        f"calibration_samples={summary['sampleCount']}, "
        f"calibration_ready={summary['calibrationReady']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
