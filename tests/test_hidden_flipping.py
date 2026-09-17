import json
from pathlib import Path

import pytest

from osrs_market import flipping_site
from osrs_market.flipping import build_public_flipping, select_flipping_timeseries_candidates
from osrs_market.models import LatestPrice, MappingItem, TimeSeriesPoint


ROOT = Path(__file__).resolve().parents[1]


def _settings():
    return {
        "freshness": {
            "fresh_seconds": 1800,
            "acceptable_seconds": 7200,
            "very_stale_seconds": 86400,
        },
        "flipping": {"candidate_timeseries_limit": 100},
    }


def _mapping():
    return {100: MappingItem(id=100, name="Test item", members=False, limit=1000)}


def _latest():
    return {100: LatestPrice(high=120, high_time=9900, low=100, low_time=9950)}


def _five_minute():
    return {100: {"avgHighPrice": 119, "avgLowPrice": 101, "highPriceVolume": 80, "lowPriceVolume": 100}}


def _one_hour():
    return {100: {"avgHighPrice": 118, "avgLowPrice": 100, "highPriceVolume": 400, "lowPriceVolume": 600}}


def _timeseries():
    points = []
    rows = [
        (7000, 102, 120),
        (7300, 101, 119),
        (7600, 100, 118),
        (7900, 101, 119),
        (8200, 100, 118),
        (8500, 100, 118),
        (8800, 101, 119),
        (9100, 100, 118),
        (9400, 100, 118),
    ]
    for timestamp, low, high in rows:
        points.append(TimeSeriesPoint(
            timestamp=timestamp,
            avg_high_price=high,
            avg_low_price=low,
            high_price_volume=100,
            low_price_volume=100,
        ))
    return {100: points}


def _calibration(ready=True):
    return {
        "calibrationReady": ready,
        "calibrationHorizonMinutes": 60,
        "minimumCalibrationSamples": 100,
        "minimumItemSamples": 5,
        "byHorizon": {
            "60": {
                "sampleCount": 200,
                "marginSurvivalRate": 0.8,
                "conservativeSurvivalRate": 0.7,
                "rankingStabilityRate": 0.6,
                "meanAbsoluteExpectedMarginError": 4,
                "meanAbsoluteMidpointDriftPct": 1.2,
            }
        },
        "itemCalibration": {
            "100": {
                "ready": True,
                "sampleCount": 10,
                "marginSurvivalRate": 0.5,
                "conservativeSurvivalRate": 0.4,
                "rankingStabilityRate": 0.7,
                "meanAbsoluteExpectedMarginError": 3,
                "meanAbsoluteMidpointDriftPct": 0.9,
            }
        },
    }


def test_hidden_flipping_page_is_unlisted_and_noindex():
    page = (ROOT / "web" / "flipping.html").read_text(encoding="utf-8")
    public_site = (ROOT / "src" / "osrs_market" / "public_site.py").read_text(encoding="utf-8")

    assert 'name="robots" content="noindex,nofollow"' in page
    assert 'data-page="flipping"' in page
    assert 'assets/flipping.js' in page
    assert 'href="flipping.html"' not in public_site
    assert 'Grand Exchange Flips' not in public_site


def test_flipping_model_uses_execution_prices_and_consistent_capacity_horizons():
    item = build_public_flipping(
        10_000,
        _mapping(),
        _latest(),
        _five_minute(),
        _one_hour(),
        set(),
        _settings(),
        _timeseries(),
    )["items"][0]

    assert item["buyPrice"] == 100
    assert item["sellPrice"] == 120
    assert item["tax"] == 2
    assert item["margin"] == 18
    assert item["expected"]["buyPrice"] == 101
    assert item["expected"]["sellPrice"] == 118
    assert item["expected"]["margin"] == 15
    assert item["executionFreshness"] == "fresh"
    assert item["spread"]["state"] == "persistent"
    assert item["spreadStats"]["profitableBucketCount"] == item["spreadStats"]["bucketCount"]
    assert item["spreadStats"]["profitableBucketPct"] == 100
    assert item["buyFlowPerHour"] == 1000
    assert item["sellFlowPerHour"] == 1000
    assert item["marketFlowPerHour"] == 1000
    assert item["geLimitRatePerHour"] == 250
    assert item["capacityPerHour"] == 250
    assert item["capacityQuantity4h"] == 1000
    assert item["capacityCoverage4hPct"] == 100
    assert item["expectedOpportunity4h"] == 15000
    assert item["rankingScore4h"] == 15000
    assert item["calibration"]["applied"] is False
    assert item["drift"]["midpoint60m"] is not None


def test_flipping_v3_ranking_only_uses_survival_after_calibration_gate():
    uncalibrated = build_public_flipping(
        10_000,
        _mapping(),
        _latest(),
        _five_minute(),
        _one_hour(),
        set(),
        _settings(),
        _timeseries(),
        _calibration(False),
    )
    calibrated = build_public_flipping(
        10_000,
        _mapping(),
        _latest(),
        _five_minute(),
        _one_hour(),
        set(),
        _settings(),
        _timeseries(),
        _calibration(True),
    )

    assert uncalibrated["rankingMode"] == "expected-opportunity"
    assert uncalibrated["items"][0]["rankingScore4h"] == 15000
    assert uncalibrated["items"][0]["calibration"]["applied"] is False

    item = calibrated["items"][0]
    assert calibrated["rankingMode"] == "survival-calibrated"
    assert calibrated["calibration"]["sampleCount"] == 200
    assert item["calibration"]["source"] == "item"
    assert item["calibration"]["sampleCount"] == 10
    assert item["calibration"]["marginSurvivalRate"] == 0.5
    assert item["calibration"]["applied"] is True
    assert item["rankingScore4h"] == 7500


def test_flipping_conservative_prices_move_against_the_flip():
    rows = []
    for timestamp, low, high in [
        (8200, 100, 200),
        (8500, 100, 200),
        (8800, 100, 200),
        (9100, 100, 200),
        (9400, 150, 160),
    ]:
        rows.append(TimeSeriesPoint(timestamp, high, low, 100, 100))

    item = build_public_flipping(
        10_000,
        _mapping(),
        _latest(),
        _five_minute(),
        _one_hour(),
        set(),
        _settings(),
        {100: rows},
    )["items"][0]

    assert item["expected"]["buyPrice"] == 110
    assert item["expected"]["sellPrice"] == 192
    assert item["conservative"]["buyPrice"] == 150
    assert item["conservative"]["sellPrice"] == 160
    assert item["conservative"]["margin"] < item["expected"]["margin"]


def test_flipping_model_uses_repository_tax_exemptions():
    mapping = {100: MappingItem(id=100, name="Exempt item", limit=10)}
    latest = {100: LatestPrice(high=120, high_time=9900, low=100, low_time=9900)}
    averages = {100: {"avgHighPrice": 120, "avgLowPrice": 100, "highPriceVolume": 10, "lowPriceVolume": 10}}
    series = {100: [TimeSeriesPoint(ts, 120, 100, 10, 10) for ts in (8200, 8500, 8800, 9100, 9400)]}

    item = build_public_flipping(10_000, mapping, latest, averages, averages, {100}, _settings(), series)["items"][0]

    assert item["tax"] == 0
    assert item["margin"] == 20
    assert item["expected"]["tax"] == 0
    assert item["expected"]["margin"] == 20


def test_flipping_timeseries_preselection_prefers_supported_positive_spreads():
    selected = select_flipping_timeseries_candidates(
        10_000,
        _mapping(),
        _latest(),
        _five_minute(),
        _one_hour(),
        set(),
        _settings(),
    )
    assert selected == [100]


def test_hidden_flipping_builder_writes_same_origin_artifacts(tmp_path, monkeypatch):
    class FakeClient:
        def get_mapping(self):
            return _mapping()

        def get_latest(self):
            return _latest()

        def get_average_prices(self, timestep):
            return _five_minute() if timestep == "5m" else _one_hour()

        def get_timeseries(self, item_id, timestep):
            assert item_id == 100
            assert timestep == "5m"
            return _timeseries()[100]

    monkeypatch.setattr(flipping_site, "load_yaml", lambda path: _settings())
    monkeypatch.setattr(flipping_site, "api_settings", lambda settings: object())
    monkeypatch.setattr(flipping_site, "MarketApiClient", lambda settings: FakeClient())
    monkeypatch.setattr(flipping_site, "load_and_resolve_exemptions", lambda path, mapping: (set(), []))
    monkeypatch.setattr(flipping_site.time, "time", lambda: 10_000)

    public_dir = tmp_path / "public-site"
    (public_dir / "data").mkdir(parents=True)
    (public_dir / "assets").mkdir()
    web_dir = tmp_path / "web"
    (web_dir / "assets").mkdir(parents=True)
    (web_dir / "flipping.html").write_text("hidden page", encoding="utf-8")
    (web_dir / "assets" / "flipping.js").write_text("void 0;", encoding="utf-8")

    flipping_site.build_hidden_flipping_site(tmp_path / "config", public_dir, web_dir)

    payload = json.loads((public_dir / "data" / "flipping.json").read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == 3
    assert payload["generatedAt"] == 10_000
    assert payload["rankingMode"] == "expected-opportunity"
    assert payload["items"][0]["expectedOpportunity4h"] == 15000
    assert payload["executionCandidatesRequested"] == 1
    assert payload["executionCandidatesSucceeded"] == 1
    assert payload["executionCandidatesFailed"] == 0
    assert (public_dir / "flipping.html").read_text(encoding="utf-8") == "hidden page"
    assert (public_dir / "assets" / "flipping.js").read_text(encoding="utf-8") == "void 0;"


def test_hidden_flipping_client_reads_generated_same_origin_data():
    script = (ROOT / "web" / "assets" / "flipping.js").read_text(encoding="utf-8")

    assert 'loadJson("data/flipping.json")' in script
    assert "prices.runescape.wiki" not in script
    assert "scenarioPlan" in script
    assert "model-rank" in script
    assert "rankingPlanScore" in script
    assert "capacityQuantity4h" in script
    assert "profitableBucketPct" in script
    assert "Available GP limits planned quantity" in script


def test_publish_workflows_build_hidden_flipping_and_persist_calibration_separately():
    expected = "python -m osrs_market.flipping_site --config config --public-dir build/public-site --web-dir web --history-cache .flipping-cache/flipping-history.json"
    live = (ROOT / ".github" / "workflows" / "refresh-live.yml").read_text(encoding="utf-8")
    history = (ROOT / ".github" / "workflows" / "refresh-history.yml").read_text(encoding="utf-8")
    calibration = (ROOT / ".github" / "workflows" / "refresh-flipping-calibration.yml").read_text(encoding="utf-8")

    assert expected in live
    assert expected in history
    assert ".flipping-cache" in live
    assert "python tools/flipping_history.py" not in live
    assert "python tools/flipping_history.py" in history
    assert "python tools/flipping_history.py" in calibration
    assert "workflow_run:" in calibration
    assert "Refresh live market data" in calibration
    assert ".flipping-cache" in calibration
