from pathlib import Path

from osrs_market.catalog_gap import build_catalog_gap_report
from osrs_market.catalog_wave5 import wave5_method_catalog
from osrs_market.config import load_yaml
from osrs_market.method_model import input_quantity, iter_method_variants
from osrs_market.methods_v2 import cooking_success_probability
from osrs_market.wiki_discovery import build_discovery_audit


def test_wave5_adds_requested_catalogue_families():
    catalog = wave5_method_catalog()
    assert len(catalog) >= 115
    for method_id in ("enchant_sapphire_ring", "enchant_zenyte_amulet", "charge_water_orb", "charge_air_orb", "make_teleport_tablet_standard_varrock", "make_teleport_tablet_ancient_ghorrock", "make_teleport_tablet_lunar_catherby", "make_teleport_tablet_arceuus_barrows", "make_prayer_potions_v2", "make_super_combat_potions_v2", "cook_probabilistic_shark", "gather_yew_logs", "gather_magic_logs", "gather_teak_logs", "gather_mahogany_logs", "gather_camphor_logs", "gather_mining_amethyst", "gather_fishing_anglerfish"):
        assert method_id in catalog


def test_jewellery_family_covers_all_gems_and_shapes():
    catalog = wave5_method_catalog()
    for gem in ("sapphire", "emerald", "ruby", "diamond", "dragonstone", "onyx", "zenyte"):
        for shape in ("ring", "necklace", "bracelet", "amulet"): assert f"enchant_{gem}_{shape}" in catalog


def test_orb_routes_are_explicit_variants():
    catalog = wave5_method_catalog()
    water = {method_id for method_id, _ in iter_method_variants("charge_water_orb", catalog["charge_water_orb"])}
    air = {method_id for method_id, _ in iter_method_variants("charge_air_orb", catalog["charge_air_orb"])}
    assert water == {"charge_water_orb__agility_80", "charge_water_orb__agility_70", "charge_water_orb__no_shortcut"}
    assert air == {"charge_air_orb__edgeville_energy", "charge_air_orb__poh_pool"}


def test_prescription_goggles_expected_and_conservative_consumption():
    variants = dict(iter_method_variants("make_prayer_potions_v2", wave5_method_catalog()["make_prayer_potions_v2"]))
    secondary = variants["make_prayer_potions_v2__prescription_goggles"]["inputs"][1]
    assert input_quantity(secondary, "expected") == 0.9
    assert input_quantity(secondary, "minimum") == 1.0


def test_chemistry_models_true_three_and_four_dose_mix():
    variants = dict(iter_method_variants("make_prayer_potions_v2", wave5_method_catalog()["make_prayer_potions_v2"]))
    chemistry = variants["make_prayer_potions_v2__amulet_of_chemistry"]
    assert chemistry["outputs"][0]["quantity_expected"] == 0.95
    assert chemistry["outputs"][1]["quantity_expected"] == 0.05
    assert chemistry["model"]["doseModel"]["chemistryProcChance"] == 0.05


def test_cooking_probability_respects_level_location_gauntlets_and_cape():
    profile = wave5_method_catalog()["cook_probabilistic_shark"]["model"]["cooking"]
    normal_80 = cooking_success_probability(profile, 80, "range", False, False)
    assert cooking_success_probability(profile, 80, "range", True, False) > normal_80
    assert cooking_success_probability(profile, 80, "hosidius_10", False, False) > normal_80
    assert cooking_success_probability(profile, 99, "range", False, True) == 1.0


def test_gathering_only_values_defensible_nest_roll():
    method = wave5_method_catalog()["gather_yew_logs"]
    assert method["outputs"][0]["quantity_expected"] == 255 / 256
    assert method["outputs"][1]["quantity_expected"] == 1 / 256
    assert "Clue nest contents" in method["model"]["excludedExpectedOutputs"]


def test_catalog_gap_v2_reports_requested_families_covered():
    report = build_catalog_gap_report(load_yaml(Path("config/methods.yaml"))["methods"])
    assert report["schemaVersion"] == 2
    by_key = {row["key"]: row for row in report["families"]}
    for key in ("enchant_jewellery", "teleport_tablets", "orb_charging", "potion_v2", "cooking_burns", "more_gathering", "forestry_outputs"): assert by_key[key]["status"] == "covered"


def test_wiki_discovery_is_review_only_and_flags_revision_changes():
    baseline = {"pages": [{"pageId": 1, "title": "Money making guide/Test", "revisionId": 10, "url": "old"}]}
    discovered = [{"pageId": 1, "title": "Money making guide/Test", "revisionId": 11, "revisionTimestamp": "2026-08-29T00:00:00Z", "url": "new"}, {"pageId": 2, "title": "Money making guide/New", "revisionId": 1, "revisionTimestamp": "2026-08-29T00:00:00Z", "url": "new"}]
    audit = build_discovery_audit(discovered, baseline)
    assert audit["requiresReview"] is True
    assert {row["status"] for row in audit["findings"]} == {"changed", "new"}
    assert "advisory only" in audit["trustPolicy"]
