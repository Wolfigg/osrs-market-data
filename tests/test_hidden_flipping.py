from pathlib import Path

import pytest

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


def test_hidden_flipping_page_is_unlisted_and_noindex():
    page = (ROOT / "web" / "flipping.html").read_text(encoding="utf-8")
    public_site = (ROOT / "src" / "osrs_market" / "public_site.py").read_text(encoding="utf-8")

    assert 'name="robots" content="noindex,nofollow"' in page
    assert 'data-page="flipping"' in page
    assert 'assets/flipping.js' in page
    assert 'href="flipping.html"' not in public_site
    assert 'Grand Exchange Flips' not in public_site


def test_flipping_model_uses_post_tax_margin_and_directional_flow():
    mapping = {
        100: MappingItem(id=100, name="Test item", members=False, limit=1000),
    }
    latest = {
        100: LatestPrice(high=120, high_time=9900, low=100, low_time=9950),
    }
    five_minute = {
        100: {"avgHighPrice": 119, "avgLowPrice": 101, "highPriceVolume": 80, "lowPriceVolume": 100},
    }
    one_hour = {
        100: {"avgHighPrice": 118, "avgLowPrice": 100, "highPriceVolume": 400, "lowPriceVolume": 600},
    }

    item = build_public_flipping(10_000, mapping, latest, five_minute, one_hour, set(), _settings())["items"][0]

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
