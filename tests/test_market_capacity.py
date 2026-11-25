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


def test_thin_directional_market_limits_expected_to_observed_flow_and_conservative_further():
    method = _method(directional_output=1197, fill_score=18)
    capacity = _market_capacity(method)
    raw = 1197 / 24
    assert round(capacity["rawDirectionalCyclesPerHour"], 3) == round(raw, 3)
    assert capacity["expectedExecutableCyclesPerHour"] == raw
    assert capacity["conservativeParticipationPct"] == 2.0
    assert capacity["conservativeExecutableCyclesPerHour"] == raw * 0.02
    assert capacity["participationPct"] is None
    assert capacity["limitingItem"]["name"] == "Example output"
    assert capacity["evidence"] == "weak"


def test_market_capacity_scales_expected_and_conservative_independently():
    method = _method(directional_output=1197, fill_score=18)
    _apply_market_capacity(method)
    expected_ratio = method["marketCapacity"]["mechanicalRatioPct"] / 100
    conservative_ratio = method["marketCapacity"]["conservativeMechanicalRatioPct"] / 100
    assert method["recommended"]["gpPerHour"] == 4_131_607.0 * expected_ratio
    assert method["scenarios"]["expectedGpPerHour"] == 4_131_607.0 * expected_ratio
    assert method["scenarios"]["conservativeGpPerHour"] == 3_000_000.0 * conservative_ratio
    assert method["current"]["gpPerHour"] == 4_527_600.0
    assert method["economics"]["unconstrainedConservativeGpPerHour"] == 3_000_000.0


def test_liquid_stable_market_can_retain_full_expected_and_conservative_rate():
    method = _method(directional_output=120_000, fill_score=95, stability="stable")
    capacity = _market_capacity(method)
    assert capacity["expectedExecutableCyclesPerHour"] == 1200.0
    assert capacity["conservativeExecutableCyclesPerHour"] == 1200.0
    assert capacity["mechanicalRatioPct"] == 100.0
    assert capacity["conservativeMechanicalRatioPct"] == 100.0
    assert capacity["evidence"] == "strong"


def test_volatile_market_only_reduces_conservative_participation():
    stable = _market_capacity(_method(directional_output=24_000, fill_score=95, stability="stable"))
    volatile = _market_capacity(_method(directional_output=24_000, fill_score=95, stability="volatile"))
    assert volatile["conservativeParticipationPct"] < stable["conservativeParticipationPct"]
    assert volatile["expectedExecutableCyclesPerHour"] == stable["expectedExecutableCyclesPerHour"]
    assert volatile["conservativeExecutableCyclesPerHour"] < stable["conservativeExecutableCyclesPerHour"]


def test_recent_directional_slowdown_constrains_expected_then_conservative_capacity():
    method = _method(directional_output=120_000, fill_score=95)
    method["liquidity"]["outputs"][0]["directionalVolume6h"] = 600
    capacity = _market_capacity(method)
    assert capacity["marketSupportedCyclesPerHour"] == 100
    assert capacity["expectedExecutableCyclesPerHour"] == 100
    assert capacity["conservativeExecutableCyclesPerHour"] == 25
    assert capacity["limitingItem"]["volumeAccelerationRatio"] < 1


def test_camphor_like_throughput_is_not_cut_when_observed_flow_supports_full_rate():
    method = {
        "mechanics": {"cyclesPerHour": 833.0, "cyclesPerHourByBuyLimits": 833.0},
        "fillConfidence": {"score": 84.0},
        "stability": {"state": "unknown"},
        "liquidity": {
            "inputs": [],
            "outputs": [{
                "name": "Camphor plank",
                "unitsPerHour": 833.0,
                "directionalVolume1h": 1497.0,
                "directionalVolume6h": 6104.0,
                "directionalVolume24h": 127588.0,
            }],
        },
        "current": {"valid": True, "gpPerHour": 299_047.0},
        "recommended": {"gpPerHour": 299_047.0},
        "scenarios": {
            "currentGpPerHour": 299_047.0,
            "expectedGpPerHour": 299_047.0,
            "conservativeGpPerHour": 280_000.0,
        },
        "economics": {},
        "priceSource": {},
    }

    capacity = _market_capacity(method)
    assert capacity["rawDirectionalCyclesPerHour"] == 6104 / 6
    assert capacity["expectedExecutableCyclesPerHour"] == 833.0
    assert capacity["conservativeExecutableCyclesPerHour"] < 833.0

    _apply_market_capacity(method)
    assert method["scenarios"]["expectedGpPerHour"] == 299_047.0
    assert method["recommended"]["gpPerHour"] == 299_047.0
    assert method["scenarios"]["conservativeGpPerHour"] < 280_000.0
