from __future__ import annotations

from dataclasses import dataclass, field
from math import floor
from typing import Any


@dataclass(frozen=True, slots=True)
class InventoryHolding:
    item_name: str
    quantity: float
    market_value_gp_each: float

    @property
    def market_value_gp(self) -> float:
        return max(0.0, self.quantity) * max(0.0, self.market_value_gp_each)


@dataclass(frozen=True, slots=True)
class SessionInputs:
    starting_bankroll_gp: float
    duration_hours: float
    production_rate_per_hour: float
    profit_gp_per_unit: float
    input_cash_cost_gp_per_unit: float
    input_economic_cost_gp_per_unit: float | None = None
    output_sale_value_gp_per_unit: float | None = None
    input_fill_rate_per_hour: float | None = None
    output_sell_rate_per_hour: float | None = None
    ge_buy_limit_4h: float | None = None
    ge_limit_reset_hours: float = 4.0
    input_fill_delay_hours: float = 0.0
    output_sell_delay_hours: float = 0.0
    owned_inventory_units: float = 0.0
    owned_inventory_market_value_gp_per_unit: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SessionResult:
    theoretical_gp_per_hour: float
    production_limited_gp_per_hour: float
    liquidity_limited_gp_per_hour: float
    bankroll_limited_gp_per_hour: float
    realistic_session_profit_gp: float
    market_value_profit_gp: float
    cash_flow_profit_gp: float
    capital_locked_gp: float
    incremental_cash_required_gp: float
    idle_time_hours: float
    processed_units: float
    production_cycles: float
    limiting_factor: str
    assumptions: dict[str, Any]


def _ge_limit_rate(limit_4h: float | None, reset_hours: float) -> float:
    if limit_4h is None:
        return float("inf")
    return max(0.0, limit_4h) / max(1e-9, reset_hours)


def calculate_session(inputs: SessionInputs) -> SessionResult:
    duration = max(0.0, float(inputs.duration_hours))
    production_rate = max(0.0, float(inputs.production_rate_per_hour))
    profit_per_unit = float(inputs.profit_gp_per_unit)
    input_cash = max(0.0, float(inputs.input_cash_cost_gp_per_unit))
    input_economic = max(0.0, float(inputs.input_economic_cost_gp_per_unit if inputs.input_economic_cost_gp_per_unit is not None else input_cash))
    sale_value = max(0.0, float(inputs.output_sale_value_gp_per_unit if inputs.output_sale_value_gp_per_unit is not None else input_cash + profit_per_unit))

    if duration <= 0 or production_rate <= 0:
        return SessionResult(0, 0, 0, 0, 0, 0, 0, 0, 0, duration, 0, 0, "duration", {"durationHours": duration})

    input_fill_rate = max(0.0, float(inputs.input_fill_rate_per_hour)) if inputs.input_fill_rate_per_hour is not None else float("inf")
    output_sell_rate = max(0.0, float(inputs.output_sell_rate_per_hour)) if inputs.output_sell_rate_per_hour is not None else float("inf")
    ge_rate = _ge_limit_rate(inputs.ge_buy_limit_4h, inputs.ge_limit_reset_hours)

    liquidity_rate = min(production_rate, input_fill_rate, output_sell_rate, ge_rate)
    bankroll = max(0.0, float(inputs.starting_bankroll_gp))
    owned = max(0.0, float(inputs.owned_inventory_units))

    # Capital cannot be recycled until produced outputs have cleared. This turns
    # sell delay into a working-capital requirement rather than pretending the
    # proceeds are immediately reusable.
    recycling_delay = max(0.0, float(inputs.output_sell_delay_hours))
    fill_delay = max(0.0, float(inputs.input_fill_delay_hours))
    active_window = max(0.0, duration - fill_delay)
    concurrency_hours = max(1.0 / max(production_rate, 1e-9), recycling_delay + 1.0 / max(production_rate, 1e-9))
    units_financed_by_cash = bankroll / input_cash if input_cash > 0 else float("inf")
    bankroll_rate = units_financed_by_cash / concurrency_hours if units_financed_by_cash != float("inf") else float("inf")

    sustainable_rate = min(liquidity_rate, bankroll_rate) if owned <= 0 else liquidity_rate
    theoretical_units = production_rate * active_window
    market_units = liquidity_rate * active_window

    # Owned materials can bootstrap production without cash, but they still carry
    # economic value. After they are exhausted, ordinary bankroll recycling rules
    # apply to additional units.
    owned_used = min(owned, market_units)
    cash_window_units = max(0.0, sustainable_rate * active_window)
    processed_units = min(market_units, max(owned_used, owned_used + cash_window_units))

    if owned_used >= market_units:
        processed_units = market_units
        bankroll_rate_effective = liquidity_rate
    else:
        remaining_market_units = market_units - owned_used
        cash_units = min(remaining_market_units, cash_window_units)
        processed_units = owned_used + cash_units
        bankroll_rate_effective = processed_units / active_window if active_window > 0 else 0.0

    produced_over_time = processed_units / active_window if active_window > 0 else 0.0
    unsold_units = 0.0
    if output_sell_rate != float("inf"):
        sold_capacity = max(0.0, output_sell_rate * max(0.0, active_window - recycling_delay))
        unsold_units = max(0.0, processed_units - sold_capacity)
    capital_locked = unsold_units * sale_value

    cash_purchased_units = max(0.0, processed_units - owned_used)
    incremental_cash_required = min(bankroll, cash_purchased_units * input_cash)

    economic_cost = processed_units * input_economic
    revenue = processed_units * sale_value
    market_value_profit = revenue - economic_cost
    cash_outlay = cash_purchased_units * input_cash
    cash_flow_profit = revenue - cash_outlay

    theoretical_gph = production_rate * profit_per_unit
    production_gph = theoretical_gph
    liquidity_gph = liquidity_rate * profit_per_unit
    bankroll_gph = bankroll_rate_effective * profit_per_unit
    realistic_profit = processed_units * profit_per_unit

    limiting_factor = "production"
    candidates = {
        "production": production_rate,
        "input_fill": input_fill_rate,
        "output_sell": output_sell_rate,
        "ge_buy_limit": ge_rate,
        "bankroll": bankroll_rate if owned <= 0 else float("inf"),
    }
    finite = {key: value for key, value in candidates.items() if value != float("inf")}
    if finite:
        limiting_factor = min(finite, key=finite.get)
    if fill_delay >= duration:
        limiting_factor = "input_fill_delay"

    idle_time = max(0.0, duration - (processed_units / production_rate if production_rate > 0 else 0.0))
    cycles = processed_units
    return SessionResult(
        theoretical_gp_per_hour=theoretical_gph,
        production_limited_gp_per_hour=production_gph,
        liquidity_limited_gp_per_hour=liquidity_gph,
        bankroll_limited_gp_per_hour=bankroll_gph,
        realistic_session_profit_gp=realistic_profit,
        market_value_profit_gp=market_value_profit,
        cash_flow_profit_gp=cash_flow_profit,
        capital_locked_gp=capital_locked,
        incremental_cash_required_gp=incremental_cash_required,
        idle_time_hours=idle_time,
        processed_units=processed_units,
        production_cycles=cycles,
        limiting_factor=limiting_factor,
        assumptions={
            "activeWindowHours": active_window,
            "inputFillDelayHours": fill_delay,
            "outputSellDelayHours": recycling_delay,
            "ownedInventoryUsed": owned_used,
            "geLimitRatePerHour": None if ge_rate == float("inf") else ge_rate,
            "inputFillRatePerHour": None if input_fill_rate == float("inf") else input_fill_rate,
            "outputSellRatePerHour": None if output_sell_rate == float("inf") else output_sell_rate,
        },
    )
