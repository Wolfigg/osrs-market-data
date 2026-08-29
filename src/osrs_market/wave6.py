from __future__ import annotations

from copy import deepcopy
from statistics import fmean
from typing import Any

from .requirements import evaluate_requirements, normalise_account_profile, normalise_requirements
from .route_engine import evaluate_route


def throughput_distribution(method: dict[str, Any]) -> dict[str, float]:
    raw = (method.get("throughput") or {}).get("quantiles") or {}
    configured = float(method.get("cycles_per_hour", 0) or 0)
    theoretical = float(method.get("theoretical_cycles_per_hour", configured) or configured)
    route = evaluate_route(method.get("route"))
    median = float(raw.get("p50", raw.get("median", route.get("itemsPerHour") if route else configured)) or configured)
    p10 = float(raw.get("p10", median * 0.82))
    p25 = float(raw.get("p25", median * 0.92))
    p75 = float(raw.get("p75", min(theoretical, median * 1.08)))
    p90 = float(raw.get("p90", min(theoretical, median * 1.15)))
    values = sorted((max(0.0, p10), max(0.0, p25), max(0.0, median), max(0.0, p75), max(0.0, p90)))
    return {"p10": values[0], "p25": values[1], "p50": values[2], "p75": values[3], "p90": values[4]}


def provenance_summary(method: dict[str, Any]) -> dict[str, Any]:
    explicit = method.get("provenance") or {}
    reference = method.get("reference")
    assumptions = explicit.get("assumptions") or []
    if not assumptions:
        assumptions = [{
            "key": "cycles_per_hour",
            "value": method.get("cycles_per_hour"),
            "unit": "cycles_per_hour",
            "source": "osrs_wiki" if reference else "catalogue",
            "sourceUrl": reference,
            "verifiedAt": (method.get("audit") or {}).get("verified_at"),
            "confidence": "medium",
            "kind": "wiki_documented_rate",
        }]
    confidences = {"high": 0.95, "medium": 0.8, "low": 0.6}
    score = fmean(confidences.get(str(row.get("confidence", "medium")).lower(), 0.7) for row in assumptions) if assumptions else 0.7
    return {"assumptions": assumptions, "score": round(score * 100, 1), "complete": all(row.get("sourceUrl") or row.get("source") == "player_configurable" for row in assumptions)}


def apply_account_profile(method: dict[str, Any], profile: dict[str, Any] | None) -> dict[str, Any]:
    result = deepcopy(method)
    account = normalise_account_profile(profile)
    result["requirements"] = normalise_requirements(result.get("requirements"))
    result["eligibility"] = evaluate_requirements(result["requirements"], account)

    cooking = ((result.get("model") or {}).get("cooking") or {})
    if cooking and account["skills"].get("cooking") is not None:
        cooking.setdefault("defaults", {})["level"] = account["skills"]["cooking"]

    options = profile or {}
    cooking_options = options.get("cooking") or {}
    if cooking and cooking_options:
        defaults = cooking.setdefault("defaults", {})
        for source_key, target_key in (("location", "location"), ("gauntlets", "gauntlets"), ("cookingCape", "cookingCape")):
            if source_key in cooking_options:
                defaults[target_key] = cooking_options[source_key]

    result["throughputDistribution"] = throughput_distribution(result)
    result["provenanceSummary"] = provenance_summary(result)
    route = evaluate_route(result.get("route"))
    if route:
        result["routeResult"] = route
    return result


def confidence_components(*, price: float | None, input_liquidity: float | None, output_liquidity: float | None, throughput: float | None, model: float | None) -> dict[str, Any]:
    components = {"price": price, "inputLiquidity": input_liquidity, "outputLiquidity": output_liquidity, "throughput": throughput, "model": model}
    available = [float(value) for value in components.values() if value is not None]
    if not available:
        return {"score": None, "components": components}
    weights = {"price": 0.25, "inputLiquidity": 0.2, "outputLiquidity": 0.2, "throughput": 0.2, "model": 0.15}
    total_weight = sum(weights[key] for key, value in components.items() if value is not None)
    score = sum(float(value) * weights[key] for key, value in components.items() if value is not None) / total_weight
    return {"score": round(max(0.0, min(100.0, score)), 1), "components": components}
