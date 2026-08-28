from __future__ import annotations

import math
import statistics
from typing import Any, Iterable

from .models import TimeSeriesPoint
from .windows import WindowSpec


def _weighted_average(pairs: Iterable[tuple[int | None, int]]) -> float | None:
    weighted_sum = 0
    volume_sum = 0
    for price, volume in pairs:
        if price is None or volume <= 0:
            continue
        weighted_sum += price * volume
        volume_sum += volume
    return weighted_sum / volume_sum if volume_sum else None


def _mid(point: TimeSeriesPoint) -> float | None:
    if point.avg_high_price is None or point.avg_low_price is None:
        return None
    return (point.avg_high_price + point.avg_low_price) / 2.0


def calculate_window_metrics(points: list[TimeSeriesPoint], spec: WindowSpec) -> dict[str, Any]:
    sample_count = len(points)
    expected_samples = max(round(spec.duration_seconds / spec.source_bucket_seconds), 1)
    high_values = [p.avg_high_price for p in points if p.avg_high_price is not None]
    low_values = [p.avg_low_price for p in points if p.avg_low_price is not None]
    high_volume = sum(p.high_price_volume for p in points)
    low_volume = sum(p.low_price_volume for p in points)

    mids = [(p.timestamp, _mid(p)) for p in points]
    valid_mids = [(timestamp, mid) for timestamp, mid in mids if mid is not None and mid > 0]
    start_mid = valid_mids[0][1] if valid_mids else None
    end_mid = valid_mids[-1][1] if valid_mids else None

    spreads: list[float] = []
    spread_pcts: list[float] = []
    for point in points:
        mid = _mid(point)
        if mid is None or mid == 0:
            continue
        spread = float(point.avg_high_price - point.avg_low_price)  # type: ignore[operator]
        spreads.append(spread)
        spread_pcts.append(spread / mid * 100.0)

    returns: list[float] = []
    for (_, previous), (_, current) in zip(valid_mids, valid_mids[1:]):
        if previous and current and previous > 0 and current > 0:
            returns.append(math.log(current / previous))

    change_absolute = None
    change_pct = None
    if start_mid is not None and end_mid is not None and start_mid != 0:
        change_absolute = end_mid - start_mid
        change_pct = (end_mid / start_mid - 1.0) * 100.0

    samples_with_high = len(high_values)
    samples_with_low = len(low_values)
    two_sided = len(valid_mids)

    return {
        "startTimestamp": points[0].timestamp if points else None,
        "endTimestamp": points[-1].timestamp if points else None,
        "sampleCount": sample_count,
        "samplesWithHigh": samples_with_high,
        "samplesWithLow": samples_with_low,
        "twoSidedSamples": two_sided,
        "highVolume": high_volume,
        "lowVolume": low_volume,
        "totalVolume": high_volume + low_volume,
        "highVwap": _weighted_average((p.avg_high_price, p.high_price_volume) for p in points),
        "lowVwap": _weighted_average((p.avg_low_price, p.low_price_volume) for p in points),
        "highMin": min(high_values) if high_values else None,
        "highMax": max(high_values) if high_values else None,
        "lowMin": min(low_values) if low_values else None,
        "lowMax": max(low_values) if low_values else None,
        "startMid": start_mid,
        "endMid": end_mid,
        "changeAbsolute": change_absolute,
        "changePct": change_pct,
        "medianSpread": statistics.median(spreads) if spreads else None,
        "medianSpreadPct": statistics.median(spread_pcts) if spread_pcts else None,
        "volatilityPct": statistics.pstdev(returns) * 100.0 if len(returns) >= 2 else None,
        "coveragePct": min(sample_count / expected_samples * 100.0, 100.0),
        "twoSidedCoveragePct": min(two_sided / expected_samples * 100.0, 100.0),
        "sourceTimestep": spec.source_timestep,
    }
