import math

from osrs_market.metrics import calculate_window_metrics
from osrs_market.models import TimeSeriesPoint
from osrs_market.windows import WindowSpec

SPEC = WindowSpec("test", 120, "1h", 60)


def p(ts, high, low, hv=1, lv=1):
    return TimeSeriesPoint(ts, high, low, hv, lv)


def test_vwap_known_fixture():
    points = [p(0, 100, 80, hv=1), p(60, 200, 180, hv=3)]
    m = calculate_window_metrics(points, SPEC)
    assert m["highVwap"] == 175


def test_null_price_is_not_zero_and_is_ignored_by_vwap():
    points = [p(0, None, 90, hv=50), p(60, 200, 180, hv=2)]
    m = calculate_window_metrics(points, SPEC)
    assert m["highVwap"] == 200
    assert m["samplesWithHigh"] == 1


def test_zero_volume_does_not_contribute_to_vwap():
    points = [p(0, 999, 90, hv=0), p(60, 100, 80, hv=2)]
    m = calculate_window_metrics(points, SPEC)
    assert m["highVwap"] == 100


def test_one_sided_points_do_not_manufacture_midpoint():
    points = [p(0, 100, None), p(60, None, 90)]
    m = calculate_window_metrics(points, SPEC)
    assert m["startMid"] is None
    assert m["changePct"] is None
    assert m["twoSidedSamples"] == 0


def test_change_uses_earliest_and_latest_valid_midpoint():
    points = [p(0, 110, 90), p(60, 121, 99)]
    m = calculate_window_metrics(points, SPEC)
    assert m["startMid"] == 100
    assert m["endMid"] == 110
    assert math.isclose(m["changePct"], 10.0)


def test_crossed_historical_spread_is_preserved():
    m = calculate_window_metrics([p(0, 90, 100)], WindowSpec("x", 60, "1h", 60))
    assert m["medianSpread"] == -10


def test_coverage_uses_expected_buckets_not_array_length_as_time():
    m = calculate_window_metrics([p(0, 100, 90)], SPEC)
    assert m["coveragePct"] == 50.0


def test_no_points_returns_null_metrics_not_fake_zero_prices():
    m = calculate_window_metrics([], SPEC)
    assert m["highVwap"] is None
    assert m["lowVwap"] is None
    assert m["changePct"] is None
    assert m["sampleCount"] == 0
