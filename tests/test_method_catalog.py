import json
from pathlib import Path

import pytest

from osrs_market.config import load_yaml
from osrs_market.public_models import build_public_afk


def test_full_catalog_has_structural_guards_and_verified_audit():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    assert len(methods) >= 60
    for method_id, method in methods.items():
        if method.get("enabled", True) is False:
            continue
        assert method["cycles_per_hour"] > 0, method_id
        assert method["afk"]["interval_seconds"] > 0, method_id
        assert method["outputs"] or method.get("shop_sales"), method_id
        assert method["method_types"], method_id
        assert method["reference"].startswith("https://oldschool.runescape.wiki/"), method_id
        assert method["audit"]["status"] == "verified", method_id
        assert method["audit"]["source"].startswith("https://oldschool.runescape.wiki/"), method_id
        assert isinstance(method["audit"]["verified_at"], str), method_id


def test_merged_catalog_is_strictly_json_serializable():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    encoded = json.dumps(methods, allow_nan=False)
    assert "steel_cannonballs_double_mould" in encoded


def test_audited_hand_tuned_methods_receive_provenance():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    cannonballs = methods["steel_cannonballs_double_mould"]
    assert cannonballs["audit"]["status"] == "verified"
    assert cannonballs["method_types"] == ["bankstanding", "make-x"]
    assert methods["mahogany_plank_make_afk"]["method_types"] == ["autocast", "bankstanding"]


def test_generated_catalog_types_come_from_semantics_not_copy_text():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    assert "gathering" in methods["gather_mining_amethyst"]["method_types"]
    assert methods["string_yew_longbows"]["method_types"] == ["bankstanding"]
    assert methods["fletch_magic_longbow_u"]["method_types"] == ["bankstanding", "make-x"]


def test_auxiliary_numeric_requirement_metadata_is_not_a_skill():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    sharks = methods["cook_sharks"]
    assert "minimum_cooking" not in sharks["requirements"]
    assert sharks["requirement_metadata"]["minimum_cooking"] == 80
    assert sharks["requirements"]["cooking"] == 99
    assert methods["cook_karambwan"]["requirements"]["quests"] == ["Tai Bwo Wannai Trio"]


def test_jewellery_membership_matches_current_f2p_access():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    for type_key in ("ring", "necklace", "amulet_u"):
        assert methods[f"craft_gold_{type_key}"]["requirements"]["members"] is False
        for gem in ("sapphire", "emerald", "ruby", "diamond"):
            assert methods[f"craft_{gem}_{type_key}"]["requirements"]["members"] is False
        assert methods[f"craft_dragonstone_{type_key}"]["requirements"]["members"] is True
    assert methods["craft_gold_bracelet"]["requirements"]["members"] is True
    for gem in ("sapphire", "emerald", "ruby", "diamond", "dragonstone"):
        assert methods[f"craft_{gem}_bracelet"]["requirements"]["members"] is True


def test_jewellery_and_battlestaff_throughput_matches_current_guidance():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    for type_key in ("ring", "necklace", "bracelet", "amulet_u"):
        assert methods[f"craft_gold_{type_key}"]["cycles_per_hour"] == 1400
        assert methods[f"craft_gold_{type_key}"]["theoretical_cycles_per_hour"] == 1600
        for gem in ("sapphire", "emerald", "ruby", "diamond", "dragonstone"):
            method = methods[f"craft_{gem}_{type_key}"]
            assert method["cycles_per_hour"] == 1400
            assert method["theoretical_cycles_per_hour"] == 1400
    for element in ("water", "earth", "fire", "air"):
        method = methods[f"craft_{element}_battlestaves"]
        assert method["cycles_per_hour"] == 2450
        assert method["theoretical_cycles_per_hour"] == 2625


def test_longbow_cooking_and_glass_intervals_match_make_x_mechanics():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    for wood in ("maple", "yew", "magic"):
        unstrung = methods[f"fletch_{wood}_longbow_u"]
        assert unstrung["cycles_per_hour"] == 1500
        assert unstrung["theoretical_cycles_per_hour"] == 1800
        assert unstrung["afk"]["interval_seconds"] == 48.6
        assert methods[f"string_{wood}_longbows"]["afk"]["interval_seconds"] == 16.8
    for food in ("karambwan", "sharks", "monkfish", "anglerfish", "dark_crabs"):
        cooking = methods[f"cook_{food}"]
        assert cooking["cycles_per_hour"] == 1300
        assert cooking["theoretical_cycles_per_hour"] == 1500
        assert cooking["afk"]["interval_seconds"] == 67.2
    assert methods["blow_unpowered_orbs"]["cycles_per_hour"] == 1600
    assert methods["blow_unpowered_orbs"]["theoretical_cycles_per_hour"] == 1750
    assert methods["blow_unpowered_orbs"]["afk"]["interval_seconds"] == 48.6


def test_onyx_bolt_tip_quantity_uses_24_tips_per_gem():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    onyx = methods["onyx_bolt_tips"]
    assert onyx["requirements"]["fletching"] == 73
    assert onyx["outputs"] == [{"item_id": 9194, "quantity": 24}]


def test_gathering_requirements_match_modelled_rate_gear_and_access():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    assert methods["cut_redwood_logs"]["requirements"]["equipment"] == ["Dragon axe"]
    assert methods["gather_magic_logs"]["requirements"]["equipment"] == ["Dragon or crystal axe"]
    camphor = methods["gather_camphor_logs"]["requirements"]
    assert camphor["woodcutting"] == 66
    assert camphor["sailing"] == 45
    assert camphor["quests"] == ["Troubled Tortugans (partial)"]
    assert camphor["equipment"] == ["Dragon axe", "Log basket"]
    assert methods["gather_fishing_dark_crabs"]["requirements"]["equipment"] == ["Lobster pot"]


def test_engorged_bloodwood_method_models_the_full_tradeable_arrow_batch():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    method = methods["gather_engorged_bloodwood_seeking_dragon_arrows"]
    assert method["cycles_per_hour"] == 16
    assert method["afk"]["interval_seconds"] == 118
    assert [(row.get("item_name"), row.get("item_id"), row["quantity"]) for row in method["inputs"]] == [
        ("Redwood logs", None, 1),
        ("Feather", None, 105),
        ("Dragon arrow", None, 105),
    ]
    assert method["outputs"] == [{"item_id": 33595, "quantity": 105}]
    assert method["requirements"]["woodcutting"] == 77
    assert method["requirements"]["fletching"] == 90
    assert method["requirements"]["quests"] == ["The Blood Moon Rises"]
    assert method["method_types"] == ["gathering", "make-x"]
    assert method["audit"]["verified_at"] == "2026-11-25"


def test_shop_hopping_catalogue_records_stock_costs_and_rate_limits():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    assert len([method for method in methods.values() if "shop-hopping" in method["method_types"]]) == 11
    mixed = methods["shop_hop_mixed_hide_bases"]
    assert mixed["cycles_per_hour"] * mixed["outputs"][0]["quantity"] == 1485
    assert mixed["shop_purchases"][0]["quantity"] * mixed["shop_purchases"][0]["gp_per_item"] * mixed["cycles_per_hour"] == 18803070
    for method_id in (
        "shop_hop_baba_yaga_astral_runes",
        "shop_hop_tal_teklan_cosmic_runes",
        "shop_hop_pellem_jaguar_fur",
        "shop_hop_fortis_jaguar_fur",
        "shop_hop_bandits_brew_big_heist_lodge",
        "shop_hop_limestone_razmire_builders",
        "shop_hop_spade_vanessa",
    ):
        method = methods[method_id]
        assert method["cycles_per_hour"] == pytest.approx(3600 / 7)
        assert "upper bound" in method["afk"]["description"].lower()
    warhammer = methods["shop_hop_rune_warhammer_skulgrimen"]
    assert warhammer["outputs"] == []
    assert warhammer["shop_sales"][0]["gp_per_item"] == 29050
    assert warhammer["inputs"][0]["item_id"] == warhammer["shop_sales"][0]["item_id"]
    assert warhammer["cycles_per_hour"] / warhammer["inputs"][0]["quantity"] > 70 / 4
    expected_shop_costs = {
        "shop_hop_baba_yaga_astral_runes": 13940,
        "shop_hop_tal_teklan_cosmic_runes": 1510,
        "shop_hop_pellem_jaguar_fur": 209,
        "shop_hop_fortis_jaguar_fur": 193,
        "shop_hop_bandits_brew_big_heist_lodge": 650,
        "shop_hop_limestone_razmire_builders": 10,
        "shop_hop_spade_vanessa": 3,
    }
    for method_id, expected in expected_shop_costs.items():
        method = methods[method_id]
        purchase = method["shop_purchases"][0]
        assert purchase["quantity"] * purchase["gp_per_item"] == pytest.approx(expected)


def test_fountain_recharge_routes_and_additional_processing_methods_are_audited():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    fountain_ids = [method_id for method_id in methods if method_id.startswith("fountain_recharge_")]
    assert len(fountain_ids) == 8
    for method_id in fountain_ids:
        method = methods[method_id]
        assert method["method_types"] == ["active-route"]
        assert method["inputs"][0]["quantity"] == 27
        assert method["inputs"][1] == {"item_id": 3016, "quantity": 1, "buy_via_ge": True}
        assert method["outputs"][0]["quantity"] == 27
        assert method["requirements"]["equipment"]
        assert "Wilderness death risk" in method["notes"]

    assert methods["fountain_recharge_glory_obelisk_route"]["outputs"][0]["item_id"] == 11978
    assert methods["fountain_recharge_combat_bracelet_obelisk_route"]["outputs"][0]["item_id"] == 11972
    assert methods["fountain_recharge_skills_necklace_obelisk_route"]["outputs"][0]["item_id"] == 11968
    assert methods["fountain_recharge_rings_of_wealth_obelisk_route"]["outputs"][0]["item_id"] == 11980
    assert methods["fountain_recharge_rings_of_wealth_obelisk_route"]["cycles_per_hour"] == 40
    assert methods["fountain_recharge_rings_of_wealth_wilderness_sword_4"]["cycles_per_hour"] == 60
    assert methods["fountain_recharge_rings_of_wealth_wilderness_sword_4"]["theoretical_cycles_per_hour"] == 72

    assert methods["make_pizza_bases"]["outputs"] == [
        {"item_id": 2283, "quantity": 1}, {"item_id": 1935, "quantity": 1}, {"item_id": 1931, "quantity": 1}
    ]
    assert methods["make_pastry_dough"]["cycles_per_hour"] == 2160
    assert methods["make_pastry_dough"]["theoretical_cycles_per_hour"] == 2400
    assert methods["make_pie_shells"]["inputs"][1]["item_id"] == 2313
    assert methods["cook_plain_pizzas"]["requirements"]["cooking"] == 68
    assert methods["grind_chocolate_bars"]["cycles_per_hour"] == 1800



def test_hunter_kit_outputs_tradeable_contents_with_correct_torch_id():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    output_ids = {item["item_id"] for item in methods["hunter_kit_opening"]["outputs"]}
    assert output_ids == {10150, 10010, 10006, 10031, 10093, 596, 11260, 10008}
    assert 598 not in output_ids

def _public_result(category: str, method_types: list[str]):
    return {
        "methodId": "test",
        "name": "Test method",
        "category": category,
        "methodTypes": method_types,
        "scenario": "CURRENT_INSTANT",
        "valid": True,
        "mechanics": {"cyclesPerHour": 100, "cyclesPerHourByBuyLimits": 100},
        "afk": {"intervalSeconds": 60, "gpPerInteractionWindow": 1000, "description": "No keyword dependence."},
        "economics": {
            "profitGpPerHourBuyLimitSustainable": 100_000,
            "profitGpPerCycle": 1000,
            "inputGpPerCycle": 0,
            "fixedCostGpPerCycle": 0,
            "totalCostGpPerCycle": 0,
            "outputGrossGeGpPerCycle": 1000,
            "geTaxGpPerCycle": 0,
            "outputNetGeGpPerCycle": 1000,
        },
        "inputs": [],
        "outputs": [{"itemId": 1, "name": "Output", "quantity": 1, "gePrice": 1000, "geTaxPerItem": 0, "geNetPerItem": 1000}],
        "liquidity": {"inputs": [], "outputs": [{"itemId": 1, "name": "Output", "observedVolume24h": 100000, "warnings": []}]},
        "requirements": {"members": True},
        "warnings": [],
    }


def test_public_category_normalises_generated_prefix_and_uses_explicit_tags():
    payload = build_public_afk(123, [_public_result("gathering/mining", ["gathering"])])
    row = payload["methods"][0]
    assert row["category"] == "Mining"
    assert "gathering" in row["tags"]
    assert "bankstanding" not in row["tags"]


def test_catalog_validation_rejects_invalid_override(tmp_path):
    config = tmp_path / "methods.yaml"
    config.write_text(
        "methods:\n  bad_method:\n    enabled: true\n    name: Bad\n    category: smithing\n    inputs: []\n    outputs: []\n    cycles_per_hour: 0\n    afk:\n      interval_seconds: 0\n    reference: https://example.com\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid method catalog"):
        load_yaml(config)
