from osrs_market.catalogue_intelligence import (
    REVIEW_REQUIRED,
    UNRESOLVED,
    apply_impact_to_assumptions,
    build_assumption_registry,
    build_catalogue_quality_report,
)
from osrs_market.catalog_gap_v3 import GUIDE_CHANGED, GUIDE_REMOVED, RATE_CHANGE_SUSPECTED, RECIPE_CHANGE_SUSPECTED


def method():
    return {
        "enabled": True,
        "name": "Test method",
        "inputs": [{"item_name": "Input", "quantity": 1}],
        "outputs": [{"item_name": "Output", "quantity": 1}],
        "cycles_per_hour": 100,
        "theoretical_cycles_per_hour": 120,
        "requirements": {"members": True, "cooking": 80},
        "model": {"gatheringV2": {"activityType": "fishing"}},
        "reference": "https://oldschool.runescape.wiki/w/Test_method",
        "audit": {"status": "verified", "verified_at": "2026-08-30", "source": "https://oldschool.runescape.wiki/w/Test_method"},
    }


def test_registry_has_stable_per_method_assumption_types_and_provenance():
    registry = build_assumption_registry({"test": method()})
    assert registry["methodCount"] == 1
    assert registry["assumptionCount"] == 4
    assert {row["kind"] for row in registry["assumptions"]} == {"recipe", "throughput", "requirements", "model"}
    assert registry["sourceCoveragePct"] == 100.0
    assert registry["verificationCoveragePct"] == 100.0
    assert all(len(row["fingerprint"]) == 16 for row in registry["assumptions"])


def test_changed_rate_marks_only_rate_and_model_assumptions_for_review():
    registry = build_assumption_registry({"test": method()})
    impact = {"findings": [{
        "guide": "Test method",
        "status": GUIDE_CHANGED,
        "classifications": [GUIDE_CHANGED, RATE_CHANGE_SUSPECTED],
        "potentiallyAffectedMethods": ["test"],
        "changedSections": ["Rates"],
    }]}
    drift = apply_impact_to_assumptions(registry, impact)
    status = {row["kind"]: row["status"] for row in drift["assumptions"]}
    assert status["throughput"] == REVIEW_REQUIRED
    assert status["model"] == REVIEW_REQUIRED
    assert status["recipe"] != REVIEW_REQUIRED
    assert status["requirements"] != REVIEW_REQUIRED
    assert drift["reviewRequired"] is True
    assert drift["autoPromote"] is False


def test_removed_source_marks_all_method_assumptions_unresolved():
    registry = build_assumption_registry({"test": method()})
    drift = apply_impact_to_assumptions(registry, {"findings": [{
        "guide": "Test method",
        "status": GUIDE_REMOVED,
        "classifications": [GUIDE_REMOVED],
        "potentiallyAffectedMethods": ["test"],
        "changedSections": [],
    }]})
    assert {row["status"] for row in drift["assumptions"]} == {UNRESOLVED}


def test_quality_report_does_not_equate_catalogue_coverage_with_model_quality():
    methods = {"test": method(), "plain": {**method(), "model": {}, "variants": []}}
    registry = build_assumption_registry(methods)
    quality = build_catalogue_quality_report(methods, registry)
    assert quality["methodCount"] == 2
    assert quality["modelledMethodPct"] == 50.0
    assert quality["coverageIsNotQuality"] is True
