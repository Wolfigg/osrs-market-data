from __future__ import annotations

from copy import deepcopy
from typing import Any

from .method_model import effective_cycles_per_hour, iter_method_variants, method_has_probabilistic_outputs, output_quantity
from .methods import evaluate_method as evaluate_legacy_method


def _materialise_method(method: dict[str, Any], basis: str) -> dict[str, Any]:
    materialised = deepcopy(method)
    materialised["cycles_per_hour"] = effective_cycles_per_hour(materialised)
    for entry in materialised.get("outputs", []):
        entry["quantity"] = output_quantity(entry, basis)
        entry.pop("quantity_expected", None)
        entry.pop("quantity_minimum", None)
        entry.pop("quantity_maximum", None)
        entry.pop("probability", None)
    return materialised


def evaluate_method(
    method_id: str,
    method: dict[str, Any],
    item_records: dict[int, dict[str, Any]],
    exempt_item_ids: set[int],
    settings: dict[str, Any],
    generated_at: int,
) -> list[dict[str, Any]]:
    """Evaluate base methods, variants, workflow timing and probabilistic outputs.

    The existing deterministic evaluator remains the pricing/tax/liquidity core.
    This adapter expands variants, converts workflow timing into an effective
    mechanical rate, evaluates expected output, and separately evaluates the
    configured lower-bound output for Conservative profitability.
    """
    results: list[dict[str, Any]] = []
    for variant_method_id, variant in iter_method_variants(method_id, method):
        expected_method = _materialise_method(variant, "expected")
        expected_results = evaluate_legacy_method(
            variant_method_id,
            expected_method,
            item_records,
            exempt_item_ids,
            settings,
            generated_at,
        )

        lower_by_scenario: dict[str, dict[str, Any]] = {}
        probabilistic = method_has_probabilistic_outputs(variant)
        if probabilistic:
            minimum_method = _materialise_method(variant, "minimum")
            lower_results = evaluate_legacy_method(
                variant_method_id,
                minimum_method,
                item_records,
                exempt_item_ids,
                settings,
                generated_at,
            )
            lower_by_scenario = {str(row["scenario"]): row for row in lower_results}

        workflow = variant.get("workflow") or {}
        variant_meta = variant.get("variant") or {}
        for row in expected_results:
            lower = lower_by_scenario.get(str(row["scenario"]))
            economics = row.setdefault("economics", {})
            economics["profitGpPerCycleLowerBound"] = (
                (lower.get("economics") or {}).get("profitGpPerCycle") if lower else economics.get("profitGpPerCycle")
            )
            economics["profitGpPerHourLowerBoundSustainable"] = (
                (lower.get("economics") or {}).get("profitGpPerHourBuyLimitSustainable")
                if lower
                else economics.get("profitGpPerHourBuyLimitSustainable")
            )
            row["model"] = {
                "probabilisticOutputs": probabilistic,
                "expectedValueUsed": probabilistic,
                "conservativeUsesLowerBound": probabilistic,
                "workflow": {
                    "processSeconds": workflow.get("process_seconds"),
                    "bankSeconds": workflow.get("bank_seconds"),
                    "travelSeconds": workflow.get("travel_seconds"),
                    "inventorySize": workflow.get("inventory_size"),
                    "itemsPerInventory": workflow.get("items_per_inventory"),
                },
                "variant": variant_meta or None,
            }
            if probabilistic:
                row.setdefault("warnings", []).append("EXPECTED_VALUE_OUTPUT_MODEL")
            results.append(row)
    return results
