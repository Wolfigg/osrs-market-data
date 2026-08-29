from __future__ import annotations

from typing import Any

from .recommendation import build_stability, recommended_gp_per_hour, weighted_reference

PUBLIC_SCHEMA_VERSION = 1

_HISTORY_SCENARIOS = {
    "HISTORICAL_INSTANT_6H": "6hGpPerHour",
    "HISTORICAL_INSTANT_24H": "24hGpPerHour",
    "HISTORICAL_INSTANT_7D": "7dGpPerHour",
    "HISTORICAL_INSTANT_30D": "30dGpPerHour",
}

_CATEGORY_LABELS = {
    "smithing": "Smithing",
    "fletching": "Fletching",
    "crafting": "Crafting",
    "cooking": "Cooking",
    "magic": "Magic",
    "fishing": "Fishing",
    "mining": "Mining",
    "woodcutting": "Woodcutting",
}


def _number(value: Any) -> float | None:
    return float(value) if value is not None else None


def _intish(value: Any) -> int | float | None:
    if value is None:
        return None
    number = float(value)
    return int(number) if number.is_integer() else number


def _category(value: Any) -> str:
    raw = str(value or "other").strip().lower()
    return _CATEGORY_LABELS.get(raw, raw.replace("_", " ").title() or "Other")


def classify_afk(interval_seconds: float | int | None) -> str:
    if interval_seconds is None:
        return "Unknown"
    seconds = float(interval_seconds)
    if seconds >= 180:
        return "Deep AFK"
    if seconds >= 90:
        return "Very AFK"
    if seconds >= 45:
        return "AFK"
    if seconds >= 30:
        return "Light AFK"
    return "Low interaction"


def public_risk(warnings: list[str] | None, valid: bool = True) -> dict[str, Any]:
    warnings = list(warnings or [])
    if not valid:
        return {"level": "unavailable", "label": "Unavailable", "reasons": ["Current calculation is not reliable enough to publish."]}
    reasons: list[str] = []
    level = "normal"
    joined = " ".join(warnings)
    if any(token in joined for token in ("STALE", "LOW_24H_VOLUME", "HIGH_RISK", "CROSSED")):
        level = "high"
    elif warnings:
        level = "watch"
    if "STALE" in joined:
        reasons.append("Price is older than usual, so current profit may not be representative.")
    if "LOW_24H_VOLUME" in joined or "HIGH_RISK" in joined:
        reasons.append("Thin market: planned volume is large relative to recent trading.")
    if "CROSSED" in joined:
        reasons.append("Current market observations disagree, so this entry needs caution.")
    if not reasons and warnings:
        reasons.append("Margin or liquidity deserves attention.")
    labels = {"normal": "Normal market risk", "watch": "Watch market conditions", "high": "High market risk", "unavailable": "Unavailable"}
    return {"level": level, "label": labels[level], "reasons": reasons}


def _requirements(result: dict[str, Any]) -> dict[str, Any]:
    raw = result.get("requirements") or {}
    skills: dict[str, int | float] = {}
    quests: list[str] = []
    equipment: list[str] = []
    for key, value in raw.items():
        lowered = str(key).lower()
        if lowered == "quests" and isinstance(value, list):
            quests = [str(x) for x in value]
        elif lowered == "equipment" and isinstance(value, list):
            equipment = [str(x) for x in value]
        elif lowered == "members":
            continue
        elif isinstance(value, (int, float)):
            skills[lowered] = _intish(value)  # type: ignore[assignment]
    return {"skills": skills, "quests": quests, "equipment": equipment}


def _members(result: dict[str, Any]) -> bool:
    requirements = result.get("requirements") or {}
    account = result.get("account") or {}
    if "members" in requirements:
        return bool(requirements["members"])
    if "members" in account:
        return bool(account["members"])
    return True


def _tags(result: dict[str, Any]) -> list[str]:
    tags = {_category(result.get("category")).lower()}
    description = str((result.get("afk") or {}).get("description") or "").lower()
    name = str(result.get("name") or "").lower()
    if "make-x" in description or "make x" in description:
        tags.add("make-x")
    if "bank" in description or "bolt tip" in name or "dart tip" in name:
        tags.add("bankstanding")
    if "autocast" in name or "auto-cast" in description:
        tags.add("autocast")
    if any(token in description for token in ("fish", "mine", "woodcut", "gather")):
        tags.add("gathering")
    tags.add("members" if _members(result) else "f2p")
    return sorted(tags)


def build_public_afk(generated_at: int, afk_results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for result in afk_results:
        grouped.setdefault(str(result["methodId"]), {})[str(result["scenario"])] = result

    methods: list[dict[str, Any]] = []
    for method_id, scenarios in grouped.items():
        current = scenarios.get("CURRENT_INSTANT")
        if current is None:
            continue
        economics = current.get("economics") or {}
        afk = current.get("afk") or {}
        mechanics = current.get("mechanics") or {}
        sustainable_cph = _number(mechanics.get("cyclesPerHourByBuyLimits")) or 0.0
        input_gp_per_cycle = _number(economics.get("inputGpPerCycle")) or 0.0
        capital_one_hour = input_gp_per_cycle * sustainable_cph
        capital_four_hours = input_gp_per_cycle * sustainable_cph * 4
        current_gp = _number(economics.get("profitGpPerHourBuyLimitSustainable"))
        valid = bool(current.get("valid")) and current_gp is not None

        history: dict[str, float | None] = {}
        for scenario, key in _HISTORY_SCENARIOS.items():
            hist = scenarios.get(scenario) or {}
            hist_econ = hist.get("economics") or {}
            history[key] = _number(hist_econ.get("profitGpPerHourBuyLimitSustainable")) if hist.get("valid") else None

        inputs = [{"name": str(row.get("name", "")), "quantity": _intish(row.get("quantity"))} for row in (current.get("inputs") or [])]
        outputs = [{"name": str(row.get("name", "")), "quantity": _intish(row.get("quantity"))} for row in (current.get("outputs") or [])]
        interval = _number(afk.get("intervalSeconds"))
        buy_limit_constrained = sustainable_cph + 1e-9 < (_number(mechanics.get("cyclesPerHour")) or 0.0)
        risk = public_risk(current.get("warnings"), valid=valid)
        stability = build_stability(current_gp, history, current.get("warnings"), valid)
        recommended = recommended_gp_per_hour(current_gp, history, stability["state"])
        reference = weighted_reference(history)

        methods.append({
            "methodId": method_id,
            "name": str(current.get("name", method_id)),
            "category": _category(current.get("category")),
            "tags": _tags(current),
            "members": _members(current),
            "requirements": _requirements(current),
            "current": {"valid": valid, "gpPerHour": current_gp if valid else None},
            "recommended": {"gpPerHour": recommended, "referenceGpPerHour": reference},
            "history": history,
            "stability": stability,
            "afk": {"classification": classify_afk(interval), "intervalSeconds": _intish(interval), "gpPerInteraction": _number(afk.get("gpPerInteractionWindow")) if valid else None, "description": str(afk.get("description") or "")},
            "economics": {"capitalOneHour": round(capital_one_hour) if inputs else 0, "capitalFourHours": round(capital_four_hours) if inputs else 0, "buyLimitConstrained": buy_limit_constrained},
            "risk": risk,
            "inputs": inputs,
            "outputs": outputs,
            "description": str(afk.get("description") or current.get("notes") or ""),
            "reference": current.get("reference"),
        })

    methods.sort(key=lambda row: row["recommended"]["gpPerHour"] if row["recommended"]["gpPerHour"] is not None else float("-inf"), reverse=True)
    return {"schemaVersion": PUBLIC_SCHEMA_VERSION, "generatedAt": generated_at, "methods": methods}


def _freshness(age_seconds: int | float | None) -> str:
    if age_seconds is None:
        return "Unknown"
    age = float(age_seconds)
    if age <= 1800:
        return "Fresh"
    if age <= 7200:
        return "Recent"
    if age <= 86400:
        return "Delayed"
    return "Stale"


def _history_profit(row: dict[str, Any], key: str) -> float | None:
    history = row.get(key) or {}
    return _number(history.get("profitPerCast")) if history.get("valid") else None


def build_public_alchemy(generated_at: int, candidates: list[dict[str, Any]], assumptions: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    use_fire_staff = bool(assumptions.get("useFireStaff", True))
    for row in candidates:
        current = row.get("currentInstant") or {}
        valid = bool(current.get("valid")) and current.get("profitPerCast") is not None
        rune_cost = _number(current.get("natureRunePrice")) or 0.0
        if not use_fire_staff:
            rune_cost += _number(current.get("fireRunePrice")) or 0.0
        history24 = _history_profit(row, "historicalInstant24h")
        history7 = _history_profit(row, "historicalInstant7d")
        history30 = _history_profit(row, "historicalInstant30d")
        risk = public_risk(row.get("warnings"), valid=valid)
        items.append({
            "itemId": int(row["itemId"]), "name": str(row.get("name", row["itemId"])), "members": bool(row.get("members", True)),
            "buyPrice": _intish(current.get("buyPrice")) if valid else None, "highAlchValue": _intish(row.get("highAlchValue")), "runeCost": _intish(rune_cost) if valid else None,
            "profitPerCast": _number(current.get("profitPerCast")) if valid else None, "roi": _number(current.get("roiPct")) if valid else None, "buyLimit": _intish(row.get("geBuyLimit")),
            "quantity4h": _intish((row.get("capacity4h") or {}).get("maxQuantity")) if valid else None, "profit4h": _number(row.get("profitPer4hGeLimit")) if valid else None,
            "capitalRequired": _number(row.get("capitalRequired")) if valid else None, "volume24h": _intish(row.get("volume24h")), "freshness": _freshness(row.get("buyPriceAgeSeconds")),
            "history": {"24hProfitPerCast": history24, "7dProfitPerCast": history7, "30dProfitPerCast": history30}, "history24hProfitPerCast": history24, "risk": risk,
        })
    items.sort(key=lambda row: row["profit4h"] if row["profit4h"] is not None else float("-inf"), reverse=True)
    return {"schemaVersion": PUBLIC_SCHEMA_VERSION, "generatedAt": generated_at, "assumptions": {"magicLevel": 55, "castsPerHour": int(assumptions.get("castsPerHour", 1200)), "natureRuneCost": next((item["runeCost"] for item in items if item["runeCost"] is not None), None), "fireStaff": use_fire_staff}, "items": items}


def build_public_status(generated_at: int, internal_health: dict[str, Any], short_history_generated_at: int | None = None, long_history_generated_at: int | None = None) -> dict[str, Any]:
    status = str(internal_health.get("status", "ok"))
    warnings = internal_health.get("warnings") or []
    api = internal_health.get("api") or {}
    failed = int(api.get("timeseriesFailed") or 0)
    if status == "ok" and not warnings and failed == 0:
        state = "current"
    elif failed > 0 or warnings:
        state = "delayed"
    else:
        state = "data_issue"
    return {"schemaVersion": PUBLIC_SCHEMA_VERSION, "generatedAt": generated_at, "liveGeneratedAt": generated_at, "shortHistoryGeneratedAt": short_history_generated_at, "longHistoryGeneratedAt": long_history_generated_at, "state": state, "ageSeconds": 0}
