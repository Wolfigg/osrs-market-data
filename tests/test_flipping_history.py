import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("flipping_history", ROOT / "tools" / "flipping_history.py")
flipping_history = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(flipping_history)


def _item(margin=20, conservative=10, opportunity=20_000):
    return {
        "itemId": 100,
        "name": "Test item",
        "margin": 25,
        "expected": {"buyPrice": 100, "sellPrice": 122, "margin": margin},
        "conservative": {"buyPrice": 105, "sellPrice": 117, "margin": conservative},
        "expectedOpportunity4h": opportunity,
        "capacityQuantity4h": 1000,
        "spreadStats": {"profitableBucketPct": 90},
        "drift": {"drift60mPct": -1.5},
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


def test_flipping_history_evaluates_margin_survival_and_error():
    old = flipping_history.snapshot(_item(margin=20, conservative=10), 10_000, 2)
    current = _item(margin=15, conservative=8)

    result = flipping_history.evaluate(old, current, 4, 60.0)

    assert result["followupExpectedMargin"] == 15
    assert result["expectedMarginError"] == -5
    assert result["absoluteExpectedMarginError"] == 5
    assert result["conservativeSurvived"] is True
    assert result["marginSurvived"] is True
    assert result["rankingStable"] is True


def test_flipping_history_calibration_readiness_is_evidence_gated():
    rows = [{
        "absoluteExpectedMarginError": 5,
        "conservativeSurvived": True,
        "marginSurvived": True,
        "rankingStable": False,
    }] * 4

    summary = flipping_history.summarise(rows, minimum_calibration_samples=5)
    assert summary["sampleCount"] == 4
    assert summary["meanAbsoluteExpectedMarginError"] == 5
    assert summary["calibrationReady"] is False

    ready = flipping_history.summarise(rows + [rows[0]], minimum_calibration_samples=5)
    assert ready["calibrationReady"] is True
