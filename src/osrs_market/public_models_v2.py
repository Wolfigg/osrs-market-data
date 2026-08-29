from __future__ import annotations

from typing import Any

from .public_models import build_public_afk as build_public_afk_legacy

_HISTORY_SCENARIOS = {
    "HISTORICAL_INSTANT_24H": "24h",
    "HISTORICAL_INSTANT_7D": "7d",
    "HISTORICAL_INSTANT_30D": "30d",
}


def _lower_bound_lookup(afk_results: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    lookup: dict[str, dict[str, float | None]] = {}
    for row in afk_results:
        econ = row.get("economics") or {}
        lookup.setdefault(str(row["methodId"]), {})[str(row["scenario"])] = econ.get(
            "profitGpPerHourLowerBoundSustainable"
        )
    return lookup


def _model_lookup(afk_results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in afk_results:
        method_id = str(row["methodId"])
        if method_id not in result and row.get("model"):
            result[method_id] = row["model"]
    return result


def build_public_afk(generated_at: int, afk_results: list[dict[str, Any]]) -> dict[str, Any]:
    payload = build_public_afk_legacy(generated_at, afk_results)
    lower = _lower_bound_lookup(afk_results)
    models = _model_lookup(afk_results)

    for method in payload.get("methods", []):
        method_id = str(method["methodId"])
        model = models.get(method_id) or {
            "probabilisticOutputs": False,
            "expectedValueUsed": False,
            "conservativeUsesLowerBound": False,
            "workflow": {},
            "variant": None,
        }
        method["model"] = model
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
            method["priceSource"]["conservative"] = (
                "Lowest available lower-bound Current, 24H, 7D or 30D profitability. "
                "Probabilistic outputs use their configured lower-bound expected quantity."
            )
        if model.get("variant"):
            variant = model["variant"]
            method["baseMethodId"] = variant.get("baseMethodId")
            method["variant"] = {
                "id": variant.get("id"),
                "label": variant.get("label"),
                "description": variant.get("description"),
            }
    return payload
