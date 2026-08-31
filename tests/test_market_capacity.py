from osrs_market.public_models_v2 import _apply_market_capacity, _market_capacity


def _method(*, directional_output: float, fill_score: float = 18.0):
    return {
        "mechanics": {"cyclesPerHour": 1200.0, "cyclesPerHourByBuyLimits": 1200.0},
        "fillConfidence": {"score": fill_score},
        "liquidity": {
            "inputs": [],
            "outputs": [
                {
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
    # Mirrors the failure mode seen live for an Arceuus tablet: roughly 1,200
    # instant-sell units observed in an entire day cannot support 1,200 units/h
    # from a single player. Very-low confidence permits only 2% participation.
    method = _method(directional_output=1197, fill_score=18)
    capacity = _market_capacity(method)
    assert capacity["participationPct"] == 2.0
    assert round(capacity["rawDirectionalCyclesPerHour"], 3) == round(1197 / 24, 3)
    assert capacity["cyclesPerHour"] < 1.0


def test_market_capacity_scales_recommended_and_expected_not_current_price_math():
    method = _method(directional_output=1197, fill_score=18)
    _apply_market_capacity(method)
    ratio = method["marketCapacity"]["mechanicalRatioPct"] / 100
    assert method["recommended"]["gpPerHour"] == 4_131_607.0 * ratio
    assert method["scenarios"]["expectedGpPerHour"] == 4_131_607.0 * ratio
    assert method["scenarios"]["conservativeGpPerHour"] == 3_000_000.0 * ratio
    # Current remains the raw current-price mechanical reference and is labelled
    # separately in the UI; executable recommendation/session values are capped.
    assert method["current"]["gpPerHour"] == 4_527_600.0


def test_liquid_market_can_retain_full_mechanical_rate():
    # At high confidence the model allows 25% of observed directional flow.
    # 120,000/day => 5,000/h raw => 1,250/h personal cap, above 1,200 mechanics.
    method = _method(directional_output=120_000, fill_score=95)
    capacity = _market_capacity(method)
    assert capacity["participationPct"] == 25.0
    assert capacity["cyclesPerHour"] == 1200.0
    assert capacity["mechanicalRatioPct"] == 100.0
