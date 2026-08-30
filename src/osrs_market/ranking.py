from __future__ import annotations

from typing import Any


RANKING_MODES = {"best_profit", "best_afk", "best_low_capital", "best_stable", "best_overall"}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _method_score(method: dict[str, Any], mode: str) -> float:
    scenarios = method.get("scenarios") or {}
    expected = _num(scenarios.get("expectedGpPerHour"), float("-inf"))
    conservative = _num(scenarios.get("conservativeGpPerHour"), expected)
    capital = max(0.0, _num((method.get("economics") or {}).get("capitalOneHour")))
    afk_seconds = max(0.0, _num((method.get("afk") or {}).get("intervalSeconds")))
    fill = _num((method.get("fillConfidence") or {}).get("score"), 50.0)
    stability_state = str((method.get("stability") or {}).get("state") or "unknown")
    stability = {"stable": 100, "mostly_stable": 85, "mixed": 65, "volatile": 35, "unknown": 50}.get(stability_state, 50)
    confidence = _num((method.get("confidence") or {}).get("overall"), 70.0)
    sustainability_state = str((method.get("sustainability") or {}).get("state") or "unknown")
    sustainability = {"strong": 100, "moderate": 82, "watch": 68, "constrained": 50, "thin": 38, "limited": 25, "unknown": 50}.get(sustainability_state, 50)

    if mode == "best_profit":
        return expected
    if mode == "best_afk":
        return expected * 0.55 + conservative * 0.15 + afk_seconds * 1500 + fill * 250 + confidence * 250
    if mode == "best_low_capital":
        return expected * 0.45 + conservative * 0.25 + fill * 300 + confidence * 200 - capital * 0.08
    if mode == "best_stable":
        return conservative * 0.55 + expected * 0.15 + stability * 1200 + fill * 500 + confidence * 400
    if mode == "best_overall":
        return expected * 0.35 + conservative * 0.25 + fill * 450 + stability * 350 + sustainability * 350 + confidence * 450 + min(afk_seconds, 300) * 250 - capital * 0.015
    raise ValueError(f"unknown ranking mode: {mode}")


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
