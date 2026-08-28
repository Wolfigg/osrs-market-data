from __future__ import annotations

from typing import Any

from .models import LatestPrice


def freshness_label(age_seconds: int | None, freshness: dict[str, int]) -> str:
    if age_seconds is None:
        return "missing"
    if age_seconds <= int(freshness["fresh_seconds"]):
        return "fresh"
    if age_seconds <= int(freshness["acceptable_seconds"]):
        return "acceptable"
    if age_seconds <= int(freshness["very_stale_seconds"]):
        return "stale"
    return "very_stale"


def current_diagnostics(latest: LatestPrice, generated_at: int, freshness: dict[str, int]) -> dict[str, Any]:
    high_age = max(generated_at - latest.high_time, 0) if latest.high_time is not None else None
    low_age = max(generated_at - latest.low_time, 0) if latest.low_time is not None else None
    raw_spread = None
    raw_spread_pct = None
    crossed = False

    if latest.high is not None and latest.low is not None:
        raw_spread = latest.high - latest.low
        midpoint = (latest.high + latest.low) / 2.0
        raw_spread_pct = raw_spread / midpoint * 100.0 if midpoint else None
        crossed = latest.high < latest.low

    high_freshness = freshness_label(high_age, freshness)
    low_freshness = freshness_label(low_age, freshness)
    worst = _worst_freshness(high_freshness, low_freshness)

    return {
        "high": latest.high,
        "highTime": latest.high_time,
        "highAgeSeconds": high_age,
        "low": latest.low,
        "lowTime": latest.low_time,
        "lowAgeSeconds": low_age,
        "rawSpread": raw_spread,
        "rawSpreadPct": raw_spread_pct,
        "crossed": crossed,
        "highFreshness": high_freshness,
        "lowFreshness": low_freshness,
        "freshness": worst,
    }


def build_quality(
    current: dict[str, Any],
    windows: dict[str, dict[str, Any]],
    item_limit: int | None,
    highalch: int | None,
    settings: dict[str, Any],
) -> dict[str, Any]:
    warnings: list[str] = []
    acceptable = {"fresh", "acceptable"}

    if current["highFreshness"] not in acceptable:
        warnings.append("CURRENT_HIGH_STALE" if current["high"] is not None else "NO_HIGH_SIDE_TRADES")
    if current["lowFreshness"] not in acceptable:
        warnings.append("CURRENT_LOW_STALE" if current["low"] is not None else "NO_LOW_SIDE_TRADES")
    if current["crossed"]:
        warnings.append("CROSSED_CURRENT_PRICE")

    window_24h = windows.get("24h", {})
    volume_24h = int(window_24h.get("totalVolume") or 0)
    two_sided_coverage = float(window_24h.get("twoSidedCoveragePct") or 0.0)

    quality_settings = settings.get("quality", {})
    if volume_24h < int(quality_settings.get("low_24h_volume", 100)):
        warnings.append("LOW_24H_VOLUME")
    if two_sided_coverage < float(quality_settings.get("sparse_24h_two_sided_coverage_pct", 50.0)):
        warnings.append("SPARSE_24H_DATA")
    if int(window_24h.get("samplesWithHigh") or 0) == 0:
        warnings.append("NO_HIGH_SIDE_TRADES")
    if int(window_24h.get("samplesWithLow") or 0) == 0:
        warnings.append("NO_LOW_SIDE_TRADES")
    if item_limit is None:
        warnings.append("MISSING_BUY_LIMIT")
    if highalch is None:
        warnings.append("MISSING_HIGH_ALCH")

    warnings = list(dict.fromkeys(warnings))
    return {
        "currentHighFresh": current["highFreshness"] in acceptable,
        "currentLowFresh": current["lowFreshness"] in acceptable,
        "crossed": current["crossed"],
        "twoSidedCoveragePct24h": two_sided_coverage,
        "volume24h": volume_24h,
        "warnings": warnings,
    }


def scenario_current_valid(current: dict[str, Any], required_sides: tuple[str, ...]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    for side in required_sides:
        value = current.get(side)
        freshness = current.get(f"{side}Freshness")
        if value is None:
            warnings.append(f"CURRENT_{side.upper()}_MISSING")
        elif freshness not in {"fresh", "acceptable"}:
            warnings.append(f"CURRENT_{side.upper()}_STALE")
    if current.get("crossed"):
        warnings.append("CROSSED_CURRENT_PRICE")
    return not warnings, warnings


def liquidity_warnings(planned_share_pct: float | None, liquidity_settings: dict[str, Any]) -> list[str]:
    if planned_share_pct is None:
        return []
    if planned_share_pct > float(liquidity_settings.get("high_risk_market_share_pct", 10)):
        return ["HIGH_LIQUIDITY_RISK"]
    if planned_share_pct > float(liquidity_settings.get("caution_market_share_pct", 5)):
        return ["CAUTION"]
    if planned_share_pct > float(liquidity_settings.get("notice_market_share_pct", 1)):
        return ["NOTICE"]
    return []


def _worst_freshness(*labels: str) -> str:
    order = {"fresh": 0, "acceptable": 1, "stale": 2, "very_stale": 3, "missing": 4}
    return max(labels, key=lambda label: order[label])
