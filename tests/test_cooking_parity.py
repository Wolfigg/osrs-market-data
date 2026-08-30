import json
from pathlib import Path

import pytest

from osrs_market.methods_v2 import cooking_success_probability


@pytest.mark.parametrize("fixture", json.loads(Path("tests/fixtures/cooking_parity.json").read_text(encoding="utf-8")))
def test_backend_cooking_probability_matches_parity_fixture(fixture):
    actual = cooking_success_probability(
        fixture["model"], fixture["level"], fixture["location"], fixture["gauntlets"], fixture["cookingCape"]
    )
    assert actual == pytest.approx(fixture["expected"], abs=1e-12)
