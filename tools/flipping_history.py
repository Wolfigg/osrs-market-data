from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any


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
    }


def evaluate(old: dict[str, Any], current: dict[str, Any], current_rank: int, horizon_minutes: float) -> dict[str, Any]:
    followup_margin = finite((current.get("expected") or {}).get("margin"))
    predicted = finite(old.get("expectedMargin"))
    conservative = finite(old.get("conservativeMargin"))
    original_rank = int(old.get("rank") or current_rank)
    error = None if followup_margin is None or predicted is None else followup_margin - predicted
    return {
        "itemId": int(old["itemId"]),
        "name": str(old.get("name") or old["itemId"]),
        "snapshotGeneratedAt": int(old["generatedAt"]),
        "evaluatedAt": int(time.time()),
        "horizonMinutes": horizon_minutes,
        "followupExpectedMargin": followup_margin,
        "expectedMarginError": error,
        "absoluteExpectedMarginError": None if error is None else abs(error),
        "conservativeSurvived": None if followup_margin is None else conservative is None or followup_margin >= conservative,
        "marginSurvived": None if followup_margin is None else followup_margin > 0,
        "originalRank": original_rank,
        "followupRank": current_rank,
        "rankingStable": abs(current_rank - original_rank) <= 5,
    }


def summarise(rows: list[dict[str, Any]], minimum_calibration_samples: int) -> dict[str, Any]:
    errors = [float(row["absoluteExpectedMarginError"]) for row in rows if row.get("absoluteExpectedMarginError") is not None]
    conservative = [bool(row["conservativeSurvived"]) for row in rows if row.get("conservativeSurvived") is not None]
    margins = [bool(row["marginSurvived"]) for row in rows if row.get("marginSurvived") is not None]
    rankings = [bool(row["rankingStable"]) for row in rows if row.get("rankingStable") is not None]
    sample_count = len(rows)
    return {
        "schemaVersion": 1,
        "generatedAt": int(time.time()),
        "sampleCount": sample_count,
        "meanAbsoluteExpectedMarginError": sum(errors) / len(errors) if errors else None,
        "conservativeSurvivalRate": sum(conservative) / len(conservative) if conservative else None,
        "marginSurvivalRate": sum(margins) / len(margins) if margins else None,
        "rankingStabilityRate": sum(rankings) / len(rankings) if rankings else None,
        "calibrationReady": sample_count >= max(1, minimum_calibration_samples),
        "minimumCalibrationSamples": max(1, minimum_calibration_samples),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist and evaluate flipping recommendation snapshots")
    parser.add_argument("--public-flipping", default="build/public-site/data/flipping.json")
    parser.add_argument("--cache", default=".market-cache/flipping-history.json")
    parser.add_argument("--summary", default="build/internal-report/flipping-backtesting-summary.json")
    parser.add_argument("--minimum-horizon-minutes", type=float, default=60.0)
    parser.add_argument("--minimum-calibration-samples", type=int, default=100)
    parser.add_argument("--max-snapshots", type=int, default=5000)
    args = parser.parse_args()

    public = read_json(Path(args.public_flipping), {})
    items = [row for row in (public.get("items") or []) if (row.get("expected") or {}).get("margin") is not None]
    generated_at = int(public.get("generatedAt") or time.time())
    current_by_id = {int(row["itemId"]): (rank, row) for rank, row in enumerate(items, start=1)}

    history = read_json(Path(args.cache), {"schemaVersion": 1, "snapshots": [], "backtests": []})
    snapshots = list(history.get("snapshots") or [])
    backtests = list(history.get("backtests") or [])
    already_evaluated = {(int(row.get("itemId") or 0), int(row.get("snapshotGeneratedAt") or 0)) for row in backtests}

    for old in snapshots:
        key = (int(old.get("itemId") or 0), int(old.get("generatedAt") or 0))
        if key in already_evaluated or key[0] not in current_by_id:
            continue
        age_minutes = max(0.0, (generated_at - key[1]) / 60.0)
        if age_minutes < args.minimum_horizon_minutes:
            continue
        rank, current = current_by_id[key[0]]
        backtests.append(evaluate(old, current, rank, age_minutes))

    latest_keys = {(int(row.get("itemId") or 0), int(row.get("generatedAt") or 0)) for row in snapshots}
    for rank, item in enumerate(items, start=1):
        key = (int(item["itemId"]), generated_at)
        if key not in latest_keys:
            snapshots.append(snapshot(item, generated_at, rank))

    max_rows = max(1, args.max_snapshots)
    snapshots = sorted(snapshots, key=lambda row: int(row.get("generatedAt") or 0))[-max_rows:]
    backtests = sorted(backtests, key=lambda row: int(row.get("evaluatedAt") or 0))[-max_rows:]
    summary = summarise(backtests, args.minimum_calibration_samples)
    write_json(Path(args.cache), {"schemaVersion": 1, "snapshots": snapshots, "backtests": backtests, "summary": summary})
    write_json(Path(args.summary), {**summary, "recentBacktests": backtests[-100:]})
    print(f"flipping history: {len(snapshots)} snapshots, {len(backtests)} evaluated, calibration_ready={summary['calibrationReady']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
