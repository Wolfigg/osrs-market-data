from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal

from .player_profile import PlayerProfile, evaluate_requirements, stable_id

Side = Literal["inputs", "outputs"]


@dataclass(frozen=True, slots=True)
class QuantityModifier:
    side: Side
    item_name: str | None = None
    item_id: int | None = None
    role: str | None = None
    expected_multiplier: float = 1.0
    minimum_multiplier: float | None = None
    maximum_multiplier: float | None = None
    quantity_add: float = 0.0

    def matches(self, entry: dict[str, Any]) -> bool:
        if self.item_id is not None and int(entry.get("item_id") or 0) != self.item_id:
            return False
        if self.item_name is not None and str(entry.get("item_name") or "").casefold() != self.item_name.casefold():
            return False
        if self.role is not None and stable_id(str(entry.get("role") or "")) != stable_id(self.role):
            return False
        return self.item_id is not None or self.item_name is not None or self.role is not None


@dataclass(frozen=True, slots=True)
class AddedItem:
    side: Side
    item_name: str | None = None
    item_id: int | None = None
    quantity: float = 1.0
    quantity_expected: float | None = None
    quantity_minimum: float | None = None
    quantity_maximum: float | None = None
    buy_via_ge: bool = True
    role: str | None = None

    def to_entry(self) -> dict[str, Any]:
        row: dict[str, Any] = {"quantity": self.quantity}
        if self.item_name is not None:
            row["item_name"] = self.item_name
        if self.item_id is not None:
            row["item_id"] = self.item_id
        if self.side == "inputs":
            row["buy_via_ge"] = self.buy_via_ge
        if self.role is not None:
            row["role"] = self.role
        for key, value in (
            ("quantity_expected", self.quantity_expected),
            ("quantity_minimum", self.quantity_minimum),
            ("quantity_maximum", self.quantity_maximum),
        ):
            if value is not None:
                row[key] = value
        return row


@dataclass(frozen=True, slots=True)
class MethodModifier:
    id: str
    requirements: dict[str, Any] = field(default_factory=dict)
    input_modifiers: tuple[QuantityModifier, ...] = ()
    output_modifiers: tuple[QuantityModifier, ...] = ()
    added_items: tuple[AddedItem, ...] = ()
    throughput_multiplier: float = 1.0
    capacity_modifier: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def available(self, profile: PlayerProfile) -> bool:
        met, _ = evaluate_requirements(self.requirements, profile)
        return met


def _as_modifier(raw: MethodModifier | dict[str, Any]) -> MethodModifier:
    if isinstance(raw, MethodModifier):
        return raw

    def quantity(row: dict[str, Any], side: Side) -> QuantityModifier:
        return QuantityModifier(
            side=side,
            item_name=row.get("item_name"),
            item_id=int(row["item_id"]) if row.get("item_id") is not None else None,
            role=row.get("role"),
            expected_multiplier=float(row.get("expected_multiplier", 1.0)),
            minimum_multiplier=float(row["minimum_multiplier"]) if row.get("minimum_multiplier") is not None else None,
            maximum_multiplier=float(row["maximum_multiplier"]) if row.get("maximum_multiplier") is not None else None,
            quantity_add=float(row.get("quantity_add", 0.0)),
        )

    added: list[AddedItem] = []
    for row in raw.get("added_items") or []:
        side = str(row.get("side") or "inputs")
        if side not in {"inputs", "outputs"}:
            raise ValueError(f"modifier {raw.get('id')}: invalid added item side {side}")
        added.append(AddedItem(
            side=side,  # type: ignore[arg-type]
            item_name=row.get("item_name"),
            item_id=int(row["item_id"]) if row.get("item_id") is not None else None,
            quantity=float(row.get("quantity", 1.0)),
            quantity_expected=float(row["quantity_expected"]) if row.get("quantity_expected") is not None else None,
            quantity_minimum=float(row["quantity_minimum"]) if row.get("quantity_minimum") is not None else None,
            quantity_maximum=float(row["quantity_maximum"]) if row.get("quantity_maximum") is not None else None,
            buy_via_ge=bool(row.get("buy_via_ge", True)),
            role=row.get("role"),
        ))
    return MethodModifier(
        id=str(raw["id"]),
        requirements=dict(raw.get("requirements") or {}),
        input_modifiers=tuple(quantity(row, "inputs") for row in raw.get("input_modifiers") or []),
        output_modifiers=tuple(quantity(row, "outputs") for row in raw.get("output_modifiers") or []),
        added_items=tuple(added),
        throughput_multiplier=float(raw.get("throughput_multiplier", 1.0)),
        capacity_modifier=int(raw.get("capacity_modifier", 0)),
        metadata=dict(raw.get("metadata") or {}),
    )


def modifiers_from_method(method: dict[str, Any]) -> list[MethodModifier]:
    return [_as_modifier(row) for row in method.get("modifiers") or []]


def resolve_modifiers(method: dict[str, Any], profile: PlayerProfile) -> list[MethodModifier]:
    return [modifier for modifier in modifiers_from_method(method) if modifier.available(profile)]


def _apply_quantity_modifier(entry: dict[str, Any], modifier: QuantityModifier, *, input_side: bool) -> None:
    if not modifier.matches(entry):
        return
    base = float(entry.get("quantity", 1.0))
    current_expected = float(entry.get("quantity_expected", base))
    entry["quantity_expected"] = max(0.0, current_expected * modifier.expected_multiplier + modifier.quantity_add)

    if modifier.minimum_multiplier is not None:
        current_minimum = float(entry.get("quantity_minimum", base))
        entry["quantity_minimum"] = max(0.0, current_minimum * modifier.minimum_multiplier + modifier.quantity_add)
    if modifier.maximum_multiplier is not None:
        current_maximum = float(entry.get("quantity_maximum", base))
        entry["quantity_maximum"] = max(0.0, current_maximum * modifier.maximum_multiplier + modifier.quantity_add)

    # Conservative accounting requires an explicit upper bound for inputs and
    # lower bound for outputs when expected consumption/output was changed.
    if input_side and modifier.maximum_multiplier is None:
        entry.setdefault("quantity_maximum", base)
    if not input_side and modifier.minimum_multiplier is None:
        entry.setdefault("quantity_minimum", min(base, float(entry["quantity_expected"])))


def apply_modifiers(method: dict[str, Any], modifiers: list[MethodModifier]) -> tuple[dict[str, Any], list[str]]:
    result = deepcopy(method)
    applied: list[str] = []
    for modifier in modifiers:
        for quantity_modifier in modifier.input_modifiers:
            for entry in result.get("inputs", []):
                _apply_quantity_modifier(entry, quantity_modifier, input_side=True)
        for quantity_modifier in modifier.output_modifiers:
            for entry in result.get("outputs", []):
                _apply_quantity_modifier(entry, quantity_modifier, input_side=False)
        for added in modifier.added_items:
            result.setdefault(added.side, []).append(added.to_entry())
        if modifier.throughput_multiplier != 1.0:
            for key in ("cycles_per_hour", "theoretical_cycles_per_hour"):
                if result.get(key) is not None:
                    result[key] = float(result[key]) * modifier.throughput_multiplier
        if modifier.capacity_modifier:
            workflow = result.setdefault("workflow", {})
            current = int(workflow.get("inventory_capacity") or workflow.get("inventory_size") or 28)
            workflow["inventory_capacity"] = max(1, current + modifier.capacity_modifier)
        result.setdefault("model", {}).setdefault("appliedModifiers", []).append({
            "id": modifier.id,
            **deepcopy(modifier.metadata),
        })
        applied.append(modifier.id)
    return result, applied
