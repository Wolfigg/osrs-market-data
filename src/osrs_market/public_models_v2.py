from __future__ import annotations

from typing import Any

from .afk_quality import build_afk_quality
from .anomaly_detection import detect_method_anomalies, publication_errors
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


def _participation_fraction(fill_score: float | None, stability_state: str = "unknown") -> float:
    """Prudent share of observed directional flow available to one user.

    Fill confidence sets the base participation ceiling. Price instability then
    reduces that ceiling because historic volume at unstable prices is weaker
    evidence of executable depth at the current margin.
    """
    if fill_score is None:
        base = 0.02
    else:
        score = float(fill_score)
        if score >= 90:
            base = 0.25
        elif score >= 75:
            base = 0.15
        elif score >= 55:
            base = 0.10
        elif score >= 35:
            base = 0.05
        else:
            base = 0.02
    modifier = {
        "stable": 1.0,
        "watch": 0.85,
        "volatile": 0.65,
        "thin_market": 0.50,
        "stale": 0.35,
        "unknown": 0.60,
    }.get(str(stability_state or "unknown"), 0.60)
    return max(0.01, base * modifier)


def _market_capacity(method: dict[str, Any]) -> dict[str, Any]:
    mechanics = method.get("mechanics") or {}
    mechanical = max(0.0, float(mechanics.get("cyclesPerHour") or 0.0))
    ge_limited = max(0.0, float(mechanics.get("cyclesPerHourByBuyLimits") or mechanical))
    fill_score_raw = (method.get("fillConfidence") or {}).get("score")
    fill_score = float(fill_score_raw) if fill_score_raw is not None else None
    stability_state = str((method.get("stability") or {}).get("state") or "unknown")
    participation = _participation_fraction(fill_score, stability_state)

    candidates: list[dict[str, Any]] = []
    for side in ("inputs", "outputs"):
        for row in (method.get("liquidity") or {}).get(side, []):
            units_per_hour = row.get("unitsPerHour")
            if units_per_hour is None or mechanical <= 0:
                continue
            units_per_hour = max(0.0, float(units_per_hour))
            quantity_per_cycle = units_per_hour / mechanical if mechanical > 0 else 0.0
            if quantity_per_cycle <= 0:
                continue
            horizons: list[dict[str, float]] = []
            for hours, field in ((1.0, "directionalVolume1h"), (6.0, "directionalVolume6h"), (24.0, "directionalVolume24h")):
                directional = row.get(field)
                if directional is None:
                    continue
                volume = max(0.0, float(directional))
                horizons.append({"hours": hours, "volume": volume, "cyclesPerHour": (volume / hours) / quantity_per_cycle})
            if not horizons:
                continue
            # A recent slowdown is relevant immediately, while an isolated
            # short-window spike is not enough to override the longer window.
            raw_cycles_per_hour = min(point["cyclesPerHour"] for point in horizons)
            short = min(horizons, key=lambda point: point["hours"])
            long = max(horizons, key=lambda point: point["hours"])
            acceleration = short["cyclesPerHour"] / long["cyclesPerHour"] if long["cyclesPerHour"] > 0 else None
            candidates.append({
                "name": row.get("name"),
                "side": side[:-1],
                "directionalVolume24h": row.get("directionalVolume24h"),
                "quantityPerCycle": quantity_per_cycle,
                "rawCyclesPerHour": raw_cycles_per_hour,
                "horizons": horizons,
                "volumeAccelerationRatio": acceleration,
            })

    limiting = min(candidates, key=lambda row: row["rawCyclesPerHour"]) if candidates else None
    raw_directional = limiting["rawCyclesPerHour"] if limiting else None
    if raw_directional is None:
        capacity = min(mechanical, ge_limited)
        basis = "No directional market volume is available; mechanical and GE limits are the only capacity evidence."
        evidence = "limited"
    else:
        capacity = min(mechanical, ge_limited, raw_directional * participation)
        evidence = "strong" if fill_score is not None and fill_score >= 75 and stability_state in {"stable", "watch"} else "moderate" if fill_score is not None and fill_score >= 55 else "weak"
        limiter_name = str(limiting.get("name") or "limiting item")
        limiter_side = str(limiting.get("side") or "market")
        basis = (
            f"{limiter_name} {limiter_side} flow is the limiting directional market signal. "
            f"Capacity uses {participation * 100:.1f}% of the weakest available short/long directional flow after fill-confidence and price-stability adjustment."
        )
    ratio = capacity / mechanical if mechanical > 0 else 0.0
    return {
        "cyclesPerHour": capacity,
        "mechanicalCyclesPerHour": mechanical,
        "marketSupportedCyclesPerHour": raw_directional,
        "expectedExecutableCyclesPerHour": capacity,
        "rawDirectionalCyclesPerHour": raw_directional,
        "participationPct": participation * 100.0,
        "mechanicalRatioPct": ratio * 100.0,
        "evidence": evidence,
        "limitingItem": limiting,
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
        "Available short-window and 24H directional trade volume from prices.runescape.wiki is converted into a per-user capacity. "
        "The participation ceiling is reduced when fill confidence or price stability is weak."
    )


def _ranking_scores(methods: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    scores: dict[str, dict[str, float]] = {str(method["methodId"]): {} for method in methods}
    for mode in sorted(RANKING_MODES):
        for row in rank_methods(methods, mode):
            scores[str(row["methodId"])][mode] = float((row.get("ranking") or {}).get("score") or 0.0)
    return scores


def build_public_afk(generated_at: int, afk_results: list[dict[str, Any]], anomaly_sink: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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
            variant_label = str(variant.get("label") or "").strip()
            if variant_label:
                method["name"] = f"{method['name']} - {variant_label}"
        method["confidence"] = _confidence_for(method, model)
        method["afkQuality"] = build_afk_quality(method)
        _apply_market_capacity(method)

    publishable: list[dict[str, Any]] = []
    for method in payload.get("methods", []):
        anomalies = detect_method_anomalies(method)
        if anomaly_sink is not None:
            anomaly_sink.extend(anomalies)
        warning_count = sum(row.get("severity") == "warning" for row in anomalies)
        if warning_count:
            confidence = method.get("confidence") or {}
            confidence["score"] = max(0.0, float(confidence.get("score") or 0.0) - 5.0 * warning_count)
        if not publication_errors(anomalies):
            publishable.append(method)
    payload["methods"] = publishable

    ranking_scores = _ranking_scores(payload.get("methods", []))
    for method in payload.get("methods", []):
        method["rankingScores"] = ranking_scores.get(str(method["methodId"]), {})
    payload["rankingModes"] = sorted(RANKING_MODES)
    return payload
