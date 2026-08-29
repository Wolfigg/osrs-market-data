from datetime import date
from pathlib import Path

from osrs_market.assumption_audit import build_assumption_audit
from osrs_market.catalog_health import build_catalog_health
from osrs_market.catalog_wave6 import wave6_method_catalog
from osrs_market.config import load_yaml
from osrs_market.decision_engine import optimise_session
from osrs_market.requirements import evaluate_requirements, normalise_requirements
from osrs_market.route_engine import evaluate_route
from osrs_market.wave6 import apply_account_profile, throughput_distribution


def test_structured_requirements_support_legacy_and_account_eligibility():
    raw = {"members": True, "magic": 66, "agility": 70, "quests": ["Quest A"], "equipment": ["Dust battlestaff"]}
    structured = normalise_requirements(raw)
    assert structured["skills"] == {"agility": 70, "magic": 66}
    blocked = evaluate_requirements(raw, {"members": True, "skills": {"magic": 70, "agility": 65}, "quests": ["Quest A"], "equipment": ["Dust battlestaff"]})
    assert blocked["status"] == "blocked"
    assert blocked["missing"][0]["skill"] == "agility"
    eligible = evaluate_requirements(raw, {"members": True, "skills": {"magic": 70, "agility": 75}, "quests": ["Quest A"], "equipment": ["Dust battlestaff"]})
    assert eligible["eligible"] is True


def test_incomplete_account_profile_is_unknown_not_blocked():
    result = evaluate_requirements({"members": True, "cooking": 80, "equipment": ["Cooking gauntlets"]}, {"skills": {"cooking": 90}})
    assert result["status"] == "unknown"
    assert result["blocked"] is False


def test_route_engine_calculates_trip_rate_cost_and_variance():
    result = evaluate_route({"id": "test", "items_per_trip": 26, "steps": [{"kind": "bank", "seconds": 12, "variance_seconds": 2}, {"kind": "walk", "seconds": 100, "variance_seconds": 8}, {"kind": "production", "seconds": 48, "variance_seconds": 2, "cost_gp": 260}]})
    assert result is not None
    assert result["tripSeconds"] == 160
    assert round(result["tripsPerHour"], 2) == 22.5
    assert result["itemsPerHour"] == 585
    assert result["movementCostGpPerTrip"] == 260
    assert result["tripStdDevSeconds"] > 8


def test_wave6_gathering_has_mixed_fishing_and_throughput_quantiles():
    catalogue = wave6_method_catalog()
    mixed = catalogue["fishing_v2_tuna_swordfish"]
    assert len(mixed["outputs"]) == 2
    assert sum(row["quantity_expected"] for row in mixed["outputs"]) == 1
    distribution = throughput_distribution(mixed)
    assert distribution["p10"] < distribution["p50"] < distribution["p90"]
    assert {variant["id"] for variant in mixed["variants"]} == {"standard", "dragon_harpoon", "crystal_harpoon"}


def test_account_profile_replaces_cooking_defaults_and_reports_eligibility():
    method = {
        "cycles_per_hour": 1000,
        "theoretical_cycles_per_hour": 1200,
        "requirements": {"members": True, "cooking": 80},
        "reference": "https://oldschool.runescape.wiki/w/Cooking",
        "model": {"cooking": {"defaults": {"level": 99, "location": "range", "gauntlets": False, "cookingCape": True}}},
    }
    personalised = apply_account_profile(method, {"members": True, "skills": {"cooking": 85}, "cooking": {"location": "hosidius_10", "gauntlets": True, "cookingCape": False}})
    defaults = personalised["model"]["cooking"]["defaults"]
    assert defaults == {"level": 85, "location": "hosidius_10", "gauntlets": True, "cookingCape": False}
    assert personalised["eligibility"]["eligible"] is True


def test_assumption_audit_flags_material_drift():
    audit = build_assumption_audit("charge_air_orb", [{"key": "magic_requirement", "value": 66}, {"key": "rate", "value": 2500}], [{"key": "magic_requirement", "value": 66}, {"key": "rate", "value": 2200, "sourceRevision": 123}])
    assert audit["status"] == "REVIEW_REQUIRED"
    rate = next(row for row in audit["findings"] if row["key"] == "rate")
    assert round(rate["differencePct"]) == -12


def test_catalogue_health_surfaces_missing_wave6_metadata():
    methods = {
        "good": {"outputs": [{"item_id": 1, "quantity": 1}], "requirements": {"members": False}, "audit": {"status": "verified", "verified_at": "2026-08-30"}, "provenance": {"assumptions": []}, "throughput": {"quantiles": {"p50": 100}}},
        "old": {"outputs": [{"item_name": "Thing", "quantity": 1}], "requirements": {}, "audit": {"status": "review", "verified_at": "2025-01-01"}},
    }
    health = build_catalog_health(methods, today=date(2026, 8, 30), stale_days=90)
    assert health["summary"]["methods"] == 2
    assert health["summary"]["needsReview"] == 1
    assert health["summary"]["staleAssumptions"] == 1
    assert health["summary"]["methodsWithoutProvenance"] == 1


def test_session_optimizer_respects_bankroll_and_intensity():
    methods = [
        {"methodId": "a", "name": "A", "current": {"valid": True}, "scenarios": {"expectedGpPerHour": 1_000_000}, "economics": {"capitalOneHour": 5_000_000}, "mechanics": {"cyclesPerHour": 100, "cyclesPerHourByBuyLimits": 100}, "fillConfidence": {"turnoverHours": .5, "score": 90}, "afk": {"intensity": "low"}},
        {"methodId": "b", "name": "B", "current": {"valid": True}, "scenarios": {"expectedGpPerHour": 700_000}, "economics": {"capitalOneHour": 1_000_000}, "mechanics": {"cyclesPerHour": 100, "cyclesPerHourByBuyLimits": 100}, "fillConfidence": {"turnoverHours": 1, "score": 80}, "afk": {"intensity": "low"}},
        {"methodId": "c", "name": "C", "current": {"valid": True}, "scenarios": {"expectedGpPerHour": 2_000_000}, "economics": {"capitalOneHour": 500_000}, "mechanics": {"cyclesPerHour": 100, "cyclesPerHourByBuyLimits": 100}, "fillConfidence": {"turnoverHours": 1, "score": 90}, "afk": {"intensity": "high"}},
    ]
    plan = optimise_session(methods, bankroll=2_000_000, hours=3, maximum_intensity="low")
    assert plan["plannedHours"] == 3
    assert plan["blocks"][0]["methodId"] == "b"
    assert all(block["methodId"] != "c" for block in plan["blocks"])


def test_production_catalogue_loads_wave6_methods():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    for method_id in ("fishing_v2_tuna_swordfish", "fishing_v2_anglerfish", "mining_v2_amethyst", "mining_v2_motherlode", "woodcutting_v2_camphor"):
        assert method_id in methods
        assert methods[method_id]["audit"]["status"] == "verified"
