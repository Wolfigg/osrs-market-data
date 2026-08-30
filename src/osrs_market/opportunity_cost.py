from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class InputCostModel:
    name: str
    quantity: float = 1.0
    market_gp: float | None = None
    acquisition_seconds: float | None = None
    opportunity_cost_gp: float | None = None
    self_supplied: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def cash_cost(self) -> float:
        if self.self_supplied:
            return 0.0
        return max(0.0, float(self.market_gp or 0.0) * self.quantity)

    def economic_cost(self, *, opportunity_rate_gp_per_hour: float | None = None) -> float:
        market = max(0.0, float(self.market_gp or 0.0) * self.quantity)
        explicit = max(0.0, float(self.opportunity_cost_gp or 0.0) * self.quantity)
        time_cost = 0.0
        if opportunity_rate_gp_per_hour and self.acquisition_seconds:
            time_cost = max(0.0, float(self.acquisition_seconds) / 3600.0 * opportunity_rate_gp_per_hour * self.quantity)
        if self.self_supplied:
            return max(explicit, time_cost, market)
        return market + explicit + time_cost


@dataclass(frozen=True, slots=True)
class ProfitView:
    revenue_gp: float
    cash_input_gp: float
    economic_input_gp: float
    cash_profit_gp: float
    effective_profit_gp: float
    untradeable_requirements: tuple[str, ...]


def calculate_profit_view(
    revenue_gp: float,
    inputs: list[InputCostModel],
    *,
    fixed_cash_cost_gp: float = 0.0,
    fixed_economic_cost_gp: float | None = None,
    opportunity_rate_gp_per_hour: float | None = None,
) -> ProfitView:
    cash_inputs = sum(item.cash_cost for item in inputs) + max(0.0, fixed_cash_cost_gp)
    economic_inputs = sum(item.economic_cost(opportunity_rate_gp_per_hour=opportunity_rate_gp_per_hour) for item in inputs)
    economic_inputs += max(0.0, fixed_cash_cost_gp if fixed_economic_cost_gp is None else fixed_economic_cost_gp)
    untradeable = tuple(item.name for item in inputs if item.self_supplied or item.market_gp is None)
    revenue = float(revenue_gp)
    return ProfitView(
        revenue_gp=revenue,
        cash_input_gp=cash_inputs,
        economic_input_gp=economic_inputs,
        cash_profit_gp=revenue - cash_inputs,
        effective_profit_gp=revenue - economic_inputs,
        untradeable_requirements=untradeable,
    )
