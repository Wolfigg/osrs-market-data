from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from .method_model import effective_cycles_per_hour, input_quantity, iter_method_variants, method_has_probabilistic_quantities, output_quantity
from .methods import evaluate_method as evaluate_legacy_method
from .personalisation import materialise_method_for_player
from .player_profile import PlayerProfile


def cooking_success_probability(profile: dict[str, Any], level: int, location: str, gauntlets: bool, cooking_cape: bool = False) -> float:
    minimum = int(profile.get("minimumLevel", 1))
    level = max(minimum, min(99, int(level)))
    if cooking_cape and level >= 99:
        return 1.0
    key = str(location or "range")
    if gauntlets and bool(profile.get("gauntletsAffected")):
        candidate = f"gauntlets_{key}"
        if candidate in (profile.get("curves") or {}):
            key = candidate
    curve = (profile.get("curves") or {}).get(key) or (profile.get("curves") or {}).get("range")
    if not curve:
        return 1.0
    low = float(curve["low"])
    high = float(curve["high"])
    value = math.floor(low * (99 - level) / 98 + high * (level - 1) / 98 + 0.5) + 1
    return max(0.0, min(1.0, value / 256.0))


def _apply_cooking_model(method: dict[str, Any]) -> dict[str, Any]:
    cooked = deepcopy(method)
    profile = ((cooked.get("model") or {}).get("cooking") or {})
    if not profile:
        return cooked
    defaults = profile.get("defaults") or {}
    level = int(defaults.get("level", 99))
    location = str(defaults.get("location", "range"))
    gauntlets = bool(defaults.get("gauntlets", False))
    cape = bool(defaults.get("cookingCape", False))
    success = cooking_success_probability(profile, level, location, gauntlets, cape)
    if cooked.get("outputs"):
        cooked["outputs"][0]["quantity_expected"] = success
        cooked["outputs"][0]["quantity_minimum"] = 1.0 if success >= 1.0 else 0.0
        cooked["outputs"][0]["quantity_maximum"] = 1.0
    cooked.setdefault("model", {})["cookingResult"] = {
        "level": level,
        "location": location,
        "gauntlets": gauntlets,
        "cookingCape": cape,
        "successProbability": success,
        "burnProbability": 1.0 - success,
        "expectedCookedPerCycle": success,
        "expectedBurntPerCycle": 1.0 - success,
    }
    return cooked


def _materialise_method(method: dict[str, Any], basis: str) -> dict[str, Any]:
    materialised = _apply_cooking_model(method)
    materialised["cycles_per_hour"] = effective_cycles_per_hour(materialised)
    for entry in materialised.get("inputs", []):
        entry["quantity"] = input_quantity(entry, basis)
        for key in ("quantity_expected", "quantity_minimum", "quantity_maximum", "probability"):
            entry.pop(key, None)
    for entry in materialised.get("outputs", []):
        entry["quantity"] = output_quantity(entry, basis)
        for key in ("quantity_expected", "quantity_minimum", "quantity_maximum", "probability"):
            entry.pop(key, None)
    return materialised


def evaluate_method(
    method_id: str,
    method: dict[str, Any],
    item_records: dict[int, dict[str, Any]],
    exempt_item_ids: set[int],
    settings: dict[str, Any],
    generated_at: int,
    player_profile: PlayerProfile | dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if player_profile is None:
        variants = iter_method_variants(method_id, method)
    else:
        materialised = materialise_method_for_player(method_id, method, player_profile)
        if not materialised.available:
            return []
        variants = [(materialised.method_id, materialised.method)]

    for variant_method_id, raw_variant in variants:
        variant = _apply_cooking_model(raw_variant)
        expected_method = _materialise_method(variant, "expected")
        expected_results = evaluate_legacy_method(variant_method_id, expected_method, item_records, exempt_item_ids, settings, generated_at)
        lower_by_scenario: dict[str, dict[str, Any]] = {}
        probabilistic = method_has_probabilistic_quantities(variant)
        if probabilistic:
            minimum_method = _materialise_method(variant, "minimum")
            lower_results = evaluate_legacy_method(variant_method_id, minimum_method, item_records, exempt_item_ids, settings, generated_at)
            lower_by_scenario = {str(row["scenario"]): row for row in lower_results}
        workflow = variant.get("workflow") or {}
        variant_meta = variant.get("variant") or {}
        model_meta = variant.get("model") or {}
        personalised = variant.get("personalisation") or {}
        for row in expected_results:
            lower = lower_by_scenario.get(str(row["scenario"]))
            economics = row.setdefault("economics", {})
            economics["profitGpPerCycleLowerBound"] = ((lower.get("economics") or {}).get("profitGpPerCycle") if lower else economics.get("profitGpPerCycle"))
            economics["profitGpPerHourLowerBoundSustainable"] = ((lower.get("economics") or {}).get("profitGpPerHourBuyLimitSustainable") if lower else economics.get("profitGpPerHourBuyLimitSustainable"))
            row["personalisation"] = personalised or None
            row["model"] = {
                "probabilisticOutputs": probabilistic,
                "expectedValueUsed": probabilistic,
                "conservativeUsesLowerBound": probabilistic,
                "workflow": {"processSeconds": workflow.get("process_seconds"), "bankSeconds": workflow.get("bank_seconds"), "travelSeconds": workflow.get("travel_seconds"), "inventorySize": workflow.get("inventory_size"), "itemsPerInventory": workflow.get("items_per_inventory")},
                "variant": variant_meta or None,
                "cooking": model_meta.get("cooking"),
                "cookingResult": model_meta.get("cookingResult"),
                "doseModel": model_meta.get("doseModel"),
                "unpricedInputs": model_meta.get("unpricedInputs"),
                "excludedExpectedOutputs": model_meta.get("excludedExpectedOutputs"),
            }
            if probabilistic:
                row.setdefault("warnings", []).append("EXPECTED_VALUE_OUTPUT_MODEL")
            if model_meta.get("unpricedInputs"):
                row.setdefault("warnings", []).append("UNPRICED_SELF_SUPPLIED_INPUT")
            results.append(row)
    return results
