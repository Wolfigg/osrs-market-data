import json

import pytest

from osrs_market.public_models import PUBLIC_SCHEMA_VERSION, build_public_afk, build_public_alchemy, build_public_status, classify_afk, public_risk
from osrs_market.public_site import validate_public_site, write_public_site


def _afk_result(scenario="CURRENT_INSTANT", valid=True, gp=100_000, warnings=None, fixed_cost=0, volume=100_000):
    return {
        "methodId": "ruby_bolt_tips",
        "name": "Cut ruby bolt tips",
        "category": "fletching",
        "methodTypes": ["bankstanding", "make-x"],
        "scenario": scenario,
        "valid": valid,
        "mechanics": {"cyclesPerHour": 1000, "cyclesPerHourByBuyLimits": 900},
        "afk": {"intervalSeconds": 81, "gpPerInteractionWindow": 2200, "description": "Use Make-X at a bank."},
        "economics": {
            "profitGpPerHourBuyLimitSustainable": gp,
            "profitGpPerCycle": gp / 900 if valid else None,
            "inputGpPerCycle": 1000,
            "fixedCostGpPerCycle": fixed_cost,
            "totalCostGpPerCycle": 1000 + fixed_cost,
            "outputGrossGeGpPerCycle": 1200,
            "geTaxGpPerCycle": 12,
            "outputNetGeGpPerCycle": 1188,
        },
        "inputs": [{"itemId": 1603, "name": "Ruby", "quantity": 1, "price": 1000, "subtotal": 1000, "buyViaGe": True, "geBuyLimit": 11000, "maxCyclesPerHourByLimit": 2750}],
        "outputs": [{"itemId": 9191, "name": "Ruby bolt tips", "quantity": 12, "gePrice": 100, "geTaxPerItem": 1, "geNetPerItem": 99}],
        "liquidity": {
            "plannedHoursPerDay": 1,
            "inputs": [{"itemId": 1603, "name": "Ruby", "observedVolume24h": volume, "observedHighVolume24h": volume * 0.6, "observedLowVolume24h": volume * 0.4, "warnings": []}],
            "outputs": [{"itemId": 9191, "name": "Ruby bolt tips", "observedVolume24h": volume * 12, "observedHighVolume24h": volume * 5, "observedLowVolume24h": volume * 7, "warnings": []}],
        },
        "requirements": {"members": True, "fletching": 63, "equipment": ["Chisel"]},
        "warnings": warnings or [],
        "reference": "https://oldschool.runescape.wiki/w/Ruby_bolt_tips",
    }


def _candidate(valid=True):
    return {
        "itemId": 1, "name": "Test item", "members": False, "highAlchValue": 2000, "geBuyLimit": 100, "buyPriceAgeSeconds": 60,
        "currentInstant": {"valid": valid, "buyPrice": 1000, "natureRunePrice": 100, "fireRunePrice": None, "profitPerCast": 900 if valid else None, "roiPct": 81.8 if valid else None},
        "historicalInstant24h": {"valid": True, "profitPerCast": 800}, "historicalInstant7d": {"valid": True, "profitPerCast": 750}, "historicalInstant30d": {"valid": True, "profitPerCast": 700},
        "capacity4h": {"maxQuantity": 100}, "profitPer4hGeLimit": 90_000 if valid else None, "capitalRequired": 110_000 if valid else None, "volume24h": 10_000, "warnings": [],
    }


def _write_test_assets(assets):
    for name in ("app.css", "app.js", "enhancements.js", "planner_v3.js", "cooking_math.js", "profile.js"):
        (assets / name).write_text("void 0;", encoding="utf-8")


def test_afk_classification_boundaries():
    assert classify_afk(29.9) == "Low interaction"
    assert classify_afk(30) == "Light AFK"
    assert classify_afk(45) == "AFK"
    assert classify_afk(90) == "Very AFK"
    assert classify_afk(180) == "Deep AFK"


def test_public_afk_contains_history_scenarios_confidence_and_breakdown():
    rows = [_afk_result()]
    for scenario, gp in [("HISTORICAL_INSTANT_6H", 90_000), ("HISTORICAL_INSTANT_24H", 80_000), ("HISTORICAL_INSTANT_7D", 70_000), ("HISTORICAL_INSTANT_30D", 60_000)]:
        rows.append(_afk_result(scenario=scenario, gp=gp))
    method = build_public_afk(123, rows)["methods"][0]
    assert method["history"]["24hGpPerHour"] == 80_000
    assert method["recommended"]["gpPerHour"] is not None
    assert method["scenarios"]["currentGpPerHour"] == 100_000
    assert method["scenarios"]["expectedGpPerHour"] == method["recommended"]["gpPerHour"]
    assert method["scenarios"]["conservativeGpPerHour"] == 60_000
    assert method["economics"]["capitalOneHour"] == 900_000
    assert method["economics"]["capitalPerCycle"] == 1000
    assert method["economics"]["inputGpPerCycle"] == 1000
    assert method["economics"]["outputNetGpPerCycle"] == 1188
    assert method["inputs"][0]["price"] == 1000
    assert method["outputs"][0]["geTaxPerItem"] == 1
    assert method["mechanics"] == {"cyclesPerHour": 1000.0, "cyclesPerHourByBuyLimits": 900.0}
    assert method["liquidity"]["inputs"][0]["unitsPerHour"] == 1000
    assert method["liquidity"]["inputs"][0]["oneHourSharePct24h"] == 1.0
    assert method["liquidity"]["inputs"][0]["directionalVolume24h"] == 60_000
    assert method["liquidity"]["outputs"][0]["directionalVolume24h"] == 700_000
    assert method["fillConfidence"]["score"] is not None
    assert method["fillConfidence"]["turnoverHours"] > 0
    assert method["priceSource"]["provider"] == "OSRS Wiki Prices / RuneLite"
    assert method["sustainability"]["state"] == "moderate"
    assert method["sustainability"]["throughputRatioPct"] == 90.0
    assert "warnings" not in method
    assert "scenario" not in method


def test_directional_fill_confidence_penalises_required_side_pressure():
    liquid = build_public_afk(123, [_afk_result(volume=1_000_000)])["methods"][0]
    thin = build_public_afk(123, [_afk_result(volume=8_000)])["methods"][0]
    assert liquid["fillConfidence"]["score"] > thin["fillConfidence"]["score"]
    assert thin["fillConfidence"]["turnoverHours"] >= liquid["fillConfidence"]["turnoverHours"]


def test_sustainability_marks_thin_market_and_ge_limited_methods():
    thin = build_public_afk(123, [_afk_result(volume=8_000)])["methods"][0]
    assert thin["sustainability"]["state"] == "thin"
    assert thin["sustainability"]["maxOneHourSharePct24h"] == 12.5

    row = _afk_result()
    row["mechanics"]["cyclesPerHourByBuyLimits"] = 400
    limited = build_public_afk(123, [row])["methods"][0]
    assert limited["sustainability"]["state"] == "limited"
    assert limited["sustainability"]["limitingFactor"] == "ge_buy_limit"


def test_afk_capital_includes_fixed_coin_costs():
    method = build_public_afk(123, [_afk_result(fixed_cost=1050)])["methods"][0]
    assert method["economics"]["capitalOneHour"] == 1_845_000


def test_high_liquidity_warning_is_public_high_risk():
    risk = public_risk(["HIGH_LIQUIDITY_RISK"])
    assert risk["level"] == "high"
    assert "Thin market" in risk["reasons"][0]


def test_public_alchemy_contains_matching_historical_windows():
    payload = build_public_alchemy(123, [_candidate()], {"castsPerHour": 1200, "useFireStaff": True})
    assert payload["items"][0]["history"] == {"24hProfitPerCast": 800.0, "7dProfitPerCast": 750.0, "30dProfitPerCast": 700.0}


def test_unavailable_alchemy_never_emits_numeric_profit():
    item = build_public_alchemy(123, [_candidate(valid=False)], {"castsPerHour": 1200, "useFireStaff": True})["items"][0]
    assert item["profitPerCast"] is None
    assert item["profit4h"] is None
    assert item["capitalRequired"] is None
    assert item["risk"]["level"] == "unavailable"


def test_status_hides_internal_health_details_and_tracks_history_age():
    payload = build_public_status(123, {"status": "degraded", "api": {"timeseriesFailed": 2}, "warnings": ["SECRET_CODE"]}, short_history_generated_at=100, long_history_generated_at=80)
    assert payload == {"schemaVersion": 1, "generatedAt": 123, "liveGeneratedAt": 123, "shortHistoryGeneratedAt": 100, "longHistoryGeneratedAt": 80, "state": "delayed", "ageSeconds": 0}


def test_public_site_contains_afk_market_filters_and_compact_assets(tmp_path):
    assets = tmp_path / "assets-source"; assets.mkdir()
    _write_test_assets(assets)
    afk = build_public_afk(123, [_afk_result()]); alch = build_public_alchemy(123, [_candidate()], {"castsPerHour": 1200, "useFireStaff": True})
    site = tmp_path / "site"
    write_public_site(site, afk, alch, build_public_status(123, {"status": "ok", "api": {"timeseriesFailed": 0}, "warnings": []}), assets)
    validate_public_site(site)
    index = (site / "index.html").read_text(encoding="utf-8")
    assert "Market capacity" in index
    assert "More filters & skill levels" in index
    assert "High Alch" in index
    assert "enhancements.js" in index
    assert (site / "assets" / "enhancements.js").is_file()
    assert "Ledger" not in index and ">About<" not in index
    assert not (site / "market").exists()


def test_client_focuses_afk_scanner_on_market_aware_profit_and_breakdowns():
    app = open("web/assets/app.js", encoding="utf-8").read()
    enhancements = open("web/assets/enhancements.js", encoding="utf-8").read()
    assert 'function calculationHtml' in app
    assert 'function liquidityHtml' in app
    assert 'm.sustainability?.state' in app
    assert 'osrs-profit-finder.skill-levels.v1' in app
    assert 'age < 5400 ? "current" : age <= 9000 ? "delayed" : "stale"' in app
    assert '.planner-frame,#owned-input-panel,#local-tools{display:none!important}' in enhancements
    assert 'Expected executable' in enhancements
    assert 'Market confidence' in enhancements
    assert 'estimated executable capacity' in enhancements
    assert 'Requirements, recipe, calculation, liquidity and history' in enhancements
    assert 'data-favourite' not in enhancements
    assert 'data-compare' not in enhancements


def test_production_validator_rejects_incomplete_decision_model(tmp_path):
    assets = tmp_path / "assets-source"; assets.mkdir()
    _write_test_assets(assets)
    afk = build_public_afk(123, [_afk_result()])
    del afk["methods"][0]["fillConfidence"]
    with pytest.raises(ValueError, match="fill confidence"):
        write_public_site(tmp_path / "site", afk, build_public_alchemy(123, [_candidate()], {"castsPerHour": 1200, "useFireStaff": True}), build_public_status(123, {"status": "ok", "api": {"timeseriesFailed": 0}, "warnings": []}), assets)


def test_sanitizer_rejects_internal_key(tmp_path):
    site = tmp_path / "site"; (site / "assets").mkdir(parents=True); (site / "data").mkdir()
    for page in ("index.html", "alchemy.html"): (site / page).write_text("ok", encoding="utf-8")
    for asset in ("app.css", "app.js", "enhancements.js", "planner_v3.js", "cooking_math.js", "profile.js"):
        (site / "assets" / asset).write_text("", encoding="utf-8")
    base = {"schemaVersion": 1, "generatedAt": 123}
    (site / "data" / "afk.json").write_text(json.dumps({**base, "methods": [], "series": []}), encoding="utf-8")
    (site / "data" / "alchemy.json").write_text(json.dumps({**base, "items": []}), encoding="utf-8")
    (site / "data" / "status.json").write_text(json.dumps({**base, "state": "current"}), encoding="utf-8")
    with pytest.raises(ValueError, match="internal fields leaked"):
        validate_public_site(site)
