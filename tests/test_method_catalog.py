from pathlib import Path

import pytest

from osrs_market.config import load_yaml
from osrs_market.public_models import build_public_afk


def test_full_catalog_has_structural_guards_and_explicit_types():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    assert len(methods) >= 60
    for method_id, method in methods.items():
        if method.get("enabled", True) is False:
            continue
        assert method["cycles_per_hour"] > 0, method_id
        assert method["afk"]["interval_seconds"] > 0, method_id
        assert method["outputs"], method_id
        assert method["method_types"], method_id
        assert method["reference"].startswith("https://oldschool.runescape.wiki/"), method_id


def test_audited_hand_tuned_methods_receive_provenance():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    cannonballs = methods["steel_cannonballs_double_mould"]
    assert cannonballs["audit"]["status"] == "verified"
    assert cannonballs["method_types"] == ["bankstanding", "make-x"]
    assert methods["mahogany_plank_make_afk"]["method_types"] == ["autocast", "bankstanding"]


def test_generated_catalog_types_come_from_semantics_not_copy_text():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    assert methods["mine_amethyst"]["method_types"] == ["gathering"]
    assert methods["string_yew_longbows"]["method_types"] == ["bankstanding"]
    assert methods["fletch_magic_longbow_u"]["method_types"] == ["bankstanding", "make-x"]


def test_auxiliary_numeric_requirement_metadata_is_not_a_skill():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    sharks = methods["cook_sharks"]
    assert "minimum_cooking" not in sharks["requirements"]
    assert sharks["requirement_metadata"]["minimum_cooking"] == 80
    assert sharks["requirements"]["cooking"] == 99


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


def test_onyx_bolt_tip_quantity_uses_24_tips_per_gem():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    onyx = methods["onyx_bolt_tips"]
    assert onyx["requirements"]["fletching"] == 73
    assert onyx["outputs"] == [{"item_id": 9194, "quantity": 24}]


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
        "economics": {"profitGpPerHourBuyLimitSustainable": 100_000, "inputGpPerCycle": 0},
        "inputs": [],
        "outputs": [{"name": "Output", "quantity": 1}],
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
