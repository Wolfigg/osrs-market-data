from osrs_market.models import TimeSeriesPoint
from osrs_market.windows import normalize_points, slice_window


def p(ts, high=100, low=90, hv=1, lv=1):
    return TimeSeriesPoint(ts, high, low, hv, lv)


def test_exact_6h_cutoff_is_included():
    now = 100_000
    points = [p(now - 6 * 3600), p(now - 6 * 3600 - 1), p(now)]
    result = slice_window(points, now, 6 * 3600)
    assert [x.timestamp for x in result] == [now - 6 * 3600, now]


def test_exact_24h_cutoff_is_included():
    now = 200_000
    result = slice_window([p(now - 86400), p(now - 86401)], now, 86400)
    assert [x.timestamp for x in result] == [now - 86400]


def test_sparse_buckets_are_not_replaced():
    now = 50_000
    result = slice_window([p(now - 3000), p(now)], now, 3600)
    assert len(result) == 2


def test_out_of_order_input_is_sorted():
    points = [p(30), p(10), p(20)]
    assert [x.timestamp for x in normalize_points(points)] == [10, 20, 30]


def test_duplicate_timestamp_later_input_wins():
    points = [p(10, high=100), p(10, high=200)]
    result = normalize_points(points)
    assert len(result) == 1
    assert result[0].avg_high_price == 200


def test_future_points_are_excluded():
    result = slice_window([p(100), p(101)], 100, 3600)
    assert [x.timestamp for x in result] == [100]
