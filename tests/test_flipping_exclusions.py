import json

from osrs_market import flipping_site
from osrs_market.models import LatestPrice, MappingItem, TimeSeriesPoint


def test_hidden_flipping_excludes_old_school_bond_before_candidate_selection(tmp_path, monkeypatch):
    settings = {
        "freshness": {
            "fresh_seconds": 1800,
            "acceptable_seconds": 7200,
            "very_stale_seconds": 86400,
        },
        "flipping": {
            "candidate_timeseries_limit": 100,
            "excluded_item_ids": [13190],
        },
    }
    mapping = {
        100: MappingItem(id=100, name="Test item", limit=1000),
        13190: MappingItem(id=13190, name="Old school bond", members=True, limit=10),
    }
    latest = {
        100: LatestPrice(high=120, high_time=9900, low=100, low_time=9950),
        13190: LatestPrice(high=20_000_000, high_time=9900, low=18_000_000, low_time=9950),
    }
    averages = {
        100: {"avgHighPrice": 120, "avgLowPrice": 100, "highPriceVolume": 100, "lowPriceVolume": 100},
        13190: {"avgHighPrice": 20_000_000, "avgLowPrice": 18_000_000, "highPriceVolume": 10, "lowPriceVolume": 10},
    }
    series = [
        TimeSeriesPoint(timestamp, 120, 100, 100, 100)
        for timestamp in (8200, 8500, 8800, 9100, 9400)
    ]

    class FakeClient:
        def get_mapping(self):
            return mapping

        def get_latest(self):
            return latest

        def get_average_prices(self, timestep):
            return averages

        def get_timeseries(self, item_id, timestep):
            assert item_id == 100
            assert timestep == "5m"
            return series

    monkeypatch.setattr(flipping_site, "load_yaml", lambda path: settings)
    monkeypatch.setattr(flipping_site, "api_settings", lambda value: object())
    monkeypatch.setattr(flipping_site, "MarketApiClient", lambda value: FakeClient())
    monkeypatch.setattr(flipping_site, "load_and_resolve_exemptions", lambda path, current_mapping: (set(), []))
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
    assert [item["itemId"] for item in payload["items"]] == [100]
    assert payload["executionCandidatesRequested"] == 1
    assert payload["executionCandidatesSucceeded"] == 1
