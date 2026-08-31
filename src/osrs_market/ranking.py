from __future__ import annotations

import math
from typing import Any


RANKING_MODES = {"best_profit", "best_afk", "best_low_capital", "best_stable", "best_overall"}
_UNAVAILABLE_SCORE = -1.0e30


def _num(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _method_score(method: dict[str, Any], mode: str) -> float:
    scenarios = method.get("scenarios") or {}
    expected = _num(scenarios.get("expectedGpPerHour"), _UNAVAILABLE_SCORE)
    conservative = _num(scenarios.get("conservativeGpPerHour"), expected)
    capital = max(0.0, _num((method.get("economics") or {}).get("capitalOneHour")))
    afk_seconds = max(0.0, _num((method.get("afk") or {}).get("intervalSeconds")))
    afk_quality = _num((method.get("afkQuality") or {}).get("score"), min(100.0, afk_seconds / 1.2))
    fill = _num((method.get("fillConfidence") or {}).get("score"), 50.0)
    stability_state = str((method.get("stability") or {}).get("state") or "unknown")
    stability = {"stable": 100, "watch": 78, "volatile": 45, "thin_market": 30, "stale": 20, "unknown": 50}.get(stability_state, 50)
    confidence = _num((method.get("confidence") or {}).get("overall"), 70.0)
    sustainability_state = str((method.get("sustainability") or {}).get("state") or "unknown")
    sustainability = {"strong": 100, "moderate": 82, "watch": 68, "constrained": 50, "thin": 38, "limited": 25, "unknown": 50}.get(sustainability_state, 50)
    market_evidence = {"strong": 100, "moderate": 75, "weak": 45, "limited": 30}.get(str((method.get("marketCapacity") or {}).get("evidence") or "limited"), 30)

    if expected <= _UNAVAILABLE_SCORE / 2:
        return _UNAVAILABLE_SCORE
    if mode == "best_profit":
        score = expected
    elif mode == "best_afk":
        score = expected * 0.35 + conservative * 0.15 + afk_quality * 3500 + fill * 250 + market_evidence * 250
    elif mode == "best_low_capital":
        score = expected * 0.40 + conservative * 0.25 + fill * 250 + confidence * 200 + market_evidence * 200 - capital * 0.08
    elif mode == "best_stable":
        score = conservative * 0.50 + expected * 0.15 + stability * 1400 + fill * 450 + market_evidence * 350 + confidence * 300
    elif mode == "best_overall":
        score = expected * 0.30 + conservative * 0.20 + afk_quality * 900 + fill * 350 + stability * 300 + sustainability * 300 + market_evidence * 350 + confidence * 350 - capital * 0.01
    else:
        raise ValueError(f"unknown ranking mode: {mode}")
    return score if math.isfinite(score) else _UNAVAILABLE_SCORE


def rank_methods(methods: list[dict[str, Any]], mode: str = "best_overall") -> list[dict[str, Any]]:
    if mode not in RANKING_MODES:
        raise ValueError(f"unknown ranking mode: {mode}")
    ranked = []
    for method in methods:
        row = dict(method)
        row["ranking"] = {"mode": mode, "score": _method_score(method, mode)}
        ranked.append(row)
    ranked.sort(key=lambda row: row["ranking"]["score"], reverse=True)
    return ranked
