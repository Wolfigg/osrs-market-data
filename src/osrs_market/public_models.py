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
    "smithing": "Smithing", "fletching": "Fletching", "crafting": "Crafting",
    "cooking": "Cooking", "magic": "Magic", "fishing": "Fishing",
    "mining": "Mining", "woodcutting": "Woodcutting", "sailing": "Sailing",
    "herblore": "Herblore",
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
    skill = raw.rsplit("/", 1)[-1]
    return _CATEGORY_LABELS.get(skill, skill.replace("_", " ").title() or "Other")


def classify_afk(interval_seconds: float | int | None) -> str:
    if interval_seconds is None:
        return "Unknown"
    seconds = float(interval_seconds)
    if seconds >= 180: return "Deep AFK"
    if seconds >= 90: return "Very AFK"
    if seconds >= 45: return "AFK"
    if seconds >= 30: return "Light AFK"
    return "Low interaction"


def public_risk(warnings: list[str] | None, valid: bool = True) -> dict[str, Any]:
    warnings = list(warnings or [])
    if not valid:
        return {"level": "unavailable", "label": "Unavailable", "reasons": ["Current calculation is not reliable enough to publish."]}
    reasons: list[str] = []
    level = "normal"
    joined = " ".join(warnings)
    if any(token in joined for token in ("STALE", "LOW_24H_VOLUME", "HIGH_LIQUIDITY_RISK", "HIGH_RISK", "CROSSED")):
        level = "high"
    elif warnings:
        level = "watch"
    if "STALE" in joined:
        reasons.append("Price is older than usual, so current profit may not be representative.")
    if "LOW_24H_VOLUME" in joined or "HIGH_LIQUIDITY_RISK" in joined or "HIGH_RISK" in joined:
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
        if lowered == "quests" and isinstance(value, list): quests = [str(x) for x in value]
        elif lowered == "equipment" and isinstance(value, list): equipment = [str(x) for x in value]
        elif lowered == "members": continue
        elif not isinstance(value, bool) and isinstance(value, (int, float)): skills[lowered] = _intish(value)  # type: ignore[assignment]
    return {"skills": skills, "quests": quests, "equipment": equipment}


def _members(result: dict[str, Any]) -> bool:
    requirements = result.get("requirements") or {}
    account = result.get("account") or {}
    if "members" in requirements: return bool(requirements["members"])
    if "members" in account: return bool(account["members"])
    return True


def _tags(result: dict[str, Any]) -> list[str]:
    tags = {_category(result.get("category")).lower()}
    tags.update(str(value).lower() for value in (result.get("methodTypes") or []))
    tags.add("members" if _members(result) else "f2p")
    return sorted(tags)


def _public_inputs(current: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in current.get("inputs") or []:
        rows.append({
            "itemId": int(row.get("itemId")), "name": str(row.get("name", "")),
            "quantity": _intish(row.get("quantity")), "price": _number(row.get("price")),
            "subtotal": _number(row.get("subtotal")), "buyViaGe": bool(row.get("buyViaGe", True)),
            "geBuyLimit": _intish(row.get("geBuyLimit")),
            "maxCyclesPerHourByLimit": _number(row.get("maxCyclesPerHourByLimit")),
        })
    return rows


def _public_outputs(current: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in current.get("outputs") or []:
        rows.append({
            "itemId": int(row.get("itemId")), "name": str(row.get("name", "")),
            "quantity": _intish(row.get("quantity")), "gePrice": _number(row.get("gePrice")),
            "geTaxPerItem": _number(row.get("geTaxPerItem")), "geNetPerItem": _number(row.get("geNetPerItem")),
        })
    return rows


def _public_liquidity(current: dict[str, Any], mechanical_cph: float) -> dict[str, Any]:
    source = current.get("liquidity") or {}
    result: dict[str, Any] = {"inputs": [], "outputs": []}
    for side in ("inputs", "outputs"):
        for row in source.get(side) or []:
            item_id = int(row.get("itemId"))
            detail_source = current.get(side) or []
            detail = next((x for x in detail_source if int(x.get("itemId")) == item_id), {})
            quantity = _number(detail.get("quantity")) or 0.0
            total_volume = _number(row.get("observedVolume24h"))
            directional_key = "observedHighVolume24h" if side == "inputs" else "observedLowVolume24h"
            directional_volume = _number(row.get(directional_key))
            units_per_hour = quantity * mechanical_cph
            total_share = units_per_hour / total_volume * 100.0 if total_volume and total_volume > 0 else None
            directional_share = units_per_hour / directional_volume * 100.0 if directional_volume and directional_volume > 0 else None
            result[side].append({
                "itemId": item_id, "name": str(row.get("name", "")), "unitsPerHour": _intish(units_per_hour),
                "volume24h": _intish(total_volume), "oneHourSharePct24h": total_share,
                "directionalVolume24h": _intish(directional_volume),
                "directionalOneHourSharePct24h": directional_share,
            })
    return result


def _sustainability(mechanical_cph: float, sustainable_cph: float, liquidity: dict[str, Any]) -> dict[str, Any]:
    ratio = sustainable_cph / mechanical_cph if mechanical_cph > 0 else 0.0
    shares = [row.get("oneHourSharePct24h") for side in ("inputs", "outputs") for row in liquidity.get(side, [])]
    shares = [float(x) for x in shares if x is not None]
    max_share = max(shares, default=None)
    reasons: list[str] = []
    if ratio < 0.5:
        state, label = "limited", "GE limited"
        reasons.append("Grand Exchange buy limits cut sustainable throughput by more than half.")
    elif max_share is not None and max_share >= 10:
        state, label = "thin", "Thin market"
        reasons.append("One hour of mechanical throughput is at least 10% of recent 24H volume for a required item.")
    elif ratio < 0.85:
        state, label = "constrained", "Constrained"
        reasons.append("Grand Exchange buy limits materially reduce the mechanical rate.")
    elif max_share is not None and max_share >= 5:
        state, label = "watch", "Liquidity watch"
        reasons.append("One hour of throughput is at least 5% of recent 24H volume for a required item.")
    elif max_share is None:
        state, label = "unknown", "Liquidity unknown"
        reasons.append("Recent 24H volume is unavailable for at least one side of this method.")
    elif ratio < 0.95 or max_share >= 1:
        state, label = "moderate", "Moderate"
        reasons.append("Method is usable, but buy limits or recent market share deserve attention for longer sessions.")
    else:
        state, label = "strong", "Strong"
        reasons.append("Buy limits preserve at least 95% of mechanical throughput and one-hour market share is below 1%.")
    limiting = "ge_buy_limit" if ratio < 0.999 else ("market_liquidity" if max_share is not None and max_share >= 1 else "mechanics")
    return {
        "state": state, "label": label, "throughputRatioPct": ratio * 100.0,
        "maxOneHourSharePct24h": max_share, "limitingFactor": limiting, "reasons": reasons,
    }


def _pressure_score(share: float | None) -> float | None:
    if share is None: return None
    if share < 0.5: return 98.0
    if share < 1: return 92.0
    if share < 2: return 84.0
    if share < 5: return 70.0
    if share < 10: return 55.0
    if share < 25: return 35.0
    return 18.0


def _fill_confidence(mechanical_cph: float, sustainable_cph: float, liquidity: dict[str, Any]) -> dict[str, Any]:
    input_shares = [float(row["directionalOneHourSharePct24h"]) for row in liquidity.get("inputs", []) if row.get("directionalOneHourSharePct24h") is not None]
    output_shares = [float(row["directionalOneHourSharePct24h"]) for row in liquidity.get("outputs", []) if row.get("directionalOneHourSharePct24h") is not None]
    input_pressure = max(input_shares, default=None)
    output_pressure = max(output_shares, default=None)
    input_score = _pressure_score(input_pressure)
    output_score = _pressure_score(output_pressure)
    available = [score for score in (input_score, output_score) if score is not None]
    if not available:
        return {
            "state": "unknown", "label": "Unknown", "score": None, "inputScore": input_score, "outputScore": output_score,
            "maxDirectionalSharePct24h": None, "turnoverHours": 2.0,
            "reason": "Directional 24H trade volume is not available for the required market sides.",
        }
    score = min(available)
    throughput = sustainable_cph / mechanical_cph if mechanical_cph > 0 else 0.0
    score *= max(0.35, min(1.0, throughput))
    if score >= 90: state, label, turnover = "high", "High", 0.25
    elif score >= 75: state, label, turnover = "good", "Good", 0.5
    elif score >= 55: state, label, turnover = "fair", "Fair", 1.0
    elif score >= 35: state, label, turnover = "low", "Low", 2.0
    else: state, label, turnover = "very_low", "Very low", 4.0
    all_shares = input_shares + output_shares
    max_share = max(all_shares, default=None)
    return {
        "state": state, "label": label, "score": round(score, 1), "inputScore": input_score, "outputScore": output_score,
        "maxDirectionalSharePct24h": max_share, "turnoverHours": turnover,
        "reason": "Confidence uses the exact observed trade direction needed for inputs and outputs, plus GE buy-limit throughput. It is a proxy, not guaranteed order-book depth.",
    }


def _profit_scenarios(current_gp: float | None, expected_gp: float | None, history: dict[str, Any]) -> dict[str, float | None]:
    references = [current_gp, expected_gp, history.get("24hGpPerHour"), history.get("7dGpPerHour"), history.get("30dGpPerHour")]
    available = [float(value) for value in references if value is not None]
    conservative = min(available) if available else None
    return {
        "currentGpPerHour": current_gp,
        "expectedGpPerHour": expected_gp,
        "conservativeGpPerHour": conservative,
    }


def build_public_afk(generated_at: int, afk_results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for result in afk_results:
        grouped.setdefault(str(result["methodId"]), {})[str(result["scenario"])] = result

    methods: list[dict[str, Any]] = []
    for method_id, scenarios in grouped.items():
        current = scenarios.get("CURRENT_INSTANT")
        if current is None: continue
        economics = current.get("economics") or {}
        afk = current.get("afk") or {}
        mechanics = current.get("mechanics") or {}
        mechanical_cph = _number(mechanics.get("cyclesPerHour")) or 0.0
        sustainable_cph = _number(mechanics.get("cyclesPerHourByBuyLimits")) or 0.0
        capital_gp_per_cycle = _number(economics.get("totalCostGpPerCycle"))
        if capital_gp_per_cycle is None: capital_gp_per_cycle = _number(economics.get("inputGpPerCycle")) or 0.0
        capital_one_hour = capital_gp_per_cycle * sustainable_cph
        capital_four_hours = capital_gp_per_cycle * sustainable_cph * 4
        current_gp = _number(economics.get("profitGpPerHourBuyLimitSustainable"))
        valid = bool(current.get("valid")) and current_gp is not None

        history: dict[str, float | None] = {}
        for scenario, key in _HISTORY_SCENARIOS.items():
            hist = scenarios.get(scenario) or {}
            hist_econ = hist.get("economics") or {}
            history[key] = _number(hist_econ.get("profitGpPerHourBuyLimitSustainable")) if hist.get("valid") else None

        inputs = _public_inputs(current)
        outputs = _public_outputs(current)
        interval = _number(afk.get("intervalSeconds"))
        buy_limit_constrained = sustainable_cph + 1e-9 < mechanical_cph
        risk = public_risk(current.get("warnings"), valid=valid)
        stability = build_stability(current_gp, history, current.get("warnings"), valid)
        expected = recommended_gp_per_hour(current_gp, history, stability["state"])
        reference = weighted_reference(history)
        liquidity = _public_liquidity(current, mechanical_cph)
        sustainability = _sustainability(mechanical_cph, sustainable_cph, liquidity)
        fill_confidence = _fill_confidence(mechanical_cph, sustainable_cph, liquidity)
        profit_scenarios = _profit_scenarios(current_gp if valid else None, expected, history)

        methods.append({
            "methodId": method_id, "name": str(current.get("name", method_id)),
            "category": _category(current.get("category")), "tags": _tags(current), "members": _members(current),
            "requirements": _requirements(current),
            "current": {"valid": valid, "gpPerHour": current_gp if valid else None},
            "recommended": {"gpPerHour": expected, "referenceGpPerHour": reference},
            "scenarios": profit_scenarios,
            "history": history, "stability": stability, "sustainability": sustainability, "fillConfidence": fill_confidence,
            "afk": {"classification": classify_afk(interval), "intervalSeconds": _intish(interval), "gpPerInteraction": _number(afk.get("gpPerInteractionWindow")) if valid else None, "description": str(afk.get("description") or "")},
            "mechanics": {"cyclesPerHour": mechanical_cph, "cyclesPerHourByBuyLimits": sustainable_cph},
            "economics": {
                "capitalPerCycle": capital_gp_per_cycle, "capitalOneHour": round(capital_one_hour), "capitalFourHours": round(capital_four_hours),
                "buyLimitConstrained": buy_limit_constrained, "profitPerCycle": _number(economics.get("profitGpPerCycle")) if valid else None,
                "inputGpPerCycle": _number(economics.get("inputGpPerCycle")), "fixedCostGpPerCycle": _number(economics.get("fixedCostGpPerCycle")),
                "outputGrossGpPerCycle": _number(economics.get("outputGrossGeGpPerCycle")), "geTaxGpPerCycle": _number(economics.get("geTaxGpPerCycle")),
                "outputNetGpPerCycle": _number(economics.get("outputNetGeGpPerCycle")),
            },
            "liquidity": liquidity, "risk": risk, "inputs": inputs, "outputs": outputs,
            "priceSource": {
                "provider": "OSRS Wiki Prices / RuneLite",
                "current": "Latest observed high trades for inputs and low trades for outputs, including GE tax on outputs.",
                "expected": "Current profit blended with 24H, 7D and 30D historical market references according to price stability.",
                "conservative": "Lowest available Current, Expected, 24H, 7D or 30D profit reference.",
                "liquidity": "24H observed directional trade volume for the side required by the method.",
                "generatedAt": generated_at,
            },
            "description": str(afk.get("description") or current.get("notes") or ""), "reference": current.get("reference"),
        })

    methods.sort(key=lambda row: row["scenarios"]["expectedGpPerHour"] if row["scenarios"]["expectedGpPerHour"] is not None else float("-inf"), reverse=True)
    return {"schemaVersion": PUBLIC_SCHEMA_VERSION, "generatedAt": generated_at, "methods": methods}


def _freshness(age_seconds: int | float | None) -> str:
    if age_seconds is None: return "Unknown"
    age = float(age_seconds)
    if age <= 1800: return "Fresh"
    if age <= 7200: return "Recent"
    if age <= 86400: return "Delayed"
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
        if not use_fire_staff: rune_cost += _number(current.get("fireRunePrice")) or 0.0
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
    if status == "ok" and not warnings and failed == 0: state = "current"
    elif failed > 0 or warnings: state = "delayed"
    else: state = "data_issue"
    return {"schemaVersion": PUBLIC_SCHEMA_VERSION, "generatedAt": generated_at, "liveGeneratedAt": generated_at, "shortHistoryGeneratedAt": short_history_generated_at, "longHistoryGeneratedAt": long_history_generated_at, "state": state, "ageSeconds": 0}
