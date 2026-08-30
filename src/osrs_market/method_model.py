from __future__ import annotations

from copy import deepcopy
from typing import Any


def effective_cycle_seconds(method: dict[str, Any]) -> float | None:
    workflow = method.get("workflow") or {}
    values = [workflow.get("process_seconds"), workflow.get("bank_seconds"), workflow.get("travel_seconds")]
    if not any(value is not None for value in values):
        return None
    total = sum(float(value or 0) for value in values)
    return total if total > 0 else None


def effective_cycles_per_hour(method: dict[str, Any]) -> float:
    configured = float(method.get("cycles_per_hour", 0) or 0)
    cycle_seconds = effective_cycle_seconds(method)
    if cycle_seconds is None:
        return configured
    workflow_rate = 3600.0 / cycle_seconds
    return min(configured, workflow_rate) if configured > 0 else workflow_rate


def stochastic_quantity(entry: dict[str, Any], basis: str = "expected", *, input_side: bool = False) -> float:
    """Materialise a stochastic quantity for expected/conservative evaluation.

    Outputs use their minimum as the conservative lower bound. Inputs use their
    maximum as the conservative upper-cost bound. This is required for effects
    such as Prescription goggles, where expected secondary consumption is below
    one but conservative profitability must assume the secondary is consumed.
    """
    if basis == "minimum":
        key = "quantity_maximum" if input_side else "quantity_minimum"
        if entry.get(key) is not None:
            return float(entry[key])
    if basis == "maximum":
        key = "quantity_minimum" if input_side else "quantity_maximum"
        if entry.get(key) is not None:
            return float(entry[key])
    if entry.get("quantity_expected") is not None:
        return float(entry["quantity_expected"])
    quantity = float(entry.get("quantity", 1) or 0)
    probability = entry.get("probability")
    if probability is not None:
        return quantity * float(probability)
    return quantity


def output_quantity(entry: dict[str, Any], basis: str = "expected") -> float:
    return stochastic_quantity(entry, basis, input_side=False)


def input_quantity(entry: dict[str, Any], basis: str = "expected") -> float:
    return stochastic_quantity(entry, basis, input_side=True)


def method_has_probabilistic_quantities(method: dict[str, Any]) -> bool:
    return any(
        entry.get("quantity_expected") is not None
        or entry.get("quantity_minimum") is not None
        or entry.get("quantity_maximum") is not None
        or entry.get("probability") is not None
        for side in ("inputs", "outputs")
        for entry in method.get(side, [])
    )


def method_has_probabilistic_outputs(method: dict[str, Any]) -> bool:
    return any(
        entry.get("quantity_expected") is not None
        or entry.get("quantity_minimum") is not None
        or entry.get("quantity_maximum") is not None
        or entry.get("probability") is not None
        for entry in method.get("outputs", [])
    )


def iter_method_variants(method_id: str, method: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    variants = method.get("variants") or []
    if not variants:
        return [(method_id, method)]
    rows: list[tuple[str, dict[str, Any]]] = []
    if bool(method.get("include_base_variant", False)):
        rows.append((method_id, method))
    for raw in variants:
        variant = deepcopy(method)
        variant.pop("variants", None)
        variant_id = str(raw.get("id") or "default")
        _deep_merge(variant, raw.get("overrides") or {})
        variant["variant"] = {
            "baseMethodId": method_id,
            "id": variant_id,
            "label": str(raw.get("label") or variant_id.replace("_", " ").title()),
            "description": str(raw.get("description") or ""),
        }
        rows.append((f"{method_id}__{variant_id}", variant))
    return rows


def all_method_item_ids(method: dict[str, Any]) -> set[int]:
    ids: set[int] = set()
    for _, variant in iter_method_variants("method", method):
        for side in ("inputs", "outputs"):
            for entry in variant.get(side, []):
                if entry.get("item_id") is not None:
                    ids.add(int(entry["item_id"]))
    for modifier in method.get("modifiers") or []:
        for entry in modifier.get("added_items") or []:
            if entry.get("item_id") is not None:
                ids.add(int(entry["item_id"]))
    return ids


def _deep_merge(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = deepcopy(value)
