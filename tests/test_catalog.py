from pathlib import Path

from osrs_market.catalog import generated_method_catalog
from osrs_market.catalog_expansion import expanded_method_catalog
from osrs_market.config import load_yaml


def test_generated_catalog_has_broad_method_coverage():
    catalog = generated_method_catalog()
    assert len(catalog) >= 50
    for method_id in (
        "opal_bolt_tips", "rune_dart_tips", "fletch_yew_longbow_u",
        "string_magic_longbows", "cook_anglerfish", "craft_diamond_bracelet",
        "blow_unpowered_orbs", "mine_amethyst", "cut_redwood_logs", "catch_dark_crabs",
    ):
        assert method_id in catalog


def test_expansion_has_wave_three_method_families():
    catalog = expanded_method_catalog()
    assert len(catalog) >= 60
    for method_id in (
        "oak_plank_make_afk", "cut_uncut_diamond", "blow_vials",
        "fletch_yew_shortbow_u", "string_magic_shortbows",
        "fletch_willow_longbow_u", "string_oak_shortbows",
        "fletch_magic_arrow_shafts", "make_toadflax_unfinished_potion",
        "make_snapdragon_unfinished_potion", "make_lantadyme_unfinished_potion",
        "make_prayer_potions", "make_ranging_potions", "humidify_clay",
        "humidify_buckets", "smelt_bronze_bars", "smelt_silver_bars", "smelt_gold_bars",
    ):
        assert method_id in catalog


def test_shortbow_item_ids_are_correct():
    catalog = expanded_method_catalog()
    assert catalog["fletch_maple_shortbow_u"]["outputs"][0]["item_id"] == 64
    assert catalog["fletch_yew_shortbow_u"]["outputs"][0]["item_id"] == 68
    assert catalog["fletch_magic_shortbow_u"]["outputs"][0]["item_id"] == 72
    assert catalog["string_maple_shortbows"]["inputs"][0]["item_id"] == 64
    assert catalog["string_yew_shortbows"]["inputs"][0]["item_id"] == 68
    assert catalog["string_magic_shortbows"]["inputs"][0]["item_id"] == 72


def test_arrow_shaft_yields_scale_with_log_tier():
    catalog = expanded_method_catalog()
    assert catalog["fletch_logs_arrow_shafts"]["outputs"][0]["quantity"] == 15
    assert catalog["fletch_oak_arrow_shafts"]["outputs"][0]["quantity"] == 30
    assert catalog["fletch_magic_arrow_shafts"]["outputs"][0]["quantity"] == 90


def test_methods_yaml_is_merged_over_all_generated_catalogues():
    payload = load_yaml(Path("config/methods.yaml"))
    methods = payload["methods"]
    assert len(methods) >= 120
    assert "steel_cannonballs_double_mould" in methods
    assert "oak_plank_make_afk" in methods
    assert "humidify_clay" in methods
    assert "fletch_magic_arrow_shafts" in methods
    assert methods["steel_cannonballs_double_mould"]["cycles_per_hour"] == 1080
    assert methods["oak_plank_make_afk"]["fixed_cost_gp_per_cycle"] == 175
    assert methods["oak_plank_make_afk"]["audit"]["status"] == "verified"


def test_every_generated_method_has_market_inputs_or_outputs():
    for method_id, method in {**generated_method_catalog(), **expanded_method_catalog()}.items():
        assert method.get("inputs") or method.get("outputs"), method_id
        assert method["cycles_per_hour"] > 0, method_id
        assert method["afk"]["interval_seconds"] > 0, method_id
