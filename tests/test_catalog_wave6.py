from pathlib import Path

from osrs_market.catalog_wave6 import wave6_method_catalog
from osrs_market.config import load_yaml
from osrs_market.methods_v2 import _generic_modifier_materialisations


def test_potion_catalogue_uses_independent_modifiers_not_manual_combo_variants():
    methods = wave6_method_catalog()
    potion = methods["make_prayer_potions_v2"]
    assert potion.get("variants") == []
    modifier_ids = [row["id"] for row in potion.get("modifiers") or []]
    assert modifier_ids == ["prescription_goggles", "amulet_of_chemistry"]
    assert "chemistry_and_goggles" not in modifier_ids

    rows = _generic_modifier_materialisations("make_prayer_potions_v2", potion)
    ids = [row_id for row_id, _ in rows]
    assert len(rows) == 4
    assert any("prescription_goggles_amulet_of_chemistry" in row_id for row_id in ids)
    combined = next(method for row_id, method in rows if "prescription_goggles_amulet_of_chemistry" in row_id)
    assert combined["model"]["appliedModifierIds"] == ["prescription_goggles", "amulet_of_chemistry"]
    assert "Prescription goggles" in combined["requirements"]["equipment"]
    assert "Amulet of chemistry" in combined["requirements"]["equipment"]


def test_production_config_applies_wave6_overrides():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    potion = methods["make_prayer_potions_v2"]
    assert potion.get("variants") == []
    assert [row["id"] for row in potion.get("modifiers") or []] == ["prescription_goggles", "amulet_of_chemistry"]
    assert methods["gather_fishing_swordfish"]["enabled"] is False
    assert methods["gather_fishing_tuna_swordfish"]["enabled"] is True


def test_tuna_swordfish_is_explicit_mixed_distribution():
    method = wave6_method_catalog()["gather_fishing_tuna_swordfish"]
    outputs = {row["item_name"]: row["quantity_expected"] for row in method["outputs"]}
    assert outputs == {"Raw tuna": 0.60, "Raw swordfish": 0.40}
    assert sum(outputs.values()) == 1.0
    assert method["cycles_per_hour"] == 195
    assert method["model"]["fishing"]["mixedCatch"] is True
