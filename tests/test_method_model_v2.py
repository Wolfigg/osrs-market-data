from pathlib import Path

from osrs_market.catalog_gap import build_catalog_gap_report
from osrs_market.catalog_wave4 import wave4_method_catalog
from osrs_market.config import load_yaml
from osrs_market.method_model import all_method_item_ids, effective_cycles_per_hour, iter_method_variants, output_quantity


def test_wave4_adds_broad_deterministic_and_stochastic_families():
    catalog = wave4_method_catalog()
    assert len(catalog) >= 20
    for method_id in (
        "tan_green_dragonhide",
        "grind_unicorn_horns",
        "make_headless_arrows",
        "make_rune_arrows",
        "spin_flax",
        "superglass_make_giant_seaweed",
        "cut_yew_logs_with_nests",
        "catch_raw_karambwan",
    ):
        assert method_id in catalog


def test_variant_item_ids_include_variant_only_runes():
    method = wave4_method_catalog()["spin_flax"]
    ids = all_method_item_ids(method)
    assert 1779 in ids
    assert 1777 in ids
    assert 561 in ids
    assert 9075 in ids
    variants = iter_method_variants("spin_flax", method)
    assert {method_id for method_id, _ in variants} == {"spin_flax__spinning_wheel", "spin_flax__lunar_spell"}


def test_workflow_caps_configured_cycles_per_hour():
    method = {
        "cycles_per_hour": 2000,
        "workflow": {"process_seconds": 1.0, "bank_seconds": 1.0, "travel_seconds": 1.0},
    }
    assert effective_cycles_per_hour(method) == 1200


def test_probabilistic_output_has_source_backed_expected_and_lower_bound_quantities():
    output = wave4_method_catalog()["superglass_make_giant_seaweed"]["outputs"][0]
    assert output_quantity(output, "expected") == 26.1
    assert output_quantity(output, "minimum") == 18.0
    assert output_quantity(output, "maximum") == 30.0


def test_untradeable_karambwanji_is_not_a_market_input():
    method = wave4_method_catalog()["catch_raw_karambwan"]
    assert method["inputs"] == []
    assert 3150 not in all_method_item_ids(method)
    assert "Self-supplied raw karambwanji bait" in method["requirements"]["supplies"]


def test_yew_nest_probability_uses_documented_standard_tree_roll():
    method = wave4_method_catalog()["cut_yew_logs_with_nests"]
    assert method["requirements"]["members"] is True
    nest = next(row for row in method["outputs"] if row["item_id"] == 5075)
    assert output_quantity(nest, "expected") == 1 / 256
    assert output_quantity(nest, "minimum") == 0


def test_merged_catalogue_exceeds_wave3_and_validates_richer_metadata():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    assert len(methods) >= 135
    assert methods["superglass_make_giant_seaweed"]["audit"]["status"] == "verified"
    assert "probabilistic" in methods["superglass_make_giant_seaweed"]["method_types"]
    assert "variants" in methods["spin_flax"]["method_types"]


def test_catalog_gap_report_finds_covered_and_remaining_families():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    report = build_catalog_gap_report(methods)
    assert report["catalogueMethodCount"] >= 135
    by_key = {row["key"]: row for row in report["families"]}
    assert by_key["tanning"]["status"] == "covered"
    assert by_key["superglass"]["status"] == "covered"
    assert by_key["enchant_jewellery"]["status"] == "missing"
    assert report["missingFamilyCount"] >= 1
