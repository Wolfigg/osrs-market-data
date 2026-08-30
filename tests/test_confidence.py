import pytest

from osrs_market.confidence import ConfidenceComponents, method_confidence


def test_confidence_retains_components_and_explicit_weights():
    result = method_confidence(ConfidenceComponents(100, 95, 72, 68, 80, 93))
    assert result["components"]["mechanical"] == 100
    assert result["components"]["liquidity"] == 72
    assert result["components"]["sourceFreshness"] == 93
    assert sum(result["weights"].values()) == pytest.approx(1.0, abs=1e-5)
    assert 0 <= result["overall"] <= 100


def test_confidence_rejects_incomplete_weight_configuration():
    with pytest.raises(ValueError, match="missing confidence weights"):
        method_confidence(ConfidenceComponents(100, 100, 100, 100, 100, 100), {"mechanical": 1.0})
