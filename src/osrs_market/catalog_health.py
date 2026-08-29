from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _days_old(value: Any, today: date) -> int | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            parsed = date.fromisoformat(str(value))
        except ValueError:
            return None
    return (today - parsed).days


def build_catalog_health(methods: dict[str, dict[str, Any]], *, today: date | None = None, stale_days: int = 90) -> dict[str, Any]:
    today = today or date.today()
    counters = {
        "methods": len(methods), "families": 0, "variants": 0, "verified": 0,
        "needsReview": 0, "staleAssumptions": 0, "missingPriceMappings": 0,
        "brokenItemMappings": 0, "methodsWithoutProvenance": 0,
        "methodsWithoutConservativeModel": 0, "methodsWithoutLiquidityModel": 0,
        "methodsWithoutRequirements": 0, "methodsWithoutThroughputDistribution": 0,
    }
    details: dict[str, list[str]] = {key: [] for key in counters if key not in {"methods", "families", "variants", "verified"}}
    family_ids: set[str] = set()

    for method_id, method in methods.items():
        variant = method.get("variant") or {}
        family_ids.add(str(variant.get("baseMethodId") or method_id).split("__", 1)[0])
        counters["variants"] += len(method.get("variants") or [])
        audit = method.get("audit") or {}
        if audit.get("status") == "verified":
            counters["verified"] += 1
        else:
            counters["needsReview"] += 1; details["needsReview"].append(method_id)
        age = _days_old(audit.get("verified_at"), today)
        if age is None or age > stale_days:
            counters["staleAssumptions"] += 1; details["staleAssumptions"].append(method_id)
        for side in ("inputs", "outputs"):
            for entry in method.get(side) or []:
                if entry.get("item_id") is None and not entry.get("item_name"):
                    counters["brokenItemMappings"] += 1; details["brokenItemMappings"].append(method_id); break
                if entry.get("item_id") is None:
                    counters["missingPriceMappings"] += 1; details["missingPriceMappings"].append(method_id); break
        if not method.get("provenance"):
            counters["methodsWithoutProvenance"] += 1; details["methodsWithoutProvenance"].append(method_id)
        probabilistic = any(any(entry.get(key) is not None for key in ("probability", "quantity_expected", "quantity_minimum", "quantity_maximum")) for side in ("inputs", "outputs") for entry in (method.get(side) or []))
        if probabilistic and not any(entry.get("quantity_minimum") is not None for side in ("inputs", "outputs") for entry in (method.get(side) or [])):
            counters["methodsWithoutConservativeModel"] += 1; details["methodsWithoutConservativeModel"].append(method_id)
        if not method.get("liquidity") and not any(bool(entry.get("buy_via_ge", True)) for entry in method.get("inputs") or []) and not method.get("outputs"):
            counters["methodsWithoutLiquidityModel"] += 1; details["methodsWithoutLiquidityModel"].append(method_id)
        if not method.get("requirements"):
            counters["methodsWithoutRequirements"] += 1; details["methodsWithoutRequirements"].append(method_id)
        if not (method.get("throughput") or {}).get("quantiles"):
            counters["methodsWithoutThroughputDistribution"] += 1; details["methodsWithoutThroughputDistribution"].append(method_id)

    counters["families"] = len(family_ids)
    return {"schemaVersion": 1, "generatedForDate": today.isoformat(), "summary": counters, "issues": {key: sorted(set(value)) for key, value in details.items()}}
