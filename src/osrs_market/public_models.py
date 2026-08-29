from __future__ import annotations

from typing import Any

PUBLIC_SCHEMA_VERSION = 1
LOW_CAPITAL_THRESHOLD_GP = 1_000_000

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
        return {
            "level": "unavailable",
            "label": "Unavailable",
            "reasons": ["Current calculation is not reliable enough to publish."],
        }

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

    labels = {
        "normal": "Normal market risk",
        "watch": "Watch market conditions",
        "high": "High market risk",
        "unavailable": "Unavailable",
    }
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

        inputs = [
            {"name": str(row.get("name", "")), "quantity": _intish(row.get("quantity"))}
            for row in (current.get("inputs") or [])
        ]
        outputs = [
            {"name": str(row.get("name", "")), "quantity": _intish(row.get("quantity"))}
            for row in (current.get("outputs") or [])
        ]

        interval = _number(afk.get("intervalSeconds"))
        buy_limit_constrained = sustainable_cph + 1e-9 < (_number(mechanics.get("cyclesPerHour")) or 0.0)
        risk = public_risk(current.get("warnings"), valid=valid)

        methods.append(
            {
                "methodId": method_id,
                "name": str(current.get("name", method_id)),
                "category": _category(current.get("category")),
                "tags": _tags(current),
                "members": _members(current),
                "requirements": _requirements(current),
                "current": {"valid": valid, "gpPerHour": current_gp if valid else None},
                "history": history,
                "afk": {
                    "classification": classify_afk(interval),
                    "intervalSeconds": _intish(interval),
                    "gpPerInteraction": _number(afk.get("gpPerInteractionWindow")) if valid else None,
                    "description": str(afk.get("description") or ""),
                },
                "economics": {
                    "capitalOneHour": round(capital_one_hour) if inputs else 0,
                    "capitalFourHours": round(capital_four_hours) if inputs else 0,
                    "buyLimitConstrained": buy_limit_constrained,
                },
                "risk": risk,
                "inputs": inputs,
                "outputs": outputs,
                "description": str(afk.get("description") or current.get("notes") or ""),
                "reference": current.get("reference"),
            }
        )

    methods.sort(
        key=lambda row: row["current"]["gpPerHour"]
        if row["current"]["valid"] and row["current"]["gpPerHour"] is not None
        else float("-inf"),
        reverse=True,
    )
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


def build_public_alchemy(
    generated_at: int,
    candidates: list[dict[str, Any]],
    assumptions: dict[str, Any],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    use_fire_staff = bool(assumptions.get("useFireStaff", True))
    for row in candidates:
        current = row.get("currentInstant") or {}
        valid = bool(current.get("valid")) and current.get("profitPerCast") is not None
        rune_cost = _number(current.get("natureRunePrice")) or 0.0
        if not use_fire_staff:
            rune_cost += _number(current.get("fireRunePrice")) or 0.0
        history = row.get("historicalInstant24h") or {}
        risk = public_risk(row.get("warnings"), valid=valid)
        items.append(
            {
                "itemId": int(row["itemId"]),
                "name": str(row.get("name", row["itemId"])),
                "members": bool(row.get("members", True)),
                "buyPrice": _intish(current.get("buyPrice")) if valid else None,
                "highAlchValue": _intish(row.get("highAlchValue")),
                "runeCost": _intish(rune_cost) if valid else None,
                "profitPerCast": _number(current.get("profitPerCast")) if valid else None,
                "roi": _number(current.get("roiPct")) if valid else None,
                "buyLimit": _intish(row.get("geBuyLimit")),
                "quantity4h": _intish((row.get("capacity4h") or {}).get("maxQuantity")) if valid else None,
                "profit4h": _number(row.get("profitPer4hGeLimit")) if valid else None,
                "capitalRequired": _number(row.get("capitalRequired")) if valid else None,
                "volume24h": _intish(row.get("volume24h")),
                "freshness": _freshness(row.get("buyPriceAgeSeconds")),
                "history24hProfitPerCast": _number(history.get("profitPerCast")) if history.get("valid") else None,
                "risk": risk,
            }
        )
    items.sort(key=lambda row: row["profit4h"] if row["profit4h"] is not None else float("-inf"), reverse=True)
    return {
        "schemaVersion": PUBLIC_SCHEMA_VERSION,
        "generatedAt": generated_at,
        "assumptions": {
            "magicLevel": 55,
            "castsPerHour": int(assumptions.get("castsPerHour", 1200)),
            "natureRuneCost": next((item["runeCost"] for item in items if item["runeCost"] is not None), None),
            "fireStaff": use_fire_staff,
        },
        "items": items,
    }


def build_public_status(generated_at: int, internal_health: dict[str, Any]) -> dict[str, Any]:
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
    return {"schemaVersion": PUBLIC_SCHEMA_VERSION, "generatedAt": generated_at, "state": state, "ageSeconds": 0}


def _featured_afk(methods: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [m for m in methods if m["current"]["valid"] and m["current"]["gpPerHour"] is not None]
    if not valid:
        return None
    method = max(valid, key=lambda row: row["current"]["gpPerHour"])
    current = method["current"]["gpPerHour"]
    ref24 = method["history"].get("24hGpPerHour")
    reason = "Highest valid current AFK GP/hour in the public ledger."
    if ref24 and current and current > ref24:
        reason = "Current profit is above its 24-hour reference while remaining a valid AFK method."
    return {
        "methodId": method["methodId"],
        "name": method["name"],
        "category": method["category"],
        "currentGpPerHour": current,
        "reference24hGpPerHour": ref24,
        "afkIntervalSeconds": method["afk"]["intervalSeconds"],
        "gpPerInteraction": method["afk"]["gpPerInteraction"],
        "capitalOneHour": method["economics"]["capitalOneHour"],
        "members": method["members"],
        "risk": method["risk"]["level"],
        "reason": reason,
    }


def _featured_alchemy(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [i for i in items if i["profit4h"] is not None and i["profitPerCast"] is not None]
    if not valid:
        return None
    item = max(valid, key=lambda row: row["profit4h"])
    return {
        "itemId": item["itemId"],
        "name": item["name"],
        "profitPerCast": item["profitPerCast"],
        "profit4h": item["profit4h"],
        "quantity4h": item["quantity4h"],
        "capitalRequired": item["capitalRequired"],
        "members": item["members"],
        "freshness": item["freshness"],
        "risk": item["risk"]["level"],
    }


def _notice(kind: str, title: str, text: str, method_id: str | None = None) -> dict[str, Any]:
    payload = {"kind": kind, "title": title, "text": text}
    if method_id:
        payload["methodId"] = method_id
    return payload


def build_dashboard(generated_at: int, afk_payload: dict[str, Any], alchemy_payload: dict[str, Any]) -> dict[str, Any]:
    methods = afk_payload.get("methods") or []
    items = alchemy_payload.get("items") or []
    valid = [m for m in methods if m["current"]["valid"] and m["current"]["gpPerHour"] is not None]
    notices: list[dict[str, Any]] = []

    if valid:
        best = max(valid, key=lambda row: row["current"]["gpPerHour"])
        notices.append(_notice("MARKET NOTICE", "Highest current AFK", f"{best['name']} leads at {best['current']['gpPerHour']:,.0f} GP/hour.", best["methodId"]))

        interaction = [m for m in valid if m["afk"]["gpPerInteraction"] is not None]
        if interaction:
            top = max(interaction, key=lambda row: row["afk"]["gpPerInteraction"])
            notices.append(_notice("AFK VALUE", "Best GP per interaction", f"{top['name']} yields about {top['afk']['gpPerInteraction']:,.0f} GP per interaction window.", top["methodId"]))

        low_capital = [m for m in valid if (m["economics"]["capitalOneHour"] or 0) <= LOW_CAPITAL_THRESHOLD_GP]
        if low_capital:
            top = max(low_capital, key=lambda row: row["current"]["gpPerHour"])
            notices.append(_notice("LOW CAPITAL", "Best under 1m", f"{top['name']} is the strongest valid method below 1,000,000 GP one-hour capital.", top["methodId"]))

        changes = []
        for m in valid:
            ref = m["history"].get("24hGpPerHour")
            cur = m["current"]["gpPerHour"]
            if ref not in (None, 0) and cur is not None:
                changes.append((cur - ref, (cur - ref) / abs(ref), m))
        stronger = [x for x in changes if x[0] > 0]
        if stronger:
            delta, pct, top = max(stronger, key=lambda x: x[0])
            notices.append(_notice("ABOVE 24H", "Stronger than reference", f"{top['name']} is {pct * 100:.0f}% above its 24-hour GP/hour reference.", top["methodId"]))
        weaker = [x for x in changes if x[1] <= -0.10]
        if weaker:
            delta, pct, top = min(weaker, key=lambda x: x[1])
            notices.append(_notice("WATCH", "Below 24H reference", f"{top['name']} is {abs(pct) * 100:.0f}% below its 24-hour GP/hour reference.", top["methodId"]))

        f2p = [m for m in valid if not m["members"]]
        if f2p:
            top = max(f2p, key=lambda row: row["current"]["gpPerHour"])
            notices.append(_notice("F2P", "Best free-to-play", f"{top['name']} leads the current F2P AFK list.", top["methodId"]))

    return {
        "schemaVersion": PUBLIC_SCHEMA_VERSION,
        "generatedAt": generated_at,
        "featuredAfk": _featured_afk(methods),
        "featuredAlchemy": _featured_alchemy(items),
        "notices": notices[:6],
    }
