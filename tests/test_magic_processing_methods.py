from pathlib import Path

from osrs_market.config import load_yaml
from osrs_market.public_models import _requirements, classify_afk


def test_plank_make_catalogue_covers_all_supported_log_tiers():
    methods = load_yaml("config/methods.yaml")["methods"]
    audit = load_yaml("config/method_audit.yaml")["methods"]
    tiers = {
        "logs": (1511, 960, 70),
        "oak": (1521, 8778, 175),
        "teak": (6333, 8780, 350),
        "mahogany": (6332, 8782, 1050),
        "camphor": (32904, 31432, 1750),
        "ironwood": (32907, 31435, 3500),
        "rosewood": (32910, 31438, 5250),
    }

    for tier, (log_id, plank_id, fee) in tiers.items():
        method = methods[f"{tier}_plank_make_afk"]
        assert [(row["item_id"], row["quantity"]) for row in method["inputs"]] == [
            (log_id, 1),
            (561, 1),
            (9075, 2),
        ]
        assert method["outputs"] == [{"item_id": plank_id, "quantity": 1}]
        assert method["fixed_cost_gp_per_cycle"] == fee
        assert method["cycles_per_hour"] == 833
        assert method["theoretical_cycles_per_hour"] == 1000
        assert method["afk"]["interval_seconds"] == 90
        assert method["requirements"]["magic"] == 86
        assert method["requirements"]["quests"] == ["Dream Mentor"]
        assert method["requirements"]["equipment"] == ["Earth-rune supplying staff"]
        assert method["method_types"] == ["autocast", "bankstanding"]
        assert method["reference"] == "https://oldschool.runescape.wiki/w/Plank_Make"
        audit_entry = audit[f"{tier}_plank_make_afk"]
        assert audit_entry["status"] == "verified"
        assert audit_entry["verified_at"] == "2026-11-25"
        assert audit_entry["checks"]["input_units_per_cycle"] == 4
        assert audit_entry["checks"]["output_units_per_cycle"] == 1
        assert audit_entry["checks"]["fixed_cost_gp_per_cycle"] == fee


def test_recharge_dragonstone_methods_charge_full_inventory_with_correct_requirements():
    methods = load_yaml("config/methods.yaml")["methods"]
    audit = load_yaml("config/method_audit.yaml")["methods"]
    outputs = {
        "amulet_glory": (1704, 1712, []),
        "combat_bracelet": (11126, 11118, ["Legends' Quest"]),
        "skills_necklace": (11113, 11105, ["Legends' Quest"]),
    }

    for suffix, (input_id, output_id, extra_quests) in outputs.items():
        method = methods[f"recharge_dragonstone_{suffix}"]
        assert [(row["item_id"], row["quantity"]) for row in method["inputs"]] == [
            (input_id, 26),
            (9075, 1),
            (566, 1),
        ]
        assert method["outputs"] == [{"item_id": output_id, "quantity": 26}]
        assert method["cycles_per_hour"] == 360
        assert method["theoretical_cycles_per_hour"] == 360
        assert 35_100 / 97.5 == method["cycles_per_hour"]
        assert method["afk"]["interval_seconds"] == 10
        assert classify_afk(method["afk"]["interval_seconds"]) == "Low interaction"
        assert method["requirements"]["magic"] == 89
        assert method["requirements"]["quests"] == ["Lunar Diplomacy", *extra_quests]
        assert method["requirements"]["diaries"] == ["Hard Fremennik Diary"]
        assert method["requirements"]["equipment"] == ["Water-rune supplying staff"]
        assert method["method_types"] == ["bankstanding"]
        audit_entry = audit[f"recharge_dragonstone_{suffix}"]
        assert audit_entry["status"] == "verified"
        assert audit_entry["method_types"] == ["bankstanding"]
        assert audit_entry["checks"]["input_units_per_cycle"] == 28
        assert audit_entry["checks"]["output_units_per_cycle"] == 26
        assert method["reference"] == "https://oldschool.runescape.wiki/w/Recharge_Dragonstone"


def test_public_requirements_preserve_diaries_and_unlocks():
    requirements = _requirements(
        {
            "requirements": {
                "magic": 89,
                "quests": ["Lunar Diplomacy"],
                "diaries": ["Hard Fremennik Diary"],
                "unlocks": ["Lunar spellbook"],
                "equipment": ["Water-rune supplying staff"],
            }
        }
    )

    assert requirements == {
        "skills": {"magic": 89},
        "quests": ["Lunar Diplomacy"],
        "equipment": ["Water-rune supplying staff"],
        "diaries": ["Hard Fremennik Diary"],
        "unlocks": ["Lunar spellbook"],
    }

    app = Path("web/assets/app.js").read_text(encoding="utf-8")
    assert "r?.diaries" in app and "<h3>Diaries</h3>" in app
    assert "r?.unlocks" in app and "<h3>Unlocks</h3>" in app

