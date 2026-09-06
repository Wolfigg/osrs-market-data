"""Short-term directional execution estimates from completed five-minute buckets."""
from __future__ import annotations

import math
from typing import Any

BUCKET_SECONDS = 300
MAX_AGE_SECONDS = 900
MIN_BUCKETS = 3


def execution_quote(record: dict[str, Any], side: str, required_per_hour: float, now: int) -> dict[str, Any]:
    if side not in {"high", "low"}:
        raise ValueError("execution side must be high or low")
    current = record.get("current") or {}
    points = {}
    for point in record.get("executionPoints") or []:
        timestamp = point.get("timestamp")
        price = point.get("avgHighPrice" if side == "high" else "avgLowPrice")
        volume = point.get(f"{side}PriceVolume")
        if (isinstance(timestamp, (int, float)) and now - 3600 <= timestamp <= now - BUCKET_SECONDS
                and isinstance(price, (int, float)) and math.isfinite(price) and price > 0
                and isinstance(volume, (int, float)) and math.isfinite(volume) and volume > 0):
            points[timestamp] = (float(price), float(volume), int(timestamp))
    samples = list(points.values())
    short = [p for p in samples if p[2] >= now - 1800]
    duration = 1800 if len(short) >= MIN_BUCKETS and sum(p[1] for p in short) * 2 >= required_per_hour else 3600
    selected = short if duration == 1800 else samples
    volume = sum(p[1] for p in selected)
    latest_bucket_end = max((p[2] + BUCKET_SECONDS for p in selected), default=None)
    age = now - latest_bucket_end if latest_bucket_end is not None else None
    status = "missing" if not selected else "stale" if age > MAX_AGE_SECONDS else "insufficient" if len(selected) < MIN_BUCKETS else "fresh"
    expected = conservative = vwap = None
    if status == "fresh":
        expected = sum(price * weight for price, weight, _ in selected) / volume
        vwap = expected
        target = volume * (0.9 if side == "high" else 0.1)
        cumulative = 0.0
        quantile = expected
        for price, weight, _ in sorted(selected):
            cumulative += weight
            if cumulative >= target:
                quantile = price
                break
        conservative = max(expected, quantile) if side == "high" else min(expected, quantile)
        # GE trades use whole GP; adverse rounding also preserves net-tax ordering.
        round_price = math.ceil if side == "high" else math.floor
        expected, conservative = round_price(expected), round_price(conservative)
    hourly_volume = volume * 3600 / duration
    return {
        "side": side, "latestObserved": current.get(side),
        "latestObservedAt": current.get(f"{side}Time"),
        "latestFreshness": current.get(f"{side}Freshness", "missing"),
        "directionalVwap": vwap, "expectedExecutable": expected, "conservative": conservative,
        "directionalVolume": volume, "directionalVolumePerHour": hourly_volume,
        "requiredPerHour": required_per_hour,
        "requiredSharePct": required_per_hour / hourly_volume * 100 if hourly_volume else None,
        "windowSeconds": duration, "windowStart": now - duration, "windowEnd": now,
        "latestBucketEnd": latest_bucket_end, "ageSeconds": age,
        "bucketCount": len(selected), "freshness": status, "calculatedAt": now,
    }
