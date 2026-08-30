from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def _item(name: str, quantity: float = 1, *, buy_via_ge: bool = False) -> dict[str, Any]:
    row: dict[str, Any] = {"item_name": name, "quantity": quantity}
    if buy_via_ge:
        row["buy_via_ge"] = True
    return row


def load_catalogue_document(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"catalogue document must be an object: {source}")
    if int(payload.get("schemaVersion", 0)) != 1:
        raise ValueError(f"unsupported catalogue schema version in {source}")
    if not str(payload.get("family") or "").strip():
        raise ValueError(f"catalogue document family is required: {source}")
    return payload


def compile_jewellery_enchanting(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = load_catalogue_document(path)
    if payload.get("family") != "jewellery_enchanting":
        raise ValueError("expected jewellery_enchanting family")
    defaults = payload.get("defaults") or {}
    pieces = tuple(payload.get("pieces") or ())
    methods: dict[str, dict[str, Any]] = {}
    for tier_id, raw in (payload.get("tiers") or {}).items():
        level = int(raw["magicLevel"])
        runes = [(str(row["item"]), float(row.get("quantity", 1))) for row in raw.get("runes") or []]
        products = raw.get("products") or {}
        staff = raw.get("staff")
        for piece in pieces:
            product = products.get(piece)
            if not product:
                continue
            input_name = str(raw.get("inputNames", {}).get(piece) or f"{str(tier_id).title()} {piece}")
            base_inputs = [_item(input_name, buy_via_ge=True), *[_item(name, quantity, buy_via_ge=True) for name, quantity in runes]]
            variants = [{
                "id": "runes",
                "label": "Runes only",
                "overrides": {
                    "inputs": base_inputs,
                    "requirements": {"members": bool(raw.get("members", True)), "magic": level},
                },
            }]
            if staff:
                variants.append({
                    "id": "rune_staff",
                    "label": str(staff),
                    "overrides": {
                        "inputs": [_item(input_name, buy_via_ge=True), _item("Cosmic rune", buy_via_ge=True)],
                        "requirements": {"members": bool(raw.get("members", True)), "magic": level, "equipment": [str(staff)]},
                    },
                })
            method_id = f"enchant_{tier_id}_{piece}"
            methods[method_id] = {
                "enabled": True,
                "name": f"Enchant {tier_id} {piece}".replace("_", " "),
                "category": str(defaults.get("category", "bankstanding/magic")),
                "inputs": base_inputs,
                "outputs": [_item(str(product))],
                "fixed_cost_gp_per_cycle": 0,
                "cycles_per_hour": float(defaults.get("cyclesPerHour", 1600)),
                "theoretical_cycles_per_hour": float(defaults.get("theoreticalCyclesPerHour", 1600)),
                "planned_hours_per_day": float(defaults.get("plannedHoursPerDay", 4)),
                "afk": {
                    "interval_seconds": float(defaults.get("intervalSeconds", 2.25)),
                    "intensity": str(defaults.get("intensity", "moderate")),
                    "description": str(defaults.get("description", "Jewellery enchanting.")),
                },
                "requirements": {"members": bool(raw.get("members", True)), "magic": level},
                "notes": str(defaults.get("description", "Jewellery enchanting.")),
                "reference": str(payload.get("source", {}).get("url") or "https://oldschool.runescape.wiki/w/Enchanting"),
                "variants": variants,
                "method_types": ["bankstanding", "variants"],
                "source": dict(payload.get("source") or {}),
            }
    return methods


def _matches_selector(method_id: str, method: dict[str, Any], selector: dict[str, Any]) -> bool:
    prefix = selector.get("idPrefix")
    if prefix is not None and not method_id.startswith(str(prefix)):
        return False
    category_contains = selector.get("categoryContains")
    if category_contains is not None and str(category_contains).casefold() not in str(method.get("category") or "").casefold():
        return False
    return bool(prefix is not None or category_contains is not None)


def _paced_variant(base_rate: float, multiplier: float, variant_id: str, label: str, description: str, requirements: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": variant_id,
        "label": label,
        "description": description,
        "overrides": {
            "cycles_per_hour": round(base_rate * multiplier, 3),
            "requirements": deepcopy(requirements),
        },
    }


def compile_gathering_pacing(path: str | Path, base_methods: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    payload = load_catalogue_document(path)
    if payload.get("family") != "gathering_pacing":
        raise ValueError("expected gathering_pacing family")
    rules = payload.get("rules") or {}
    source = dict(payload.get("source") or {})
    compiled: dict[str, dict[str, Any]] = {}

    for method_id, base_method in base_methods.items():
        matching = [(rule_id, rule) for rule_id, rule in rules.items() if _matches_selector(method_id, base_method, rule.get("selector") or {})]
        if not matching:
            continue
        if len(matching) != 1:
            raise ValueError(f"{method_id}: gathering pacing matched {len(matching)} rules")
        rule_id, rule = matching[0]
        method = deepcopy(base_method)
        if method.get("enabled", True) is False:
            compiled[method_id] = method
            continue
        base_rate = float(method.get("cycles_per_hour") or 0)
        if base_rate <= 0:
            raise ValueError(f"{method_id}: gathering pacing requires cycles_per_hour > 0")
        requirements = deepcopy(method.get("requirements") or {})
        realistic = float(rule.get("realisticMultiplier", 0.90))
        afk = float(rule.get("afkMultiplier", 0.75))
        if not (0 < afk <= realistic <= 1):
            raise ValueError(f"{method_id}: invalid pacing multipliers")
        method["variants"] = [
            _paced_variant(base_rate, 1.0, "active", "Active", "Source-backed baseline throughput with sustained attention.", requirements),
            _paced_variant(base_rate, realistic, "realistic", "Realistic", "Continuous normal play with reaction, movement and banking losses.", requirements),
            _paced_variant(base_rate, afk, "afk", "AFK", "Lower-attention pacing. This is deliberately below the active guide baseline.", requirements),
        ]
        method["include_base_variant"] = False
        gathering = method.setdefault("model", {}).setdefault("gatheringV2", {})
        gathering.update(deepcopy(rule.get("model") or {}))
        gathering.update({
            "activityType": str(rule.get("activityType") or rule_id),
            "baselineCyclesPerHour": base_rate,
            "pacingProfiles": {"active": 1.0, "realistic": realistic, "afk": afk},
            "policySource": source,
        })
        if gathering.get("supportsAccountFishingModifiers"):
            equipment = list(requirements.get("equipment") or [])
            gathering.update({
                "minimumLevel": requirements.get("fishing"),
                "toolOptions": equipment,
                "supportsFishBarrel": bool(requirements.get("members", True)),
                "supportsRadasBlessing": bool(requirements.get("members", True)),
                "supportsSpiritFlakes": bool(requirements.get("members", True)),
                "mixedCatch": len(method.get("outputs") or []) > 1,
            })
            gathering.pop("supportsAccountFishingModifiers", None)
        types = set(method.get("method_types") or [])
        types.update(("gathering", "variants"))
        method["method_types"] = sorted(types)
        compiled[method_id] = method
    return compiled
