import pytest

from osrs_market.modifiers import apply_modifiers, resolve_modifiers
from osrs_market.player_profile import PlayerProfile, SkillProfile


def potion_method():
    return {
        "inputs": [
            {"item_name": "Ranarr potion (unf)", "quantity": 1, "role": "unfinished"},
            {"item_name": "Snape grass", "quantity": 1, "role": "secondary"},
        ],
        "outputs": [{"item_name": "Prayer potion(3)", "quantity": 1, "role": "primary"}],
        "cycles_per_hour": 2500,
        "modifiers": [
            {
                "id": "prescription_goggles",
                "requirements": {"equipment": ["Prescription goggles"]},
                "input_modifiers": [
                    {"role": "secondary", "expected_multiplier": 0.9, "maximum_multiplier": 1.0}
                ],
            },
            {
                "id": "amulet_of_chemistry",
                "requirements": {"equipment": ["Amulet of chemistry"]},
                "output_modifiers": [
                    {"role": "primary", "expected_multiplier": 0.95, "minimum_multiplier": 0.95}
                ],
                "added_items": [
                    {
                        "side": "outputs",
                        "item_name": "Prayer potion(4)",
                        "quantity": 1,
                        "quantity_expected": 0.05,
                        "quantity_minimum": 0.05,
                        "quantity_maximum": 0.05,
                        "role": "chemistry_proc",
                    },
                    {
                        "side": "inputs",
                        "item_name": "Amulet of chemistry",
                        "quantity": 1,
                        "quantity_expected": 0.01,
                        "quantity_maximum": 0.2,
                        "role": "chemistry_charge",
                    },
                ],
            },
        ],
    }


def test_independent_modifiers_compose_without_combo_variant():
    profile = PlayerProfile(
        skills=SkillProfile(herblore=99),
        equipment={"Prescription goggles", "Amulet of chemistry"},
    )
    modifiers = resolve_modifiers(potion_method(), profile)
    method, applied = apply_modifiers(potion_method(), modifiers)

    assert applied == ["prescription_goggles", "amulet_of_chemistry"]
    secondary = next(row for row in method["inputs"] if row.get("role") == "secondary")
    assert secondary["quantity_expected"] == 0.9
    assert secondary["quantity_maximum"] == 1.0
    primary = next(row for row in method["outputs"] if row.get("role") == "primary")
    assert primary["quantity_expected"] == 0.95
    assert any(row.get("item_name") == "Prayer potion(4)" for row in method["outputs"])
    assert any(row.get("item_name") == "Amulet of chemistry" for row in method["inputs"])


def test_unowned_modifier_is_not_applied():
    profile = PlayerProfile(skills=SkillProfile(herblore=99), equipment={"Prescription goggles"})
    modifiers = resolve_modifiers(potion_method(), profile)
    method, applied = apply_modifiers(potion_method(), modifiers)

    assert applied == ["prescription_goggles"]
    assert not any(row.get("item_name") == "Prayer potion(4)" for row in method["outputs"])


def test_capacity_and_throughput_modifiers_are_generic():
    method = {
        "cycles_per_hour": 100,
        "theoretical_cycles_per_hour": 120,
        "workflow": {"inventory_capacity": 28},
        "inputs": [],
        "outputs": [{"item_name": "Fish", "quantity": 1}],
    }
    raw = [{
        "id": "future_equipment",
        "requirements": {"equipment": ["Future equipment"]},
        "throughput_multiplier": 1.1,
        "capacity_modifier": 10,
    }]
    method["modifiers"] = raw
    profile = PlayerProfile(equipment={"Future equipment"})
    changed, applied = apply_modifiers(method, resolve_modifiers(method, profile))

    assert applied == ["future_equipment"]
    assert changed["cycles_per_hour"] == pytest.approx(110)
    assert changed["theoretical_cycles_per_hour"] == pytest.approx(132)
    assert changed["workflow"]["inventory_capacity"] == 38
