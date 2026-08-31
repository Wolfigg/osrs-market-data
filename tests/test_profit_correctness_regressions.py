from pathlib import Path

from osrs_market.config import load_yaml


def test_dragonstone_enchanting_uses_uncharged_outputs_and_manual_cast_ceiling():
    methods = load_yaml("config/methods.yaml")["methods"]
    expected = {
        "enchant_dragonstone_ring": "Ring of wealth",
        "enchant_dragonstone_necklace": "Skills necklace",
        "enchant_dragonstone_bracelet": "Combat bracelet",
        "enchant_dragonstone_amulet": "Amulet of glory",
    }
    for method_id, output in expected.items():
        method = methods[method_id]
        assert method["outputs"][0]["item_name"] == output
        assert method["cycles_per_hour"] == 1600
        assert method["theoretical_cycles_per_hour"] == 2000


def test_arceuus_tablets_cannot_be_ranked_as_zero_input_profit():
    methods = load_yaml("config/methods.yaml")["methods"]
    arceuus = [method for method_id, method in methods.items() if method_id.startswith("make_teleport_tablet_arceuus_")]
    assert len(arceuus) == 11
    assert all(method["enabled"] is False for method in arceuus)
    assert all((method.get("model") or {}).get("profitModelStatus") == "UNRESOLVED" for method in arceuus)
    assert all((method.get("model") or {}).get("unpricedInputs") for method in arceuus)


def test_account_profile_exposes_combination_staff_variants():
    profile = Path("web/assets/profile.js").read_text(encoding="utf-8")
    assert "Mud battlestaff or equivalent" in profile
    assert "Lava battlestaff or equivalent" in profile
    assert "Automatically use my best available variant" in profile


def test_planner_v3_removes_legacy_duplicate_session_calculations():
    planner = Path("web/assets/planner_v3.js").read_text(encoding="utf-8")
    assert "function removeLegacySessionCalculations" in planner
    assert "With your bankroll:" in planner
    assert "planner-v3-inline" in planner
