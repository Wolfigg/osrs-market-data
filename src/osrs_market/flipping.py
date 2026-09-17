from __future__ import annotations

import math
import statistics
from typing import Any, Iterable

from .models import LatestPrice, MappingItem, TimeSeriesPoint
from .tax import ge_tax_per_item

BUCKET_SECONDS = 300
EXECUTION_WINDOW_SECONDS = 3600
SHORT_WINDOW_SECONDS = 1800
MAX_EXECUTION_AGE_SECONDS = 900
MIN_EXECUTION_BUCKETS = 3


def _number(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _age(timestamp: int | None, generated_at: int) -> int | None:
    if timestamp is None or timestamp <= 0:
        return None
    return max(0, generated_at - int(timestamp))


def _freshness(age_seconds: int | None, settings: dict[str, Any]) -> dict[str, str]:
    if age_seconds is None:
        return {"state": "unknown", "label": "Unknown"}
    fresh = int(settings["freshness"]["fresh_seconds"])
    acceptable = int(settings["freshness"]["acceptable_seconds"])
    very_stale = int(settings["freshness"]["very_stale_seconds"])
    if age_seconds <= fresh:
        return {"state": "fresh", "label": "Fresh"}
    if age_seconds <= acceptable:
        return {"state": "recent", "label": "Recent"}
    if age_seconds <= very_stale:
        return {"state": "stale", "label": "Stale"}
    return {"state": "very_stale", "label": "Very stale"}


def _margin(buy_price: float | None, sell_price: float | None, item_id: int, exempt_ids: set[int]) -> dict[str, float | int | None]:
    if buy_price is None or sell_price is None or buy_price <= 0 or sell_price <= 0:
        return {"tax": None, "netSell": None, "margin": None, "roi": None}
    sell_int = int(sell_price)
    tax = ge_tax_per_item(sell_int, item_id, exempt_ids)
    net_sell = sell_price - tax
    margin = net_sell - buy_price
    return {
        "tax": tax,
        "netSell": net_sell,
        "margin": margin,
        "roi": margin / buy_price * 100.0,
    }


def _window(row: dict[str, Any] | None, item_id: int, exempt_ids: set[int]) -> dict[str, float | int | None]:
    if not row:
        return {
            "buyPrice": None,
            "sellPrice": None,
            "tax": None,
            "netSell": None,
            "margin": None,
            "roi": None,
            "buyFlow": None,
            "sellFlow": None,
            "balancedFlow": None,
            "buySellRatio": None,
            "flowBalancePct": None,
        }
    buy_price = _number(row.get("avgLowPrice"))
    sell_price = _number(row.get("avgHighPrice"))
    economics = _margin(buy_price, sell_price, item_id, exempt_ids)
    buy_flow = _number(row.get("lowPriceVolume"))
    sell_flow = _number(row.get("highPriceVolume"))
    balanced = min(buy_flow, sell_flow) if buy_flow is not None and sell_flow is not None else None
    ratio = buy_flow / sell_flow if buy_flow is not None and sell_flow is not None and sell_flow > 0 else None
    balance = min(buy_flow, sell_flow) / max(buy_flow, sell_flow) * 100.0 if buy_flow and sell_flow else None
    return {
        "buyPrice": buy_price,
        "sellPrice": sell_price,
        **economics,
        "buyFlow": buy_flow,
        "sellFlow": sell_flow,
        "balancedFlow": balanced,
        "buySellRatio": ratio,
        "flowBalancePct": balance,
    }


def _point_dict(point: TimeSeriesPoint | dict[str, Any]) -> dict[str, Any]:
    if isinstance(point, TimeSeriesPoint):
        return point.to_api_dict()
    return dict(point)


def _completed_points(points: Iterable[TimeSeriesPoint | dict[str, Any]], generated_at: int) -> list[dict[str, Any]]:
    deduped: dict[int, dict[str, Any]] = {}
    for raw in points:
        point = _point_dict(raw)
        timestamp = point.get("timestamp")
        if not isinstance(timestamp, (int, float)):
            continue
        ts = int(timestamp)
        if generated_at - EXECUTION_WINDOW_SECONDS <= ts <= generated_at - BUCKET_SECONDS:
            deduped[ts] = point
    return [deduped[key] for key in sorted(deduped)]


def _weighted_average(samples: list[tuple[float, float]]) -> float | None:
    total = sum(weight for _, weight in samples if weight > 0)
    if total <= 0:
        return None
    return sum(value * weight for value, weight in samples if weight > 0) / total


def _weighted_quantile(samples: list[tuple[float, float]], quantile: float) -> float | None:
    cleaned = sorted((value, weight) for value, weight in samples if weight > 0)
    total = sum(weight for _, weight in cleaned)
    if not cleaned or total <= 0:
        return None
    target = total * min(max(float(quantile), 0.0), 1.0)
    cumulative = 0.0
    for value, weight in cleaned:
        cumulative += weight
        if cumulative >= target:
            return value
    return cleaned[-1][0]


def _quantile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = min(max(float(quantile), 0.0), 1.0) * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _samples(points: list[dict[str, Any]], price_key: str, volume_key: str) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for point in points:
        price = _number(point.get(price_key))
        volume = _number(point.get(volume_key))
        if price is not None and price > 0 and volume is not None and volume > 0:
            result.append((price, volume))
    return result


def _spread_statistics(points: list[dict[str, Any]], item_id: int, exempt_ids: set[int]) -> dict[str, Any]:
    margins: list[float] = []
    for point in points:
        economics = _margin(_number(point.get("avgLowPrice")), _number(point.get("avgHighPrice")), item_id, exempt_ids)
        if economics["margin"] is not None:
            margins.append(float(economics["margin"]))
    profitable = sum(value > 0 for value in margins)
    return {
        "bucketCount": len(margins),
        "profitableBucketCount": profitable,
        "profitableBucketPct": profitable / len(margins) * 100.0 if margins else None,
        "medianMargin": statistics.median(margins) if margins else None,
        "p10Margin": _quantile(margins, 0.10),
        "averageMargin": sum(margins) / len(margins) if margins else None,
        "minMargin": min(margins) if margins else None,
        "maxMargin": max(margins) if margins else None,
    }


def _midpoint_average(points: list[dict[str, Any]]) -> float | None:
    samples: list[tuple[float, float]] = []
    for point in points:
        high = _number(point.get("avgHighPrice"))
        low = _number(point.get("avgLowPrice"))
        high_volume = _number(point.get("highPriceVolume")) or 0.0
        low_volume = _number(point.get("lowPriceVolume")) or 0.0
        weight = high_volume + low_volume
        if high is not None and low is not None and high > 0 and low > 0 and weight > 0:
            samples.append(((high + low) / 2.0, weight))
    return _weighted_average(samples)


def _drift(points: list[dict[str, Any]], current_midpoint: float, generated_at: int) -> dict[str, float | None]:
    short = [point for point in points if int(point["timestamp"]) >= generated_at - SHORT_WINDOW_SECONDS]
    midpoint30 = _midpoint_average(short)
    midpoint60 = _midpoint_average(points)

    def measure(reference: float | None) -> tuple[float | None, float | None]:
        if reference is None or reference <= 0:
            return None, None
        delta = current_midpoint - reference
        return delta, delta / reference * 100.0

    drift30, drift30_pct = measure(midpoint30)
    drift60, drift60_pct = measure(midpoint60)
    return {
        "currentMidpoint": current_midpoint,
        "midpoint30m": midpoint30,
        "midpoint60m": midpoint60,
        "drift30m": drift30,
        "drift30mPct": drift30_pct,
        "drift60m": drift60,
        "drift60mPct": drift60_pct,
    }


def _execution_model(
    points: Iterable[TimeSeriesPoint | dict[str, Any]],
    *,
    generated_at: int,
    item_id: int,
    exempt_ids: set[int],
    current_buy: float,
    current_sell: float,
) -> dict[str, Any]:
    completed = _completed_points(points, generated_at)
    short = [point for point in completed if int(point["timestamp"]) >= generated_at - SHORT_WINDOW_SECONDS]
    short_low = _samples(short, "avgLowPrice", "lowPriceVolume")
    short_high = _samples(short, "avgHighPrice", "highPriceVolume")
    use_short = len(short) >= MIN_EXECUTION_BUCKETS and len(short_low) >= MIN_EXECUTION_BUCKETS and len(short_high) >= MIN_EXECUTION_BUCKETS
    selected = short if use_short else completed
    duration = SHORT_WINDOW_SECONDS if use_short else EXECUTION_WINDOW_SECONDS
    low_samples = _samples(selected, "avgLowPrice", "lowPriceVolume")
    high_samples = _samples(selected, "avgHighPrice", "highPriceVolume")
    latest_bucket_end = max((int(point["timestamp"]) + BUCKET_SECONDS for point in selected), default=None)
    age = generated_at - latest_bucket_end if latest_bucket_end is not None else None

    status = "missing"
    if selected:
        status = "stale" if age is not None and age > MAX_EXECUTION_AGE_SECONDS else "insufficient"
        if len(selected) >= MIN_EXECUTION_BUCKETS and len(low_samples) >= MIN_EXECUTION_BUCKETS and len(high_samples) >= MIN_EXECUTION_BUCKETS and status != "stale":
            status = "fresh"

    expected_buy = expected_sell = conservative_buy = conservative_sell = None
    if status == "fresh":
        low_vwap = _weighted_average(low_samples)
        high_vwap = _weighted_average(high_samples)
        low_p90 = _weighted_quantile(low_samples, 0.90)
        high_p10 = _weighted_quantile(high_samples, 0.10)
        if low_vwap is not None and high_vwap is not None and low_p90 is not None and high_p10 is not None:
            expected_buy = math.ceil(low_vwap)
            expected_sell = math.floor(high_vwap)
            conservative_buy = math.ceil(max(low_vwap, low_p90))
            conservative_sell = math.floor(min(high_vwap, high_p10))

    expected = _margin(expected_buy, expected_sell, item_id, exempt_ids)
    conservative = _margin(conservative_buy, conservative_sell, item_id, exempt_ids)
    low_volume = sum(weight for _, weight in low_samples)
    high_volume = sum(weight for _, weight in high_samples)
    buy_flow_per_hour = low_volume * 3600.0 / duration if duration > 0 else None
    sell_flow_per_hour = high_volume * 3600.0 / duration if duration > 0 else None
    market_flow_per_hour = min(buy_flow_per_hour, sell_flow_per_hour) if buy_flow_per_hour is not None and sell_flow_per_hour is not None else None
    current_midpoint = (current_buy + current_sell) / 2.0

    return {
        "freshness": status,
        "windowSeconds": duration,
        "bucketCount": len(selected),
        "latestBucketEnd": latest_bucket_end,
        "ageSeconds": age,
        "buyFlow": low_volume,
        "sellFlow": high_volume,
        "buyFlowPerHour": buy_flow_per_hour,
        "sellFlowPerHour": sell_flow_per_hour,
        "marketFlowPerHour": market_flow_per_hour,
        "expected": {"buyPrice": expected_buy, "sellPrice": expected_sell, **expected},
        "conservative": {"buyPrice": conservative_buy, "sellPrice": conservative_sell, **conservative},
        "spreadStats": _spread_statistics(completed, item_id, exempt_ids),
        "drift": _drift(completed, current_midpoint, generated_at),
    }


def _spread_state(current_margin: float | None, execution: dict[str, Any]) -> dict[str, str]:
    if current_margin is None or current_margin <= 0:
        return {"state": "negative", "label": "Not profitable"}
    stats = execution.get("spreadStats") or {}
    buckets = int(stats.get("bucketCount") or 0)
    profitable = int(stats.get("profitableBucketCount") or 0)
    if execution.get("freshness") == "fresh" and buckets >= MIN_EXECUTION_BUCKETS:
        if profitable == buckets:
            return {"state": "persistent", "label": "Persistent"}
        if profitable > 0:
            return {"state": "mixed", "label": "Mixed recent spread"}
        return {"state": "current_only", "label": "Current only"}
    return {"state": "current_only", "label": "Current only"}


def select_flipping_timeseries_candidates(
    generated_at: int,
    mapping: dict[int, MappingItem],
    latest: dict[int, LatestPrice],
    five_minute: dict[int, dict[str, Any]],
    one_hour: dict[int, dict[str, Any]],
    exempt_ids: set[int],
    settings: dict[str, Any],
) -> list[int]:
    limit = max(0, int((settings.get("flipping") or {}).get("candidate_timeseries_limit", 100)))
    candidates: list[tuple[tuple[int, float, float], int]] = []
    for item_id, item in mapping.items():
        quote = latest.get(item_id)
        if quote is None or not item.limit or item.limit <= 0 or not quote.low or not quote.high:
            continue
        current = _margin(float(quote.low), float(quote.high), item_id, exempt_ids)
        margin = _number(current.get("margin"))
        if margin is None or margin <= 0:
            continue
        high_age = _age(quote.high_time, generated_at)
        low_age = _age(quote.low_time, generated_at)
        quote_age = max(high_age, low_age) if high_age is not None and low_age is not None else None
        if _freshness(quote_age, settings)["state"] in {"stale", "very_stale", "unknown"}:
            continue
        avg5 = _window(five_minute.get(item_id), item_id, exempt_ids)
        avg1 = _window(one_hour.get(item_id), item_id, exempt_ids)
        bulk_supported = int((_number(avg5.get("margin")) or 0) > 0 and (_number(avg1.get("margin")) or 0) > 0)
        balanced = _number(avg1.get("balancedFlow")) or 0.0
        quantity4h = min(float(item.limit), balanced * 4.0) if balanced > 0 else 0.0
        opportunity = margin * quantity4h
        candidates.append(((bulk_supported, opportunity, margin), item_id))
    candidates.sort(key=lambda row: row[0], reverse=True)
    return [item_id for _, item_id in candidates[:limit]]


def build_public_flipping(
    generated_at: int,
    mapping: dict[int, MappingItem],
    latest: dict[int, LatestPrice],
    five_minute: dict[int, dict[str, Any]],
    one_hour: dict[int, dict[str, Any]],
    exempt_ids: set[int],
    settings: dict[str, Any],
    timeseries: dict[int, list[TimeSeriesPoint | dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    series = timeseries or {}
    items: list[dict[str, Any]] = []
    for item_id, item in mapping.items():
        quote = latest.get(item_id)
        buy_limit = item.limit
        if quote is None or not buy_limit or buy_limit <= 0 or not quote.low or not quote.high:
            continue

        buy_price = float(quote.low)
        sell_price = float(quote.high)
        current = _margin(buy_price, sell_price, item_id, exempt_ids)
        high_age = _age(quote.high_time, generated_at)
        low_age = _age(quote.low_time, generated_at)
        quote_age = max(high_age, low_age) if high_age is not None and low_age is not None else None
        avg5m = _window(five_minute.get(item_id), item_id, exempt_ids)
        avg1h = _window(one_hour.get(item_id), item_id, exempt_ids)
        execution = _execution_model(
            series.get(item_id, []), generated_at=generated_at, item_id=item_id, exempt_ids=exempt_ids,
            current_buy=buy_price, current_sell=sell_price,
        )
        spread = _spread_state(current["margin"], execution)

        market_flow_per_hour = _number(execution.get("marketFlowPerHour"))
        ge_limit_rate_per_hour = float(buy_limit) / 4.0
        capacity_per_hour = min(ge_limit_rate_per_hour, market_flow_per_hour) if market_flow_per_hour is not None else None
        quantity4h = min(float(buy_limit), market_flow_per_hour * 4.0) if market_flow_per_hour is not None else None
        expected = execution["expected"]
        conservative = execution["conservative"]
        expected_opportunity4h = expected["margin"] * quantity4h if expected["margin"] is not None and quantity4h is not None else None
        conservative_opportunity4h = conservative["margin"] * quantity4h if conservative["margin"] is not None and quantity4h is not None else None
        capacity_capital = expected["buyPrice"] * quantity4h if expected["buyPrice"] is not None and quantity4h is not None else None
        coverage4h = quantity4h / float(buy_limit) * 100.0 if quantity4h is not None else None

        items.append({
            "itemId": item_id,
            "name": item.name,
            "members": item.members,
            "buyLimit": buy_limit,
            "buyPrice": buy_price,
            "sellPrice": sell_price,
            "highTime": quote.high_time,
            "lowTime": quote.low_time,
            "highAge": high_age,
            "lowAge": low_age,
            "quoteAge": quote_age,
            "freshness": _freshness(quote_age, settings),
            **current,
            "avg5m": avg5m,
            "avg1h": avg1h,
            "executionFreshness": execution["freshness"],
            "executionWindowSeconds": execution["windowSeconds"],
            "executionBucketCount": execution["bucketCount"],
            "latestExecutionBucketEnd": execution["latestBucketEnd"],
            "executionAgeSeconds": execution["ageSeconds"],
            "expected": expected,
            "conservative": conservative,
            "spreadStats": execution["spreadStats"],
            "drift": execution["drift"],
            "spread": spread,
            "buyFlowPerHour": execution["buyFlowPerHour"],
            "sellFlowPerHour": execution["sellFlowPerHour"],
            "marketFlowPerHour": market_flow_per_hour,
            "geLimitRatePerHour": ge_limit_rate_per_hour,
            "capacityPerHour": capacity_per_hour,
            "capacityQuantity4h": quantity4h,
            "capacityCoverage4hPct": coverage4h,
            "capacityCapital": capacity_capital,
            "expectedOpportunity4h": expected_opportunity4h,
            "conservativeOpportunity4h": conservative_opportunity4h,
            "capitalAtLimit": buy_price * buy_limit,
            "limitProfit4h": current["margin"] * buy_limit if current["margin"] is not None else None,
        })

    items.sort(
        key=lambda row: (
            row["expectedOpportunity4h"] if row["expectedOpportunity4h"] is not None else float("-inf"),
            row["spreadStats"].get("profitableBucketPct") or 0.0,
        ),
        reverse=True,
    )
    return {
        "schemaVersion": 2,
        "generatedAt": generated_at,
        "source": "RuneScape Wiki real-time prices API (prices.runescape.wiki)",
        "items": items,
    }
