from pathlib import Path

from osrs_market.catalog import generated_method_catalog
from osrs_market.catalog_expansion import expanded_method_catalog
from osrs_market.config import load_yaml


def test_generated_catalog_has_broad_method_coverage():
    catalog = generated_method_catalog()
    assert len(catalog) >= 50
    for method_id in (
        "opal_bolt_tips",
        "rune_dart_tips",
        "fletch_yew_longbow_u",
        "string_magic_longbows",
        "cook_anglerfish",
        "craft_diamond_bracelet",
        "blow_unpowered_orbs",
        "mine_amethyst",
        "cut_redwood_logs",
        "catch_dark_crabs",
    ):
        assert method_id in catalog


def test_expansion_has_deterministic_method_families():
    catalog = expanded_method_catalog()
    assert len(catalog) >= 30
    for method_id in (
        "oak_plank_make_afk",
        "teak_plank_make_afk",
        "cut_uncut_diamond",
        "blow_vials",
        "fletch_yew_shortbow_u",
        "string_magic_shortbows",
        "make_ranarr_unfinished_potion",
        "make_torstol_unfinished_potion",
    ):
        assert method_id in catalog


def test_methods_yaml_is_merged_over_all_generated_catalogues():
    payload = load_yaml(Path("config/methods.yaml"))
    methods = payload["methods"]
    assert len(methods) >= 90
    assert "steel_cannonballs_double_mould" in methods
    assert "opal_bolt_tips" in methods
    assert "oak_plank_make_afk" in methods
    assert "cut_uncut_sapphire" in methods
    assert "make_irit_unfinished_potion" in methods
    assert methods["steel_cannonballs_double_mould"]["cycles_per_hour"] == 1080
    assert methods["oak_plank_make_afk"]["fixed_cost_gp_per_cycle"] == 175
    assert methods["oak_plank_make_afk"]["audit"]["status"] == "verified"


def test_every_generated_method_has_market_inputs_or_outputs():
    for method_id, method in {**generated_method_catalog(), **expanded_method_catalog()}.items():
        assert method.get("inputs") or method.get("outputs"), method_id
        assert method["cycles_per_hour"] > 0, method_id
        assert method["afk"]["interval_seconds"] > 0, method_id
