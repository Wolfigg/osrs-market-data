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

    inventory_size = _num(workflow.get("inventorySize"), _num(workflow.get("inventoryCapacity")))
    items_per_inventory = _num(workflow.get("itemsPerInventory"), inventory_size)
    batch_size = items_per_inventory if items_per_inventory > 0 else None
    inventory_duration = process_seconds if process_seconds > 0 else (interval if deterministic else None)

    if gathering:
        cadence_type = "probabilistic_gathering"
    elif method_type == "autocast" or "autocast" in tags:
        cadence_type = "deterministic_autocast"
    elif deterministic:
        cadence_type = "deterministic_batch"
    else:
        cadence_type = "semi_continuous"

    cycles_per_hour = _num((method.get("mechanics") or {}).get("cyclesPerHour"))
    inventory_cycles_per_hour = cycles_per_hour / batch_size if cycles_per_hour > 0 and batch_size else None
    bank_interactions_per_hour = inventory_cycles_per_hour if bank_seconds > 0 and inventory_cycles_per_hour is not None else 0.0 if bank_seconds == 0 else None

    # Interaction burden remains an interaction-window estimate unless the
    # catalogue explicitly provides defensible click counts.
    interactions_per_hour = 3600.0 / interval if interval > 0 else None
    clicks_per_cycle_raw = workflow.get("estimatedClicksPerCycle")
    clicks_per_cycle = _num(clicks_per_cycle_raw) if clicks_per_cycle_raw is not None else None
    clicks_per_hour = clicks_per_cycle * cycles_per_hour if clicks_per_cycle is not None and cycles_per_hour > 0 else None
    interrupt_probability_raw = workflow.get("interruptProbability")
    interrupt_probability = _clamp(_num(interrupt_probability_raw), 0.0, 1.0) if interrupt_probability_raw is not None else None
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
        "cadenceType": cadence_type,
        "batchSize": round(batch_size, 2) if batch_size is not None else None,
        "inventoryDurationSeconds": round(inventory_duration, 1) if inventory_duration is not None else None,
        "bankInteractionsPerHour": round(bank_interactions_per_hour, 1) if bank_interactions_per_hour is not None else None,
        "estimatedClicksPerCycle": round(clicks_per_cycle, 2) if clicks_per_cycle is not None else None,
        "estimatedClicksPerHour": round(clicks_per_hour, 1) if clicks_per_hour is not None else None,
        "interruptProbability": interrupt_probability,
        "basis": (
            "AFK quality combines uninterrupted interval, estimated interaction frequency, banking burden and timing confidence. "
            "Gathering cadence is treated as estimated rather than guaranteed."
        ),
    }
