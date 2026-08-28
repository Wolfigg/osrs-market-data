import pytest

from osrs_market.tax import ge_tax_per_item


def test_49_gp_taxable_item_has_zero_tax():
    assert ge_tax_per_item(49, 1, set()) == 0


def test_50_gp_taxable_item_has_one_gp_tax():
    assert ge_tax_per_item(50, 1, set()) == 1


def test_100_gp_taxable_item_has_two_gp_tax():
    assert ge_tax_per_item(100, 1, set()) == 2


def test_large_item_hits_five_million_cap():
    assert ge_tax_per_item(1_000_000_000, 1, set()) == 5_000_000


def test_old_school_bond_is_exempt():
    assert ge_tax_per_item(20_000_000, 13190, {13190}) == 0


def test_negative_sell_price_is_invalid():
    with pytest.raises(ValueError):
        ge_tax_per_item(-1, 1, set())
