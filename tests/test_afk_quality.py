from osrs_market.afk_quality import build_afk_quality


def test_make_x_long_idle_scores_above_short_bankstanding_cycle():
    long_idle = {
        "afk": {"intervalSeconds": 90},
        "tags": ["make-x"],
        "model": {"methodType": "make-x", "workflow": {"processSeconds": 67.2, "bankSeconds": 3.0}},
    }
    short_idle = {
        "afk": {"intervalSeconds": 16.8},
        "tags": ["bankstanding"],
        "model": {"methodType": "bankstanding", "workflow": {"processSeconds": 16.8, "bankSeconds": 3.0}},
    }
    assert build_afk_quality(long_idle)["score"] > build_afk_quality(short_idle)["score"]


def test_gathering_is_marked_as_estimated_cadence():
    method = {
        "afk": {"intervalSeconds": 75},
        "tags": ["gathering"],
        "model": {"methodType": "gathering", "workflow": {}},
    }
    quality = build_afk_quality(method)
    assert quality["estimatedCadence"] is True
    assert quality["deterministicTiming"] is False
    assert quality["timingConfidence"] < 90


def test_afk_quality_exposes_interaction_frequency():
    method = {
        "afk": {"intervalSeconds": 60},
        "tags": ["make-x"],
        "model": {"methodType": "make-x", "workflow": {}},
    }
    quality = build_afk_quality(method)
    assert quality["estimatedInteractionsPerHour"] == 60.0
    assert 0 <= quality["score"] <= 100
