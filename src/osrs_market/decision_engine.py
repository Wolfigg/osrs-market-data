from __future__ import annotations

from typing import Any

_INTENSITY_ORDER = {"very_low": 0, "low": 1, "moderate": 2, "high": 3, "very_high": 4}


def comparison_row(method: dict[str, Any]) -> dict[str, Any]:
    scenarios = method.get("scenarios") or {}
    economics = method.get("economics") or {}
    fill = method.get("fillConfidence") or {}
    sustainability = method.get("sustainability") or {}
    return {
        "methodId": method.get("methodId"),
        "name": method.get("name"),
        "expectedGpPerHour": scenarios.get("expectedGpPerHour"),
        "conservativeGpPerHour": scenarios.get("conservativeGpPerHour"),
        "capitalRequiredOneHour": economics.get("capitalOneHour"),
        "fillConfidence": fill.get("score"),
        "activeIntensity": (method.get("afk") or {}).get("intensity"),
        "afkIntervalSeconds": (method.get("afk") or {}).get("intervalSeconds"),
        "sustainability": sustainability.get("state"),
        "requirements": method.get("requirements") or {},
        "eligibility": method.get("eligibility"),
        "profitConfidence": (method.get("profitConfidence") or {}).get("score"),
    }


def compare_methods(methods: list[dict[str, Any]], method_ids: list[str] | None = None) -> list[dict[str, Any]]:
    selected = set(method_ids or [])
    rows = [comparison_row(method) for method in methods if not selected or str(method.get("methodId")) in selected]
    return sorted(rows, key=lambda row: row.get("expectedGpPerHour") if row.get("expectedGpPerHour") is not None else float("-inf"), reverse=True)


def _eligible_for_plan(method: dict[str, Any], bankroll: float, maximum_intensity: str | None) -> bool:
    if not (method.get("current") or {}).get("valid"):
        return False
    if (method.get("eligibility") or {}).get("blocked"):
        return False
    if maximum_intensity:
        actual = str((method.get("afk") or {}).get("intensity") or "low")
        if _INTENSITY_ORDER.get(actual, 1) > _INTENSITY_ORDER.get(maximum_intensity, 4):
            return False
    capital = float((method.get("economics") or {}).get("capitalOneHour") or 0)
    return capital <= bankroll or capital == 0


def optimise_session(methods: list[dict[str, Any]], *, bankroll: float, hours: float, maximum_intensity: str | None = None) -> dict[str, Any]:
    """Greedy Wave 6 planner using expected profit, GE turnover and buy-limit sustainability.

    This intentionally does not pretend to solve exact GE fill ordering. It creates
    deterministic blocks that can later be upgraded to stochastic optimisation.
    """
    bankroll = max(0.0, float(bankroll))
    remaining = max(0.0, float(hours))
    candidates = [method for method in methods if _eligible_for_plan(method, bankroll, maximum_intensity)]
    candidates.sort(key=lambda method: float((method.get("scenarios") or {}).get("expectedGpPerHour") or float("-inf")), reverse=True)
    blocks: list[dict[str, Any]] = []
    total_profit = 0.0
    capital = bankroll

    for method in candidates:
        if remaining <= 0:
            break
        expected_gp = (method.get("scenarios") or {}).get("expectedGpPerHour")
        if expected_gp is None or float(expected_gp) <= 0:
            continue
        economics = method.get("economics") or {}
        required = float(economics.get("capitalOneHour") or 0)
        fill = method.get("fillConfidence") or {}
        turnover = max(0.25, float(fill.get("turnoverHours") or 1.0))
        mechanics = method.get("mechanics") or {}
        mechanical = float(mechanics.get("cyclesPerHour") or 0)
        sustainable = float(mechanics.get("cyclesPerHourByBuyLimits") or mechanical)
        sustainable_ratio = min(1.0, sustainable / mechanical) if mechanical > 0 else 1.0
        bankroll_scale = min(1.0, capital / required) if required > 0 else 1.0
        effective_gp = float(expected_gp) * sustainable_ratio * bankroll_scale
        max_block = min(remaining, max(turnover, 0.25))
        profit = effective_gp * max_block
        blocks.append({
            "methodId": method.get("methodId"),
            "name": method.get("name"),
            "hours": round(max_block, 3),
            "expectedGpPerHour": round(effective_gp, 2),
            "expectedProfit": round(profit, 2),
            "capitalAllocated": round(min(required, capital), 2),
            "turnoverHours": turnover,
            "fillConfidence": fill.get("score"),
            "action": "run_then_reassess_market",
        })
        total_profit += profit
        capital += max(0.0, profit)
        remaining -= max_block

    # If the initial pass does not fill the session, keep using the best eligible
    # method in turnover-sized blocks so long sessions are represented explicitly.
    while remaining > 1e-9 and blocks:
        template = blocks[0]
        block_hours = min(remaining, max(0.25, float(template["turnoverHours"])))
        profit = float(template["expectedGpPerHour"]) * block_hours
        blocks.append({**template, "hours": round(block_hours, 3), "expectedProfit": round(profit, 2), "action": "repeat_after_market_refresh"})
        total_profit += profit
        remaining -= block_hours

    return {
        "schemaVersion": 1,
        "bankroll": bankroll,
        "requestedHours": max(0.0, float(hours)),
        "plannedHours": round(sum(float(block["hours"]) for block in blocks), 3),
        "expectedProfit": round(total_profit, 2),
        "endingBankrollEstimate": round(bankroll + total_profit, 2),
        "blocks": blocks,
        "policy": "Expected-profit greedy planner constrained by account eligibility, bankroll, GE sustainable throughput, fill-turnover proxy and activity intensity.",
    }
