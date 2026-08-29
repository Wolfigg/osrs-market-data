import json

import pytest

from osrs_market.public_models import PUBLIC_SCHEMA_VERSION, build_dashboard, build_public_afk, build_public_alchemy, build_public_status, classify_afk
from osrs_market.public_site import validate_public_site, write_public_site


def _afk_result(scenario="CURRENT_INSTANT", valid=True, gp=100_000, warnings=None):
    return {
        "methodId": "ruby_bolt_tips",
        "name": "Cut ruby bolt tips",
        "category": "fletching",
        "scenario": scenario,
        "valid": valid,
        "mechanics": {"cyclesPerHour": 1000, "cyclesPerHourByBuyLimits": 900},
        "afk": {"intervalSeconds": 81, "gpPerInteractionWindow": 2200, "description": "Use Make-X at a bank."},
        "economics": {"profitGpPerHourBuyLimitSustainable": gp, "inputGpPerCycle": 1000},
        "inputs": [{"name": "Ruby", "quantity": 1}],
        "outputs": [{"name": "Ruby bolt tips", "quantity": 12}],
        "requirements": {"members": True, "fletching": 63, "equipment": ["Chisel"]},
        "warnings": warnings or [],
        "reference": "https://oldschool.runescape.wiki/w/Ruby_bolt_tips",
    }


def _candidate(valid=True):
    return {
        "itemId": 1,
        "name": "Test item",
        "members": False,
        "highAlchValue": 2000,
        "geBuyLimit": 100,
        "buyPriceAgeSeconds": 60,
        "currentInstant": {"valid": valid, "buyPrice": 1000, "natureRunePrice": 100, "fireRunePrice": None, "profitPerCast": 900 if valid else None, "roiPct": 81.8 if valid else None},
        "historicalInstant24h": {"valid": True, "profitPerCast": 800},
        "capacity4h": {"maxQuantity": 100},
        "profitPer4hGeLimit": 90_000 if valid else None,
        "capitalRequired": 110_000 if valid else None,
        "volume24h": 10_000,
        "warnings": [],
    }


def test_afk_classification_boundaries():
    assert classify_afk(30) == "Light AFK"
    assert classify_afk(45) == "AFK"
    assert classify_afk(90) == "Very AFK"
    assert classify_afk(180) == "Deep AFK"


def test_public_afk_contains_curated_fields_and_history():
    rows = [_afk_result()]
    for scenario, gp in [("HISTORICAL_INSTANT_6H", 90_000), ("HISTORICAL_INSTANT_24H", 80_000), ("HISTORICAL_INSTANT_7D", 70_000), ("HISTORICAL_INSTANT_30D", 60_000)]:
        rows.append(_afk_result(scenario=scenario, gp=gp))
    payload = build_public_afk(123, rows)
    method = payload["methods"][0]
    assert payload["schemaVersion"] == PUBLIC_SCHEMA_VERSION
    assert method["history"]["24hGpPerHour"] == 80_000
    assert method["economics"]["capitalOneHour"] == 900_000
    assert "warnings" not in method
    assert "scenario" not in method


def test_unavailable_alchemy_never_emits_numeric_profit():
    payload = build_public_alchemy(123, [_candidate(valid=False)], {"castsPerHour": 1200, "useFireStaff": True})
    item = payload["items"][0]
    assert item["profitPerCast"] is None
    assert item["profit4h"] is None
    assert item["capitalRequired"] is None
    assert item["risk"]["level"] == "unavailable"


def test_dashboard_handles_empty_and_populated_data():
    empty = build_dashboard(123, {"methods": []}, {"items": []})
    assert empty["featuredAfk"] is None
    assert empty["featuredAlchemy"] is None
    afk = build_public_afk(123, [_afk_result()])
    alch = build_public_alchemy(123, [_candidate()], {"castsPerHour": 1200, "useFireStaff": True})
    populated = build_dashboard(123, afk, alch)
    assert populated["featuredAfk"]["methodId"] == "ruby_bolt_tips"
    assert populated["featuredAlchemy"]["itemId"] == 1


def test_status_hides_internal_health_details():
    payload = build_public_status(123, {"status": "degraded", "api": {"timeseriesFailed": 2}, "warnings": ["SECRET_CODE"]})
    assert payload == {"schemaVersion": 1, "generatedAt": 123, "state": "delayed", "ageSeconds": 0}


def test_public_site_generation_and_sanitization(tmp_path):
    assets = tmp_path / "assets-source"
    assets.mkdir()
    (assets / "app.css").write_text("body{}", encoding="utf-8")
    (assets / "app.js").write_text("void 0;", encoding="utf-8")
    afk = build_public_afk(123, [_afk_result()])
    alch = build_public_alchemy(123, [_candidate()], {"castsPerHour": 1200, "useFireStaff": True})
    site = tmp_path / "site"
    write_public_site(site, build_dashboard(123, afk, alch), afk, alch, build_public_status(123, {"status": "ok", "api": {"timeseriesFailed": 0}, "warnings": []}), assets)
    validate_public_site(site)
    assert (site / "afk.html").is_file()
    assert (site / "alchemy.html").is_file()
    assert not (site / "market").exists()
    assert "Market Explorer" not in (site / "index.html").read_text(encoding="utf-8")


def test_sanitizer_rejects_internal_key(tmp_path):
    site = tmp_path / "site"
    (site / "assets").mkdir(parents=True)
    (site / "data").mkdir()
    for page in ("index.html", "afk.html", "alchemy.html", "about.html"):
        (site / page).write_text("ok", encoding="utf-8")
    (site / "assets" / "app.css").write_text("", encoding="utf-8")
    (site / "assets" / "app.js").write_text("", encoding="utf-8")
    base = {"schemaVersion": 1, "generatedAt": 123}
    (site / "data" / "dashboard.json").write_text(json.dumps({**base, "series": []}), encoding="utf-8")
    (site / "data" / "afk.json").write_text(json.dumps({**base, "methods": []}), encoding="utf-8")
    (site / "data" / "alchemy.json").write_text(json.dumps({**base, "items": []}), encoding="utf-8")
    (site / "data" / "status.json").write_text(json.dumps({**base, "state": "current"}), encoding="utf-8")
    with pytest.raises(ValueError, match="internal fields leaked"):
        validate_public_site(site)
