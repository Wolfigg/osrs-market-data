from osrs_market.recommendation import build_stability, percentage_deviation, recommended_gp_per_hour, weighted_reference


def history(h24=430_000, h7=415_000, h30=420_000):
    return {"24hGpPerHour": h24, "7dGpPerHour": h7, "30dGpPerHour": h30}


def test_percentage_deviation():
    assert round(percentage_deviation(610_000, 395_000), 1) == 54.4


def test_weighted_reference_preserves_legacy_blend_when_new_windows_are_missing():
    assert weighted_reference(history(400, 300, 200)) == 330


def test_weighted_reference_uses_short_and_six_month_context():
    values = history(400, 300, 200)
    values.update({"6hGpPerHour": 500, "6mGpPerHour": 100})
    assert weighted_reference(values) == 349.5


def test_large_current_spike_is_volatile_and_recommendation_is_capped():
    h = history()
    stability = build_stability(900_000, h, [], True)
    assert stability["state"] == "volatile"
    reference = weighted_reference(h)
    assert recommended_gp_per_hour(900_000, h, stability["state"]) == reference * 1.15


def test_consistent_current_and_history_is_stable():
    h = history(575_000, 582_000, 570_000)
    stability = build_stability(590_000, h, [], True)
    assert stability["state"] == "stable"
    recommended = recommended_gp_per_hour(590_000, h, stability["state"])
    assert weighted_reference(h) < recommended < 590_000


def test_missing_history_is_watch_and_not_stable():
    h = history(575_000, None, 570_000)
    stability = build_stability(580_000, h, [], True)
    assert stability["state"] == "watch"


def test_thin_market_is_discounted():
    h = history(500_000, 500_000, 500_000)
    stability = build_stability(500_000, h, ["HIGH_LIQUIDITY_RISK"], True)
    assert stability["state"] == "thin_market"
    assert recommended_gp_per_hour(500_000, h, stability["state"]) == 400_000


def test_stale_and_unavailable_do_not_publish_recommendation():
    h = history()
    assert build_stability(500_000, h, ["CURRENT_HIGH_STALE"], True)["state"] == "stale"
    assert recommended_gp_per_hour(500_000, h, "stale") is None
    assert build_stability(None, h, [], False)["state"] == "unavailable"
