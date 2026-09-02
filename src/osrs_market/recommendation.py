from __future__ import annotations

from typing import Any

REFERENCE_WEIGHTS = {
    "6hGpPerHour": 0.25,
    "24hGpPerHour": 0.325,
    "7dGpPerHour": 0.195,
    "30dGpPerHour": 0.13,
    "6mGpPerHour": 0.10,
}
STABLE_DEVIATION_PCT = 15.0
VOLATILE_DEVIATION_PCT = 35.0
STABLE_REFERENCE_SPREAD_PCT = 15.0
VOLATILE_REFERENCE_SPREAD_PCT = 30.0
VOLATILE_UPSIDE_CAP_PCT = 15.0
THIN_MARKET_DISCOUNT = 0.80


def _number(value: Any) -> float | None:
    return float(value) if value is not None else None


def percentage_deviation(value: float | int | None, reference: float | int | None) -> float | None:
    value = _number(value)
    reference = _number(reference)
    if value is None or reference is None:
        return None
    if reference == 0:
        return 0.0 if value == 0 else None
    return (value - reference) / abs(reference) * 100.0


def weighted_reference(history: dict[str, Any]) -> float | None:
    weighted = 0.0
    total_weight = 0.0
    for key, weight in REFERENCE_WEIGHTS.items():
        value = _number(history.get(key))
        if value is None:
            continue
        weighted += value * weight
        total_weight += weight
    return weighted / total_weight if total_weight > 0 else None


def reference_spread_pct(history: dict[str, Any]) -> float | None:
    values = [_number(history.get(key)) for key in REFERENCE_WEIGHTS]
    available = [value for value in values if value is not None]
    if len(available) < 2:
        return None
    reference = weighted_reference(history)
    if reference in (None, 0):
        return None
    return (max(available) - min(available)) / abs(reference) * 100.0


def build_stability(
    current_gp_per_hour: float | int | None,
    history: dict[str, Any],
    warnings: list[str] | None,
    valid: bool,
) -> dict[str, Any]:
    warnings = list(warnings or [])
    joined = " ".join(warnings)
    current = _number(current_gp_per_hour)
    deviations = {
        "currentVs6hPct": percentage_deviation(current, history.get("6hGpPerHour")),
        "currentVs24hPct": percentage_deviation(current, history.get("24hGpPerHour")),
        "currentVs7dPct": percentage_deviation(current, history.get("7dGpPerHour")),
        "currentVs30dPct": percentage_deviation(current, history.get("30dGpPerHour")),
        "currentVs6mPct": percentage_deviation(current, history.get("6mGpPerHour")),
    }
    spread = reference_spread_pct(history)
    core_history_keys = ("24hGpPerHour", "7dGpPerHour", "30dGpPerHour")
    available_history = sum(history.get(key) is not None for key in core_history_keys)
    reasons: list[str] = []

    if "STALE" in joined:
        state = "stale"
        reasons.append("One or more current market observations are stale.")
    elif current is None or not valid:
        state = "unavailable"
        reasons.append("Current profitability is not reliable enough to recommend.")
    elif "HIGH_LIQUIDITY_RISK" in joined or "LOW_24H_VOLUME" in joined:
        state = "thin_market"
        reasons.append("Planned throughput is large relative to recent observed trading.")
    else:
        comparable = [abs(value) for value in deviations.values() if value is not None]
        max_deviation = max(comparable) if comparable else None
        if (max_deviation is not None and max_deviation >= VOLATILE_DEVIATION_PCT) or (
            spread is not None and spread >= VOLATILE_REFERENCE_SPREAD_PCT
        ):
            state = "volatile"
            reasons.append("Current profitability is materially different from historical references.")
        elif available_history < len(core_history_keys):
            state = "watch"
            reasons.append("Not all 6H, 24H, 7D, 30D and 6M historical references are available.")
        elif (max_deviation is not None and max_deviation >= STABLE_DEVIATION_PCT) or (
            spread is not None and spread >= STABLE_REFERENCE_SPREAD_PCT
        ) or warnings:
            state = "watch"
            reasons.append("Margin, liquidity or history deserves additional caution.")
        else:
            state = "stable"
            reasons.append("Current and historical profitability are closely aligned.")

    labels = {
        "stable": "Stable",
        "watch": "Watch",
        "volatile": "Volatile",
        "thin_market": "Thin market",
        "stale": "Stale",
        "unavailable": "Unavailable",
    }
    return {
        "state": state,
        "label": labels[state],
        **deviations,
        "referenceSpreadPct": spread,
        "reasons": reasons,
    }


def recommended_gp_per_hour(
    current_gp_per_hour: float | int | None,
    history: dict[str, Any],
    stability_state: str,
) -> float | None:
    current = _number(current_gp_per_hour)
    if current is None or stability_state in {"stale", "unavailable"}:
        return None
    reference = weighted_reference(history)
    if reference is None:
        return None

    if current < 0 or reference < 0:
        return min(current, reference)
    if stability_state == "stable":
        return current * 0.50 + reference * 0.50
    if stability_state == "watch":
        return current * 0.25 + reference * 0.75
    if stability_state == "volatile":
        return min(current, reference * (1.0 + VOLATILE_UPSIDE_CAP_PCT / 100.0))
    if stability_state == "thin_market":
        conservative = current * 0.25 + reference * 0.75
        return conservative * THIN_MARKET_DISCOUNT
    return None
