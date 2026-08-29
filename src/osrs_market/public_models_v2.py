from __future__ import annotations

from typing import Any

from .public_models import build_public_afk as build_public_afk_legacy
from .requirements import normalise_requirements
from .wave6 import confidence_components

_HISTORY_SCENARIOS = {
    "HISTORICAL_INSTANT_24H": "24h",
    "HISTORICAL_INSTANT_7D": "7d",
    "HISTORICAL_INSTANT_30D": "30d",
}


def _lower_bound_lookup(afk_results: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    lookup: dict[str, dict[str, float | None]] = {}
    for row in afk_results:
        econ = row.get("economics") or {}
        lookup.setdefault(str(row["methodId"]), {})[str(row["scenario"])] = econ.get("profitGpPerHourLowerBoundSustainable")
    return lookup


def _metadata_lookup(afk_results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in afk_results:
        method_id = str(row["methodId"])
        if method_id in result:
            continue
        result[method_id] = {
            "model": row.get("model"),
            "requirements": row.get("requirements"),
            "eligibility": row.get("eligibility"),
            "throughput": row.get("throughputDistribution"),
            "provenance": row.get("provenance"),
            "route": row.get("route"),
        }
    return result


def _throughput_confidence(distribution: dict[str, Any] | None) -> float | None:
    if not distribution or distribution.get("p50") in (None, 0):
        return None
    p10 = float(distribution.get("p10", distribution["p50"]))
    p90 = float(distribution.get("p90", distribution["p50"]))
    median = abs(float(distribution["p50"]))
    relative_span = max(0.0, (p90 - p10) / median)
    return round(max(35.0, min(98.0, 100.0 - relative_span * 55.0)), 1)


def _price_confidence(method: dict[str, Any]) -> float | None:
    state = str((method.get("stability") or {}).get("state") or "")
    return {"stable": 94.0, "watch": 80.0, "volatile": 62.0, "unavailable": None}.get(state, 75.0 if state else None)


def build_public_afk(generated_at: int, afk_results: list[dict[str, Any]]) -> dict[str, Any]:
    payload = build_public_afk_legacy(generated_at, afk_results)
    lower = _lower_bound_lookup(afk_results)
    metadata = _metadata_lookup(afk_results)

    for method in payload.get("methods", []):
        method_id = str(method["methodId"])
        meta = metadata.get(method_id) or {}
        model = meta.get("model") or {"probabilisticOutputs": False, "expectedValueUsed": False, "conservativeUsesLowerBound": False, "workflow": {}, "variant": None}
        method["model"] = model
        method["requirements"] = normalise_requirements(meta.get("requirements"))
        method["eligibility"] = meta.get("eligibility")
        method["throughput"] = meta.get("throughput")
        method["provenance"] = meta.get("provenance")
        method["route"] = meta.get("route")

        candidate_values: list[float] = []
        lower_current = (lower.get(method_id) or {}).get("CURRENT_INSTANT")
        if lower_current is not None:
            candidate_values.append(float(lower_current))
        for scenario in _HISTORY_SCENARIOS:
            value = (lower.get(method_id) or {}).get(scenario)
            if value is not None:
                candidate_values.append(float(value))
        if model.get("probabilisticOutputs") and candidate_values:
            method["scenarios"]["conservativeGpPerHour"] = min(candidate_values)
            method["priceSource"]["conservative"] = "Lowest available lower-bound Current, 24H, 7D or 30D profitability. Probabilistic outputs use their configured lower-bound expected quantity."
        if model.get("variant"):
            variant = model["variant"]
            method["baseMethodId"] = variant.get("baseMethodId")
            method["variant"] = {"id": variant.get("id"), "label": variant.get("label"), "description": variant.get("description")}

        fill = method.get("fillConfidence") or {}
        provenance = meta.get("provenance") or {}
        method["profitConfidence"] = confidence_components(
            price=_price_confidence(method),
            input_liquidity=fill.get("inputScore"),
            output_liquidity=fill.get("outputScore"),
            throughput=_throughput_confidence(meta.get("throughput")),
            model=provenance.get("score"),
        )
    return payload
