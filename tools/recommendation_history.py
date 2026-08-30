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


def price_map(method: dict[str, Any], side: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for row in method.get(side) or []:
        value = finite(row.get("gePrice") if row.get("gePrice") is not None else row.get("price"))
        if value is not None:
            result[str(row.get("itemId") or row.get("name"))] = value
    return result


def snapshot(method: dict[str, Any], generated_at: int, rank: int) -> dict[str, Any]:
    scenarios = method.get("scenarios") or {}
    return {
        "generatedAt": generated_at,
        "methodId": str(method["methodId"]),
        "rank": rank,
        "currentProfitGpPerHour": finite(scenarios.get("currentGpPerHour")),
        "expectedProfitGpPerHour": finite(scenarios.get("expectedGpPerHour")),
        "conservativeProfitGpPerHour": finite(scenarios.get("conservativeGpPerHour")),
        "buyPriceAssumption": price_map(method, "inputs"),
        "sellPriceAssumption": price_map(method, "outputs"),
        "liquidityScore": finite((method.get("fillConfidence") or {}).get("score")),
        "confidenceScore": finite((method.get("confidence") or {}).get("overall")),
    }


def evaluate(old: dict[str, Any], current: dict[str, Any], current_rank: int, horizon_hours: float) -> dict[str, Any]:
    realised = finite((current.get("scenarios") or {}).get("currentGpPerHour"))
    expected = finite(old.get("expectedProfitGpPerHour"))
    conservative = finite(old.get("conservativeProfitGpPerHour"))
    original_rank = int(old.get("rank") or current_rank)
    error = None if realised is None or expected is None else realised - expected
    return {
        "methodId": str(old["methodId"]),
        "snapshotGeneratedAt": int(old["generatedAt"]),
        "evaluatedAt": int(time.time()),
        "horizonHours": horizon_hours,
        "realisedProfitGpPerHour": realised,
        "forecastErrorGpPerHour": error,
        "absoluteForecastErrorGpPerHour": None if error is None else abs(error),
        "conservativeSurvived": None if realised is None else conservative is None or realised >= conservative,
        "marginSurvived": None if realised is None else realised > 0,
        "originalRank": original_rank,
        "realisedRank": current_rank,
        "rankingStable": abs(current_rank - original_rank) <= 2,
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = [float(row["absoluteForecastErrorGpPerHour"]) for row in rows if row.get("absoluteForecastErrorGpPerHour") is not None]
    conservative = [bool(row["conservativeSurvived"]) for row in rows if row.get("conservativeSurvived") is not None]
    margins = [bool(row["marginSurvived"]) for row in rows if row.get("marginSurvived") is not None]
    rankings = [bool(row["rankingStable"]) for row in rows if row.get("rankingStable") is not None]
    return {
        "schemaVersion": 1,
        "generatedAt": int(time.time()),
        "sampleCount": len(rows),
        "meanAbsoluteForecastErrorGpPerHour": sum(errors) / len(errors) if errors else None,
        "conservativeSurvivalRate": sum(conservative) / len(conservative) if conservative else None,
        "marginSurvivalRate": sum(margins) / len(margins) if margins else None,
        "rankingStabilityRate": sum(rankings) / len(rankings) if rankings else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-afk", default="build/public-site/data/afk.json")
    parser.add_argument("--cache", default=".market-cache/recommendation-history.json")
    parser.add_argument("--summary", default="build/internal-report/backtesting-summary.json")
    parser.add_argument("--minimum-horizon-hours", type=float, default=6.0)
    parser.add_argument("--max-snapshots", type=int, default=2500)
    args = parser.parse_args()

    public = read_json(Path(args.public_afk), {})
    methods = list(public.get("methods") or [])
    generated_at = int(public.get("generatedAt") or time.time())
    current_by_id = {str(row["methodId"]): (rank, row) for rank, row in enumerate(methods, start=1)}

    history = read_json(Path(args.cache), {"schemaVersion": 1, "snapshots": [], "backtests": []})
    snapshots = list(history.get("snapshots") or [])
    backtests = list(history.get("backtests") or [])
    already_evaluated = {(str(row.get("methodId")), int(row.get("snapshotGeneratedAt") or 0)) for row in backtests}

    for old in snapshots:
        key = (str(old.get("methodId")), int(old.get("generatedAt") or 0))
        if key in already_evaluated or key[0] not in current_by_id:
            continue
        age_hours = max(0.0, (generated_at - key[1]) / 3600)
        if age_hours < args.minimum_horizon_hours:
            continue
        rank, current = current_by_id[key[0]]
        backtests.append(evaluate(old, current, rank, age_hours))

    latest_keys = {(str(row.get("methodId")), int(row.get("generatedAt") or 0)) for row in snapshots}
    for rank, method in enumerate(methods, start=1):
        key = (str(method["methodId"]), generated_at)
        if key not in latest_keys:
            snapshots.append(snapshot(method, generated_at, rank))

    snapshots = sorted(snapshots, key=lambda row: int(row.get("generatedAt") or 0))[-max(1, args.max_snapshots):]
    backtests = sorted(backtests, key=lambda row: int(row.get("evaluatedAt") or 0))[-max(1, args.max_snapshots):]
    write_json(Path(args.cache), {"schemaVersion": 1, "snapshots": snapshots, "backtests": backtests})
    write_json(Path(args.summary), {**summarise(backtests), "recentBacktests": backtests[-100:]})
    print(f"recommendation history: {len(snapshots)} snapshots, {len(backtests)} evaluated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
