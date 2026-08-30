import json
import math

from osrs_market.ranking import RANKING_MODES, rank_methods


def method(name, expected, conservative, capital, afk, fill, stability="stable", sustainability="strong", confidence=90):
    return {
        "name": name,
        "scenarios": {"expectedGpPerHour": expected, "conservativeGpPerHour": conservative},
        "economics": {"capitalOneHour": capital},
        "afk": {"intervalSeconds": afk},
        "fillConfidence": {"score": fill},
        "stability": {"state": stability},
        "sustainability": {"state": sustainability},
        "confidence": {"overall": confidence},
    }


def test_best_profit_uses_expected_profit():
    rows = [method("stable", 700_000, 650_000, 1_000_000, 60, 95), method("headline", 900_000, 250_000, 5_000_000, 20, 30)]
    assert rank_methods(rows, "best_profit")[0]["name"] == "headline"


def test_best_stable_can_prefer_lower_headline_profit():
    rows = [
        method("stable", 700_000, 650_000, 1_000_000, 60, 95, "stable", "strong", 95),
        method("headline", 900_000, 250_000, 5_000_000, 20, 30, "volatile", "thin", 55),
    ]
    assert rank_methods(rows, "best_stable")[0]["name"] == "stable"


def test_best_low_capital_penalises_large_working_capital():
    rows = [method("cheap", 500_000, 450_000, 200_000, 30, 90), method("expensive", 550_000, 500_000, 5_000_000, 30, 90)]
    assert rank_methods(rows, "best_low_capital")[0]["name"] == "cheap"


def test_unavailable_methods_never_emit_non_finite_json_scores():
    unavailable = method("unavailable", None, None, 0, 0, None, "unknown", "unknown", 50)
    for mode in RANKING_MODES:
        row = rank_methods([unavailable], mode)[0]
        assert math.isfinite(row["ranking"]["score"])
        json.dumps(row, allow_nan=False)
