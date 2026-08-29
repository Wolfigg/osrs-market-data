from osrs_market.alchemy import alch_costs, four_hour_capacity, preliminary_scan
from osrs_market.models import LatestPrice, MappingItem


def item(**kwargs):
    base = dict(id=100, name="Test item", members=False, highalch=1000, limit=5000)
    base.update(kwargs)
    return MappingItem(**base)


def test_fire_staff_enabled_costs_one_nature_only():
    result = alch_costs(item(), 700, 100, True)
    assert result["cost"] == 800
    assert result["profit"] == 200


def test_fire_staff_disabled_adds_fire_runes():
    result = alch_costs(item(), 700, 100, False, fire_rune_price=5, fire_runes_per_cast=5)
    assert result["cost"] == 825
    assert result["profit"] == 175


def test_fire_staff_disabled_without_fire_price_is_unusable():
    assert alch_costs(item(), 700, 100, False)["profit"] is None


def test_nature_price_unavailable_returns_null_profit():
    assert alch_costs(item(), 700, None, True)["profit"] is None


def test_high_alch_unavailable_returns_null_profit():
    assert alch_costs(item(highalch=None), 700, 100, True)["profit"] is None


def test_ge_limit_under_4800_caps_four_hour_quantity():
    cap = four_hour_capacity(700, 100, 1000)
    assert cap["maxQuantity"] == 1000


def test_ge_limit_over_4800_uses_mechanical_cap():
    cap = four_hour_capacity(700, 100, 10_000)
    assert cap["maxQuantity"] == 4800


def test_insufficient_capital_caps_quantity():
    cap = four_hour_capacity(700, 100, 10_000, available_gp=8000)
    assert cap["maxQuantity"] == 10


def test_preliminary_scan_rejects_stale_item_unless_forced():
    mapping = {
        561: MappingItem(id=561, name="Nature rune"),
        100: item(),
    }
    latest = {
        561: LatestPrice(100, 9990, 95, 9990),
        100: LatestPrice(700, 1, 690, 1),
    }
    settings = {"alchemy": {
        "nature_rune_item_id": 561,
        "candidate_timeseries_limit": 100,
        "preliminary_max_age_seconds": 100,
        "preliminary_margin_floor_gp": -50,
        "members_filter": "all",
    }}
    assert preliminary_scan(mapping, latest, 10_000, settings, set(), set()) == []
    forced = preliminary_scan(mapping, latest, 10_000, settings, set(), {100})
    assert forced[0]["itemId"] == 100


def test_stale_current_candidate_does_not_publish_current_profit():
    from osrs_market.alchemy import build_alchemy_candidate
    it = item()
    latest_item = LatestPrice(700, 1, 690, 1)
    latest_nature = LatestPrice(100, 1, 95, 1)
    windows = {
        "24h": {"highVwap": 700, "totalVolume": 10000, "changePct": 0},
        "7d": {"highVwap": 680, "totalVolume": 50000},
        "30d": {"highVwap": 660},
    }
    nature_windows = {
        "24h": {"highVwap": 100},
        "7d": {"highVwap": 95},
        "30d": {"highVwap": 90},
    }
    settings = {
        "alchemy": {"use_fire_staff": True, "casts_per_hour": 1200, "xp_per_cast": 65, "preliminary_max_age_seconds": 86400},
        "liquidity": {"notice_market_share_pct": 1, "caution_market_share_pct": 5, "high_risk_market_share_pct": 10},
        "freshness": {"acceptable_seconds": 7200},
    }
    result = build_alchemy_candidate(it, latest_item, latest_nature, windows, nature_windows, 10_000, settings)
    assert result["currentInstant"]["valid"] is False
    assert result["currentInstant"]["profitPerCast"] is None
    assert result["historicalInstant24h"]["profitPerCast"] == 200
    assert result["historicalInstant7d"]["profitPerCast"] == 225
    assert result["historicalInstant30d"]["profitPerCast"] == 250


def test_no_fire_staff_candidate_uses_matching_fire_rune_windows():
    from osrs_market.alchemy import build_alchemy_candidate
    it = item()
    latest_item = LatestPrice(700, 9900, 690, 9900)
    latest_nature = LatestPrice(100, 9900, 95, 9900)
    latest_fire = LatestPrice(5, 9900, 4, 9900)
    windows = {
        "24h": {"highVwap": 700, "totalVolume": 10000, "changePct": 0},
        "7d": {"highVwap": 680, "totalVolume": 50000},
        "30d": {"highVwap": 660},
    }
    nature_windows = {
        "24h": {"highVwap": 100},
        "7d": {"highVwap": 95},
        "30d": {"highVwap": 90},
    }
    fire_windows = {
        "24h": {"highVwap": 5},
        "7d": {"highVwap": 4},
        "30d": {"highVwap": 3},
    }
    settings = {
        "alchemy": {"use_fire_staff": False, "fire_runes_per_cast": 5, "casts_per_hour": 1200, "xp_per_cast": 65, "preliminary_max_age_seconds": 86400},
        "liquidity": {"notice_market_share_pct": 1, "caution_market_share_pct": 5, "high_risk_market_share_pct": 10},
        "freshness": {"acceptable_seconds": 7200},
    }
    result = build_alchemy_candidate(it, latest_item, latest_nature, windows, nature_windows, 10_000, settings, latest_fire, fire_windows)
    assert result["currentInstant"]["profitPerCast"] == 175
    assert result["historicalInstant24h"]["profitPerCast"] == 175
    assert result["historicalInstant7d"]["profitPerCast"] == 205
    assert result["historicalInstant30d"]["profitPerCast"] == 235
