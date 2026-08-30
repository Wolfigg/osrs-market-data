from __future__ import annotations

from copy import deepcopy
from typing import Any

from .catalog_wave5 import wave5_method_catalog


def _input(name: str, quantity: float = 1.0, **extra: Any) -> dict[str, Any]:
    return {"item_name": name, "quantity": quantity, "buy_via_ge": True, **extra}


def _output(name: str, quantity: float = 1.0, **extra: Any) -> dict[str, Any]:
    return {"item_name": name, "quantity": quantity, **extra}


def _potion_modifier_override(method: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(method)
    variants = {str(row.get("id")): row for row in result.get("variants") or []}
    result["variants"] = []
    result["modifiers"] = []

    inputs = result.get("inputs") or []
    outputs = result.get("outputs") or []
    if inputs:
        inputs[0]["role"] = "unfinished"
    if len(inputs) > 1:
        inputs[-1]["role"] = "secondary"
    if outputs:
        outputs[0]["role"] = "primary"

    goggles = variants.get("prescription_goggles")
    if goggles:
        goggles_overrides = goggles.get("overrides") or {}
        goggles_inputs = goggles_overrides.get("inputs") or []
        expected = None
        maximum = None
        if goggles_inputs:
            secondary = goggles_inputs[-1]
            expected = secondary.get("quantity_expected")
            maximum = secondary.get("quantity_maximum")
        modifier: dict[str, Any] = {
            "id": "prescription_goggles",
            "requirements": {"equipment": ["Prescription goggles"]},
            "input_modifiers": [{
                "role": "secondary",
                "expected_multiplier": float(expected if expected is not None else 0.9),
                "maximum_multiplier": float(maximum if maximum is not None else 1.0),
            }],
        }
        variant_cph = goggles_overrides.get("cycles_per_hour")
        base_cph = float(result.get("cycles_per_hour") or 0)
        if variant_cph is not None and base_cph > 0 and float(variant_cph) != base_cph:
            modifier["throughput_multiplier"] = float(variant_cph) / base_cph
        result["modifiers"].append(modifier)

    chemistry = variants.get("amulet_of_chemistry")
    if chemistry:
        chemistry_overrides = chemistry.get("overrides") or {}
        chemistry_outputs = chemistry_overrides.get("outputs") or []
        chemistry_inputs = chemistry_overrides.get("inputs") or []
        if len(chemistry_outputs) >= 2:
            primary = chemistry_outputs[0]
            proc = chemistry_outputs[1]
            charge = next((row for row in chemistry_inputs if str(row.get("item_name")) == "Amulet of chemistry"), None)
            added_items: list[dict[str, Any]] = [{
                "side": "outputs",
                "item_name": proc.get("item_name"),
                "quantity": float(proc.get("quantity", 1)),
                "quantity_expected": float(proc.get("quantity_expected", 0.05)),
                "quantity_minimum": float(proc.get("quantity_minimum", 0.05)),
                "quantity_maximum": float(proc.get("quantity_maximum", proc.get("quantity_expected", 0.05))),
                "role": "chemistry_proc",
            }]
            if charge:
                added_items.append({
                    "side": "inputs",
                    "item_name": "Amulet of chemistry",
                    "quantity": float(charge.get("quantity", 1)),
                    "quantity_expected": float(charge.get("quantity_expected", 0.01)),
                    "quantity_maximum": float(charge.get("quantity_maximum", 0.2)),
                    "role": "chemistry_charge",
                })
            result["modifiers"].append({
                "id": "amulet_of_chemistry",
                "requirements": {"equipment": ["Amulet of chemistry"]},
                "output_modifiers": [{
                    "role": "primary",
                    "expected_multiplier": float(primary.get("quantity_expected", 0.95)),
                    "minimum_multiplier": float(primary.get("quantity_minimum", 0.95)),
                    "maximum_multiplier": float(primary.get("quantity_maximum", 0.95)),
                }],
                "added_items": added_items,
                "metadata": {"procChance": 0.05},
            })

    method_types = set(result.get("method_types") or [])
    method_types.discard("variants")
    if result["modifiers"]:
        method_types.add("probabilistic")
        method_types.add("modifiers")
    result["method_types"] = sorted(method_types)
    result.setdefault("model", {})["modifierEngine"] = "v2"
    return result


def _mixed_tuna_swordfish() -> dict[str, Any]:
    return {
        "enabled": True,
        "name": "Catch tuna & swordfish",
        "category": "gathering/fishing",
        "inputs": [],
        "outputs": [
            _output("Raw tuna", 1, quantity_expected=0.60, quantity_minimum=0.0, quantity_maximum=1.0),
            _output("Raw swordfish", 1, quantity_expected=0.40, quantity_minimum=0.0, quantity_maximum=1.0),
        ],
        "fixed_cost_gp_per_cycle": 0,
        "cycles_per_hour": 195,
        "theoretical_cycles_per_hour": 195,
        "planned_hours_per_day": 4,
        "afk": {
            "interval_seconds": 90,
            "intensity": "low",
            "description": "Mixed harpoon catch. The output mix is represented explicitly instead of treating the spot as swordfish-only.",
        },
        "requirements": {"members": False, "fishing": 50, "equipment": ["Harpoon"]},
        "notes": "Guide-baseline mixed catch: 117 tuna and 78 swordfish per hour, represented as a 60/40 distribution at 195 catches/h. Throughput remains source-assumption dependent and is not presented as a universal level-99 rate.",
        "reference": "https://oldschool.runescape.wiki/w/Money_making_guide/Catching_tuna_%26_swordfish_(free-to-play)",
        "method_types": ["gathering", "probabilistic"],
        "model": {
            "fishing": {
                "spotId": "harpoon_tuna_swordfish_f2p",
                "minimumLevel": 50,
                "pacingProfiles": {"active": 1.0, "realistic": 0.90, "afk": 0.75},
                "mixedCatch": True,
                "supportsFishBarrel": False,
                "supportsSpiritFlakes": False,
                "supportsRadasBlessing": False,
            },
            "source": {
                "type": "wiki_guide_baseline",
                "verifiedAt": "2026-08-30",
                "notes": "Guide baseline reports approximately 117 tuna and 78 swordfish per hour under its stated assumptions.",
            },
        },
    }


def wave6_method_catalog() -> dict[str, dict[str, Any]]:
    """Production overrides that move Wave 5 families onto reusable Wave 6 engines."""
    wave5 = wave5_method_catalog()
    methods: dict[str, dict[str, Any]] = {}

    for method_id, method in wave5.items():
        if method_id.startswith("make_") and method_id.endswith("_potions_v2") and method.get("variants"):
            methods[method_id] = _potion_modifier_override(method)

    # Super combat uses the same independent goggles modifier model even though
    # its base recipe is already four-dose and therefore has no chemistry proc.
    if "make_super_combat_potions_v2" in wave5:
        methods["make_super_combat_potions_v2"] = _potion_modifier_override(wave5["make_super_combat_potions_v2"])

    # The legacy swordfish-only row is mechanically misleading for the F2P
    # harpoon spot. Retain its ID as disabled for audit history and replace it
    # with an explicit mixed tuna/swordfish method.
    if "gather_fishing_swordfish" in wave5:
        legacy = deepcopy(wave5["gather_fishing_swordfish"])
        legacy["enabled"] = False
        legacy["notes"] = str(legacy.get("notes") or "") + " Superseded by gather_fishing_tuna_swordfish mixed-catch model."
        methods["gather_fishing_swordfish"] = legacy
    methods["gather_fishing_tuna_swordfish"] = _mixed_tuna_swordfish()

    return methods
