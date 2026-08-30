import pytest

from osrs_market.session_planner_v3 import SessionInputs, calculate_session


def base(**overrides):
    values = dict(
        starting_bankroll_gp=10_000_000,
        duration_hours=4,
        production_rate_per_hour=1000,
        profit_gp_per_unit=100,
        input_cash_cost_gp_per_unit=500,
        input_economic_cost_gp_per_unit=500,
        output_sale_value_gp_per_unit=600,
    )
    values.update(overrides)
    return SessionInputs(**values)


def test_unlimited_bankroll_is_production_limited():
    result = calculate_session(base())
    assert result.processed_units == pytest.approx(4000)
    assert result.theoretical_gp_per_hour == pytest.approx(100_000)
    assert result.realistic_session_profit_gp == pytest.approx(400_000)
    assert result.limiting_factor == "production"


def test_small_bankroll_limits_recycling_rate():
    result = calculate_session(base(starting_bankroll_gp=50_000, output_sell_delay_hours=1))
    assert result.processed_units < 4000
    assert result.bankroll_limited_gp_per_hour < result.production_limited_gp_per_hour
    assert result.limiting_factor == "bankroll"


def test_slow_inputs_and_outputs_limit_session():
    input_limited = calculate_session(base(input_fill_rate_per_hour=300))
    output_limited = calculate_session(base(output_sell_rate_per_hour=250))
    assert input_limited.processed_units == pytest.approx(1200)
    assert input_limited.limiting_factor == "input_fill"
    assert output_limited.processed_units == pytest.approx(1000)
    assert output_limited.limiting_factor == "output_sell"


def test_ge_limit_is_averaged_across_reset_window():
    result = calculate_session(base(ge_buy_limit_4h=2000, ge_limit_reset_hours=4))
    assert result.processed_units == pytest.approx(2000)
    assert result.limiting_factor == "ge_buy_limit"


def test_owned_inventory_reduces_cash_required_but_not_economic_cost():
    result = calculate_session(base(
        starting_bankroll_gp=0,
        duration_hours=1,
        owned_inventory_units=1000,
        owned_inventory_market_value_gp_per_unit=500,
    ))
    assert result.processed_units == pytest.approx(1000)
    assert result.incremental_cash_required_gp == 0
    assert result.market_value_profit_gp == pytest.approx(100_000)
    assert result.cash_flow_profit_gp == pytest.approx(600_000)
