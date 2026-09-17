import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("flipping_history", ROOT / "tools" / "flipping_history.py")
flipping_history = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(flipping_history)


def _item(margin=20, conservative=10, opportunity=20_000, midpoint=110):
    return {
        "itemId": 100,
        "name": "Test item",
        "margin": 25,
        "expected": {"buyPrice": 100, "sellPrice": 122, "margin": margin},
        "conservative": {"buyPrice": 105, "sellPrice": 117, "margin": conservative},
        "expectedOpportunity4h": opportunity,
        "capacityQuantity4h": 1000,
        "spreadStats": {"profitableBucketPct": 90},
        "drift": {"drift60mPct": -1.5, "currentMidpoint": midpoint},
    }


def test_flipping_history_snapshot_records_model_evidence():
    row = flipping_history.snapshot(_item(), 10_000, 3)

    assert row["itemId"] == 100
    assert row["rank"] == 3
    assert row["expectedMargin"] == 20
    assert row["conservativeMargin"] == 10
    assert row["expectedOpportunity4h"] == 20_000
    assert row["profitableBucketPct"] == 90
    assert row["drift60mPct"] == -1.5
    assert row["currentMidpoint"] == 110


def test_flipping_history_evaluates_margin_survival_error_and_midpoint_drift():
    old = flipping_history.snapshot(_item(margin=20, conservative=10, midpoint=100), 10_000, 2)
    current = _item(margin=15, conservative=8, midpoint=102)

    result = flipping_history.evaluate(old, current, 4, 60.0, 64.0)

    assert result["targetHorizonMinutes"] == 60
    assert result["horizonMinutes"] == 64
    assert result["followupExpectedMargin"] == 15
    assert result["expectedMarginError"] == -5
    assert result["absoluteExpectedMarginError"] == 5
    assert result["conservativeSurvived"] is True
    assert result["marginSurvived"] is True
    assert result["rankingStable"] is True
    assert result["midpointDrift"] == 2
    assert result["midpointDriftPct"] == 2


def test_flipping_history_summary_separates_15_30_and_60_minute_evidence():
    rows = [
        {
            "itemId": 100,
            "targetHorizonMinutes": 15,
            "absoluteExpectedMarginError": 2,
            "conservativeSurvived": True,
            "marginSurvived": True,
            "rankingStable": True,
            "midpointDriftPct": 0.5,
        },
        {
            "itemId": 100,
            "targetHorizonMinutes": 30,
            "absoluteExpectedMarginError": 4,
            "conservativeSurvived": True,
            "marginSurvived": True,
            "rankingStable": True,
            "midpointDriftPct": 1.0,
        },
        {
            "itemId": 100,
            "targetHorizonMinutes": 60,
            "absoluteExpectedMarginError": 6,
            "conservativeSurvived": False,
            "marginSurvived": True,
            "rankingStable": False,
            "midpointDriftPct": -2.0,
        },
    ]

    summary = flipping_history.summarise(rows, minimum_calibration_samples=2, minimum_item_samples=1)

    assert summary["byHorizon"]["15"]["sampleCount"] == 1
    assert summary["byHorizon"]["30"]["sampleCount"] == 1
    assert summary["byHorizon"]["60"]["sampleCount"] == 1
    assert summary["sampleCount"] == 1
    assert summary["calibrationReady"] is False
    assert summary["itemCalibration"]["100"]["ready"] is True
    assert summary["itemCalibration"]["100"]["marginSurvivalRate"] == 1


def test_flipping_history_calibration_readiness_is_gated_on_60_minute_samples():
    rows = [{
        "itemId": 100,
        "targetHorizonMinutes": 60,
        "absoluteExpectedMarginError": 5,
        "conservativeSurvived": True,
        "marginSurvived": True,
        "rankingStable": False,
        "midpointDriftPct": 1,
    }] * 4

    summary = flipping_history.summarise(rows, minimum_calibration_samples=5)
    assert summary["sampleCount"] == 4
    assert summary["meanAbsoluteExpectedMarginError"] == 5
    assert summary["calibrationReady"] is False

    ready = flipping_history.summarise(rows + [rows[0]], minimum_calibration_samples=5)
    assert ready["calibrationReady"] is True


def test_flipping_history_legacy_rows_are_treated_as_60_minute_evidence():
    rows = [{
        "itemId": 100,
        "absoluteExpectedMarginError": 1,
        "conservativeSurvived": True,
        "marginSurvived": True,
        "rankingStable": True,
    }]

    summary = flipping_history.summarise(rows, minimum_calibration_samples=1, minimum_item_samples=1)

    assert summary["byHorizon"]["60"]["sampleCount"] == 1
    assert summary["calibrationReady"] is True
