from pathlib import Path

from osrs_market.catalog_manifest import (
    compile_catalogue_manifest,
    compile_orb_charging,
    compile_potion_v2,
    compile_probabilistic_cooking,
    compile_teleport_tablets,
)
from osrs_market.catalog_wave5 import wave5_method_catalog
from osrs_market.catalog_wave6 import wave6_method_catalog
from osrs_market.config import load_yaml


def _base():
    methods = wave5_method_catalog()
    methods.update(wave6_method_catalog())
    return methods


def test_manifest_is_authoritative_for_wave8_data_families():
    effective, report = compile_catalogue_manifest(Path("catalogue/manifest.yml"), _base())
    assert report["catalogueVersion"] == 8
    assert report["familyCount"] == 6
    assert report["policy"]["sourceOfTruth"] == "data-first"
    owners = report["methodOwners"]
    for method_id in (
        "enchant_sapphire_ring",
        "charge_air_orb",
        "make_teleport_tablet_standard_varrock",
        "make_prayer_potions_v2",
        "cook_probabilistic_shark",
        "gather_fishing_tuna_swordfish",
    ):
        assert method_id in effective
        assert method_id in owners


def test_orb_data_preserves_route_contract():
    methods = compile_orb_charging("catalogue/magic/orbs.yml")
    water = methods["charge_water_orb"]
    assert water["cycles_per_hour"] == 505
    variants = {row["id"]: row for row in water["variants"]}
    assert set(variants) == {"agility_80", "agility_70", "no_shortcut"}
    assert variants["agility_80"]["overrides"]["requirements"]["agility"] == 80
    assert variants["no_shortcut"]["overrides"]["workflow"]["travel_seconds"] > variants["agility_80"]["overrides"]["workflow"]["travel_seconds"]


def test_tablet_data_covers_all_spellbook_families():
    methods = compile_teleport_tablets("catalogue/magic/tablets.yml")
    assert len(methods) == 38
    for method_id in (
        "make_teleport_tablet_standard_varrock",
        "make_teleport_tablet_ancient_ghorrock",
        "make_teleport_tablet_lunar_catherby",
        "make_teleport_tablet_arceuus_barrows",
    ):
        assert method_id in methods
    assert methods["make_teleport_tablet_standard_varrock"]["variants"][1]["id"] == "marble_lectern"
    assert methods["make_teleport_tablet_arceuus_barrows"]["model"]["unpricedInputs"]


def test_potion_data_compiles_independent_equipment_modifiers():
    methods = compile_potion_v2("catalogue/herblore/potions.yml")
    prayer = methods["make_prayer_potions_v2"]
    assert {row["id"] for row in prayer["modifiers"]} == {"prescription_goggles", "amulet_of_chemistry"}
    goggles = next(row for row in prayer["modifiers"] if row["id"] == "prescription_goggles")
    assert goggles["input_modifiers"][0]["expected_multiplier"] == 0.9
    chemistry = next(row for row in prayer["modifiers"] if row["id"] == "amulet_of_chemistry")
    assert chemistry["metadata"]["procChance"] == 0.05
    assert any(row["item_name"] == "Prayer potion(4)" for row in chemistry["added_items"])
    super_combat = methods["make_super_combat_potions_v2"]
    assert super_combat["modifiers"][0]["throughput_multiplier"] > 1


def test_cooking_curves_are_data_driven():
    methods = compile_probabilistic_cooking("catalogue/cooking/foods.yml")
    shark = methods["cook_probabilistic_shark"]
    cooking = shark["model"]["cooking"]
    assert cooking["minimumLevel"] == 80
    assert cooking["gauntletsAffected"] is True
    assert cooking["curves"]["range"] == {"low": 1.0, "high": 232.0}


def test_production_config_exposes_manifest_report_and_data_owned_methods():
    config = load_yaml("config/methods.yaml")
    report = config["catalogueManifest"]
    assert report["catalogueVersion"] == 8
    assert report["dataOwnedMethodCount"] >= 90
    methods = config["methods"]
    assert methods["charge_air_orb"]["source"]["verifiedAt"] == "2026-08-30"
    assert methods["make_prayer_potions_v2"]["model"]["modifierEngine"] == "v2"
    assert methods["cook_probabilistic_shark"]["source"]["verifiedAt"] == "2026-08-30"
