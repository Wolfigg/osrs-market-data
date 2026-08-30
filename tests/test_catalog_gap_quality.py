from osrs_market.catalog_gap import build_catalog_gap_report


def test_gap_report_separates_family_coverage_from_model_quality():
    methods = {
        "enchant_test": {
            "enabled": True,
            "reference": "https://oldschool.runescape.wiki/w/Enchanting",
            "inputs": [{"item_name": "A", "quantity": 1}],
            "outputs": [{"item_name": "B", "quantity": 1}],
            "cycles_per_hour": 100,
            "requirements": {"magic": 7},
            "audit": {"status": "verified", "verified_at": "2026-08-30", "source": "https://oldschool.runescape.wiki/w/Enchanting"},
        }
    }
    report = build_catalog_gap_report(methods)
    assert report["schemaVersion"] == 3
    assert "coveragePct" in report
    assert report["modelQuality"]["methodCount"] == 1
    assert report["modelQuality"]["modelledMethodPct"] == 0.0
    assert report["modelQuality"]["coverageIsNotQuality"] is True
    assert "does not assert" in report["coverageInterpretation"]
