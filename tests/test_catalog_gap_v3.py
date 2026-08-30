from osrs_market.catalog_gap_v3 import (
    CATALOGUE_SOURCE_STALE,
    GUIDE_CHANGED,
    RATE_CHANGE_SUSPECTED,
    RECIPE_CHANGE_SUSPECTED,
    REQUIREMENT_CHANGE_SUSPECTED,
    build_catalogue_impact_report,
)


def test_changed_guide_maps_to_methods_and_suspected_change_types():
    baseline = {"pages": [{"title": "Making unfinished potions", "revisionId": 123456, "url": "https://oldschool.runescape.wiki/w/Making_unfinished_potions"}]}
    discovered = [{"title": "Making unfinished potions", "revisionId": 124881, "url": "https://oldschool.runescape.wiki/w/Making_unfinished_potions"}]
    methods = {
        "make_ranarr_unf": {"reference": "https://oldschool.runescape.wiki/w/Making_unfinished_potions"},
        "other": {"reference": "https://oldschool.runescape.wiki/w/Cooking"},
    }
    report = build_catalogue_impact_report(
        discovered,
        baseline,
        methods,
        changed_sections={"Making unfinished potions": ["Requirements", "Products", "Profit"]},
    )

    finding = report["findings"][0]
    assert finding["status"] == GUIDE_CHANGED
    assert finding["potentiallyAffectedMethods"] == ["make_ranarr_unf"]
    assert CATALOGUE_SOURCE_STALE in finding["classifications"]
    assert RECIPE_CHANGE_SUSPECTED in finding["classifications"]
    assert RATE_CHANGE_SUSPECTED in finding["classifications"]
    assert REQUIREMENT_CHANGE_SUSPECTED in finding["classifications"]
    assert finding["priority"] == "HIGH"
    assert finding["reviewRequired"] is True
    assert finding["autoPromote"] is False
    assert report["trustWikiStructure"] is False
