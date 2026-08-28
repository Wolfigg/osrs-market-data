from osrs_market.models import LatestPrice
from osrs_market.quality import current_diagnostics

FRESHNESS = {"fresh_seconds": 1800, "acceptable_seconds": 7200, "very_stale_seconds": 86400}


def test_fresh_both_sides():
    d = current_diagnostics(LatestPrice(100, 9900, 90, 9950), 10_000, FRESHNESS)
    assert d["freshness"] == "fresh"
    assert d["crossed"] is False


def test_stale_high():
    d = current_diagnostics(LatestPrice(100, 1000, 90, 9900), 10_000, FRESHNESS)
    assert d["highFreshness"] == "stale"


def test_stale_low():
    d = current_diagnostics(LatestPrice(100, 9900, 90, 1000), 10_000, FRESHNESS)
    assert d["lowFreshness"] == "stale"


def test_crossed_current_prices_are_flagged_not_swapped():
    d = current_diagnostics(LatestPrice(90, 9900, 100, 9900), 10_000, FRESHNESS)
    assert d["high"] == 90
    assert d["low"] == 100
    assert d["crossed"] is True
    assert d["rawSpread"] == -10


def test_one_missing_side():
    d = current_diagnostics(LatestPrice(None, None, 90, 9900), 10_000, FRESHNESS)
    assert d["highFreshness"] == "missing"
    assert d["rawSpread"] is None


def test_both_missing():
    d = current_diagnostics(LatestPrice(None, None, None, None), 10_000, FRESHNESS)
    assert d["freshness"] == "missing"
