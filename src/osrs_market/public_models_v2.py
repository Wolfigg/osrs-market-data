from __future__ import annotations

from typing import Any

from .confidence import ConfidenceComponents, method_confidence
from .public_models import build_public_afk as build_public_afk_legacy
from .ranking import RANKING_MODES, rank_methods

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


def _confidence_for(method: dict[str, Any], model: dict[str, Any]) -> dict[str, object]:
    valid = bool((method.get("current") or {}).get("valid"))
    fill = (method.get("fillConfidence") or {}).get("score")
    fill_score = float(fill) if fill is not None else 50.0
    stability = str((method.get("stability") or {}).get("state") or "unknown")
    stability_score = {"stable": 95, "watch": 75, "volatile": 50, "thin_market": 40, "stale": 35, "unknown": 55}.get(stability, 55)
    probabilistic = bool(model.get("probabilisticOutputs"))
    source = method.get("priceSource") or {}
    generated = source.get("generatedAt")
    return method_confidence(ConfidenceComponents(
        mechanical=100.0 if valid else 65.0,
        price=95.0 if valid else 45.0,
        liquidity=fill_score,
        throughput=float(stability_score),
        output_model=88.0 if probabilistic else 96.0,
        source_freshness=95.0 if generated else 60.0,
    ))


def _ranking_scores(methods: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    scores: dict[str, dict[str, float]] = {str(method["methodId"]): {} for method in methods}
    for mode in sorted(RANKING_MODES):
        for row in rank_methods(methods, mode):
            scores[str(row["methodId"])][mode] = float((row.get("ranking") or {}).get("score") or 0.0)
    return scores


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
        method["confidence"] = _confidence_for(method, model)

    ranking_scores = _ranking_scores(payload.get("methods", []))
    for method in payload.get("methods", []):
        method["rankingScores"] = ranking_scores.get(str(method["methodId"]), {})
    payload["rankingModes"] = sorted(RANKING_MODES)
    return payload
