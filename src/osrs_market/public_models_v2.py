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


def _participation_fraction(fill_score: float | None) -> float:
    """Prudent share of observed directional market flow available to one user.

    100% of observed volume is never treated as personally executable depth.
    Thinner markets receive progressively smaller participation caps.
    """
    if fill_score is None:
        return 0.02
    score = float(fill_score)
    if score >= 90:
        return 0.25
    if score >= 75:
        return 0.15
    if score >= 55:
        return 0.10
    if score >= 35:
        return 0.05
    return 0.02


def _market_capacity(method: dict[str, Any]) -> dict[str, Any]:
    mechanics = method.get("mechanics") or {}
    mechanical = max(0.0, float(mechanics.get("cyclesPerHour") or 0.0))
    ge_limited = max(0.0, float(mechanics.get("cyclesPerHourByBuyLimits") or mechanical))
    fill_score_raw = (method.get("fillConfidence") or {}).get("score")
    fill_score = float(fill_score_raw) if fill_score_raw is not None else None
    participation = _participation_fraction(fill_score)

    raw_cycle_rates: list[float] = []
    for side in ("inputs", "outputs"):
        for row in (method.get("liquidity") or {}).get(side, []):
            directional = row.get("directionalVolume24h")
            units_per_hour = row.get("unitsPerHour")
            if directional is None or units_per_hour is None or mechanical <= 0:
                continue
            directional = max(0.0, float(directional))
            units_per_hour = max(0.0, float(units_per_hour))
            quantity_per_cycle = units_per_hour / mechanical if mechanical > 0 else 0.0
            if quantity_per_cycle <= 0:
                continue
            raw_cycle_rates.append((directional / 24.0) / quantity_per_cycle)

    raw_directional = min(raw_cycle_rates) if raw_cycle_rates else None
    if raw_directional is None:
        capacity = min(mechanical, ge_limited)
        basis = "No directional 24H volume available; mechanical/GE rate only."
    else:
        capacity = min(mechanical, ge_limited, raw_directional * participation)
        basis = (
            "Prudent executable capacity derived from the limiting 24H directional trade flow, "
            f"using a {participation * 100:.0f}% participation cap for this fill-confidence tier."
        )
    ratio = capacity / mechanical if mechanical > 0 else 0.0
    return {
        "cyclesPerHour": capacity,
        "rawDirectionalCyclesPerHour": raw_directional,
        "participationPct": participation * 100.0,
        "mechanicalRatioPct": ratio * 100.0,
        "basis": basis,
    }


def _apply_market_capacity(method: dict[str, Any]) -> None:
    capacity = _market_capacity(method)
    method["marketCapacity"] = capacity
    mechanical = max(0.0, float((method.get("mechanics") or {}).get("cyclesPerHour") or 0.0))
    ratio = capacity["cyclesPerHour"] / mechanical if mechanical > 0 else 0.0

    scenarios = method.get("scenarios") or {}
    raw_expected = scenarios.get("expectedGpPerHour")
    raw_conservative = scenarios.get("conservativeGpPerHour")
    raw_recommended = (method.get("recommended") or {}).get("gpPerHour")
    method.setdefault("economics", {})["unconstrainedExpectedGpPerHour"] = raw_expected
    method["economics"]["unconstrainedRecommendedGpPerHour"] = raw_recommended

    if raw_expected is not None:
        scenarios["expectedGpPerHour"] = float(raw_expected) * ratio
    if raw_conservative is not None:
        scenarios["conservativeGpPerHour"] = float(raw_conservative) * ratio
    if raw_recommended is not None:
        method.setdefault("recommended", {})["gpPerHour"] = float(raw_recommended) * ratio
    source = method.setdefault("priceSource", {})
    source["provider"] = "RuneScape Wiki real-time prices API (prices.runescape.wiki)"
    source["current"] = "Latest high/low trade observations from prices.runescape.wiki, using the required input/output direction and GE tax on outputs."
    source["liquidity"] = (
        "24H directional trade volume from prices.runescape.wiki is converted into a per-user capacity. "
        "Expected profit uses only a confidence-tier share of observed flow, never 100% of market volume."
    )


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
        _apply_market_capacity(method)

    ranking_scores = _ranking_scores(payload.get("methods", []))
    for method in payload.get("methods", []):
        method["rankingScores"] = ranking_scores.get(str(method["methodId"]), {})
    payload["rankingModes"] = sorted(RANKING_MODES)
    return payload
