import json
from pathlib import Path

import pytest

from osrs_market import flipping_site
from osrs_market.flipping import build_public_flipping
from osrs_market.models import LatestPrice, MappingItem


ROOT = Path(__file__).resolve().parents[1]


def _settings():
    return {
        "freshness": {
            "fresh_seconds": 1800,
            "acceptable_seconds": 7200,
            "very_stale_seconds": 86400,
        }
    }


def _mapping():
    return {100: MappingItem(id=100, name="Test item", members=False, limit=1000)}


def _latest():
    return {100: LatestPrice(high=120, high_time=9900, low=100, low_time=9950)}


def _five_minute():
    return {100: {"avgHighPrice": 119, "avgLowPrice": 101, "highPriceVolume": 80, "lowPriceVolume": 100}}


def _one_hour():
    return {100: {"avgHighPrice": 118, "avgLowPrice": 100, "highPriceVolume": 400, "lowPriceVolume": 600}}


def test_hidden_flipping_page_is_unlisted_and_noindex():
    page = (ROOT / "web" / "flipping.html").read_text(encoding="utf-8")
    public_site = (ROOT / "src" / "osrs_market" / "public_site.py").read_text(encoding="utf-8")

    assert 'name="robots" content="noindex,nofollow"' in page
    assert 'data-page="flipping"' in page
    assert 'assets/flipping.js' in page
    assert 'href="flipping.html"' not in public_site
    assert 'Grand Exchange Flips' not in public_site


def test_flipping_model_uses_post_tax_margin_and_directional_flow():
    item = build_public_flipping(10_000, _mapping(), _latest(), _five_minute(), _one_hour(), set(), _settings())["items"][0]

    assert item["buyPrice"] == 100
    assert item["sellPrice"] == 120
    assert item["tax"] == 2
    assert item["margin"] == 18
    assert item["roi"] == 18
    assert item["spread"]["state"] == "persistent"
    assert item["avg1h"]["buyFlow"] == 600
    assert item["avg1h"]["sellFlow"] == 400
    assert item["avg1h"]["balancedFlow"] == 400
    assert item["avg1h"]["buySellRatio"] == 1.5
    assert item["avg1h"]["flowBalancePct"] == pytest.approx(66.6666667)
    assert item["flowCappedQuantity"] == 400
    assert item["flowCappedProfit"] == 7200
    assert item["flowCoveragePct"] == 40
    assert item["freshness"]["state"] == "fresh"


def test_flipping_model_uses_repository_tax_exemptions():
    mapping = {100: MappingItem(id=100, name="Exempt item", limit=10)}
    latest = {100: LatestPrice(high=120, high_time=9900, low=100, low_time=9900)}
    averages = {100: {"avgHighPrice": 120, "avgLowPrice": 100, "highPriceVolume": 10, "lowPriceVolume": 10}}

    item = build_public_flipping(10_000, mapping, latest, averages, averages, {100}, _settings())["items"][0]

    assert item["tax"] == 0
    assert item["margin"] == 20


def test_hidden_flipping_builder_writes_same_origin_artifacts(tmp_path, monkeypatch):
    class FakeClient:
        def get_mapping(self):
            return _mapping()

        def get_latest(self):
            return _latest()

        def get_average_prices(self, timestep):
            return _five_minute() if timestep == "5m" else _one_hour()

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
    assert payload["generatedAt"] == 10_000
    assert payload["items"][0]["flowCappedProfit"] == 7200
    assert (public_dir / "flipping.html").read_text(encoding="utf-8") == "hidden page"
    assert (public_dir / "assets" / "flipping.js").read_text(encoding="utf-8") == "void 0;"


def test_hidden_flipping_client_reads_generated_same_origin_data():
    script = (ROOT / "web" / "assets" / "flipping.js").read_text(encoding="utf-8")

    assert 'loadJson("data/flipping.json")' in script
    assert "prices.runescape.wiki" not in script
    assert "flowCoveragePct" in script
    assert "flowBalancePct" in script
    assert "buySellRatio" in script
    assert "opportunity-size proxy, not guaranteed profit or GP/hour" in script


def test_publish_workflows_build_hidden_flipping_data():
    expected = "python -m osrs_market.flipping_site --config config --public-dir build/public-site --web-dir web"
    for name in ("refresh-live.yml", "refresh-history.yml"):
        workflow = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert expected in workflow
