from pathlib import Path

from osrs_market.config import load_yaml
from osrs_market.validation_v2 import validate_catalogue_v2


def test_validation_v2_rejects_invalid_probabilities_and_bounds():
    methods = {
        "bad": {
            "enabled": True,
            "cycles_per_hour": 100,
            "requirements": {"cooking": 120},
            "inputs": [{"item_name": "Input", "quantity": 1, "probability": 1.2}],
            "outputs": [{"item_name": "Output", "quantity": 1, "quantity_minimum": 2, "quantity_expected": 1, "quantity_maximum": 0.5}],
        }
    }
    report = validate_catalogue_v2(methods)
    assert not report.valid
    assert any("probability" in error for error in report.errors)
    assert any("Cooking" in error or "cooking" in error for error in report.errors)
    assert any("minimum quantity exceeds expected" in error for error in report.errors)
    assert any("expected quantity exceeds maximum" in error for error in report.errors)


def test_current_production_catalogue_passes_mechanical_validation_v2():
    methods = load_yaml(Path("config/methods.yaml"))["methods"]
    report = validate_catalogue_v2(methods)
    report.raise_for_errors()
