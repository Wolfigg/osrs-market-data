from __future__ import annotations

import math
from typing import Any


def _num(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def build_afk_quality(method: dict[str, Any]) -> dict[str, Any]:
    """Score AFK quality independently of profitability.

    The score rewards uninterrupted idle time and penalises frequent banking or
    uncertain gathering cadence. Deterministic Make-X/autocast methods receive
    stronger timing confidence than stochastic gathering methods.
    """
    afk = method.get("afk") or {}
    model = method.get("model") or {}
    tags = {str(tag).lower() for tag in (method.get("tags") or [])}
    interval = max(0.0, _num(afk.get("intervalSeconds")))
    workflow = model.get("workflow") or {}
    bank_seconds = max(0.0, _num(workflow.get("bankSeconds")))
    process_seconds = max(0.0, _num(workflow.get("processSeconds")))

    # 0s => 0, 15s => 25, 45s => 50, 90s => 70, 180s => 85, 300s => 95.
    idle_score = _clamp(100.0 * (1.0 - math.exp(-interval / 95.0)))

    method_type = str(model.get("methodType") or "").lower()
    deterministic = bool(
        method_type in {"make-x", "autocast", "bankstanding"}
        or {"make-x", "autocast", "bankstanding"} & tags
    )
    gathering = bool(method_type == "gathering" or "gathering" in tags)
    timing_confidence = 95.0 if deterministic else 68.0 if gathering else 78.0

    total_cycle = bank_seconds + process_seconds
    bank_share = bank_seconds / total_cycle if total_cycle > 0 else 0.0
    banking_score = _clamp(100.0 * (1.0 - bank_share))

    # Interaction burden is a transparent approximation from the published
    # interval. It is intentionally not a click-count claim.
    interactions_per_hour = 3600.0 / interval if interval > 0 else None
    interaction_score = _clamp((interval / 120.0) * 100.0) if interval > 0 else 0.0

    score = (
        idle_score * 0.45
        + interaction_score * 0.25
        + banking_score * 0.15
        + timing_confidence * 0.15
    )
    score = round(_clamp(score), 1)
    if score >= 80:
        label = "Excellent AFK"
    elif score >= 65:
        label = "Very AFK"
    elif score >= 50:
        label = "AFK"
    elif score >= 35:
        label = "Semi-AFK"
    else:
        label = "Low interaction"

    return {
        "score": score,
        "label": label,
        "idleSeconds": interval,
        "estimatedInteractionsPerHour": round(interactions_per_hour, 1) if interactions_per_hour is not None else None,
        "timingConfidence": round(timing_confidence, 1),
        "bankingBurdenPct": round(bank_share * 100.0, 1),
        "deterministicTiming": deterministic,
        "estimatedCadence": gathering,
        "basis": (
            "AFK quality combines uninterrupted interval, estimated interaction frequency, banking burden and timing confidence. "
            "Gathering cadence is treated as estimated rather than guaranteed."
        ),
    }
