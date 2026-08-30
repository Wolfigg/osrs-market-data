from __future__ import annotations

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
