from osrs_market.public_models_v2 import _apply_market_capacity, _market_capacity


def _method(*, directional_output: float, fill_score: float = 18.0, stability: str = "stable"):
    return {
        "mechanics": {"cyclesPerHour": 1200.0, "cyclesPerHourByBuyLimits": 1200.0},
        "fillConfidence": {"score": fill_score},
        "stability": {"state": stability},
        "liquidity": {
            "inputs": [],
            "outputs": [
                {
                    "name": "Example output",
                    "directionalVolume24h": directional_output,
                    "unitsPerHour": 1200.0,
                }
            ],
        },
        "current": {"valid": True, "gpPerHour": 4_527_600.0},
        "recommended": {"gpPerHour": 4_131_607.0},
        "scenarios": {
            "currentGpPerHour": 4_527_600.0,
            "expectedGpPerHour": 4_131_607.0,
            "conservativeGpPerHour": 3_000_000.0,
        },
        "economics": {},
        "priceSource": {},
    }


def test_thin_directional_market_is_not_treated_as_full_personal_capacity():
    method = _method(directional_output=1197, fill_score=18)
    capacity = _market_capacity(method)
    assert capacity["participationPct"] == 2.0
    assert round(capacity["rawDirectionalCyclesPerHour"], 3) == round(1197 / 24, 3)
    assert capacity["cyclesPerHour"] < 1.0
    assert capacity["limitingItem"]["name"] == "Example output"
    assert capacity["evidence"] == "weak"


def test_market_capacity_scales_recommended_and_expected_not_current_price_math():
    method = _method(directional_output=1197, fill_score=18)
    _apply_market_capacity(method)
    ratio = method["marketCapacity"]["mechanicalRatioPct"] / 100
    assert method["recommended"]["gpPerHour"] == 4_131_607.0 * ratio
    assert method["scenarios"]["expectedGpPerHour"] == 4_131_607.0 * ratio
    assert method["scenarios"]["conservativeGpPerHour"] == 3_000_000.0 * ratio
    assert method["current"]["gpPerHour"] == 4_527_600.0


def test_liquid_stable_market_can_retain_full_mechanical_rate():
    method = _method(directional_output=120_000, fill_score=95, stability="stable")
    capacity = _market_capacity(method)
    assert capacity["participationPct"] == 25.0
    assert capacity["cyclesPerHour"] == 1200.0
    assert capacity["mechanicalRatioPct"] == 100.0
    assert capacity["evidence"] == "strong"


def test_volatile_market_reduces_participation_even_with_high_fill_score():
    stable = _market_capacity(_method(directional_output=24_000, fill_score=95, stability="stable"))
    volatile = _market_capacity(_method(directional_output=24_000, fill_score=95, stability="volatile"))
    assert volatile["participationPct"] < stable["participationPct"]
    assert volatile["cyclesPerHour"] < stable["cyclesPerHour"]


def test_recent_directional_slowdown_constrains_24h_capacity():
    method = _method(directional_output=120_000, fill_score=95)
    method["liquidity"]["outputs"][0]["directionalVolume6h"] = 600
    capacity = _market_capacity(method)
    assert capacity["marketSupportedCyclesPerHour"] == 100
    assert capacity["expectedExecutableCyclesPerHour"] == 25
    assert capacity["limitingItem"]["volumeAccelerationRatio"] < 1
