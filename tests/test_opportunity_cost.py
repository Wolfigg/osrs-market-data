from osrs_market.opportunity_cost import InputCostModel, calculate_profit_view


def test_self_supplied_untradeable_input_is_not_economically_free():
    inputs = [
        InputCostModel("Law rune", quantity=2, market_gp=150),
        InputCostModel("Dark essence block", quantity=1, acquisition_seconds=30, self_supplied=True),
    ]
    view = calculate_profit_view(1000, inputs, opportunity_rate_gp_per_hour=600_000)

    assert view.cash_input_gp == 300
    assert view.cash_profit_gp == 700
    assert view.economic_input_gp > view.cash_input_gp
    assert view.effective_profit_gp < view.cash_profit_gp
    assert "Dark essence block" in view.untradeable_requirements


def test_owned_market_value_can_still_be_economic_cost():
    inputs = [InputCostModel("Steel bar", quantity=1, market_gp=500, self_supplied=True)]
    view = calculate_profit_view(800, inputs)
    assert view.cash_input_gp == 0
    assert view.economic_input_gp == 500
    assert view.cash_profit_gp == 800
    assert view.effective_profit_gp == 300
