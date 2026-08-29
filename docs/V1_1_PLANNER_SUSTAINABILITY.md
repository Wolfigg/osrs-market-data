# OSRS Profit Finder V1.1 - Planner, Sustainability and Calculation Semantics

Updated: 2026-08-29

This document records the public semantics introduced after the original two-tool backlog was completed. The goal is to make bankroll/session rankings and liquidity labels auditable rather than opaque.

## Production validation baseline

Before this V1.1 wave, the refactored production pipeline was validated in GitHub Actions and on GitHub Pages:

- full historical bootstrap completed successfully
- 582 time-series requests completed with 0 failures
- 24H, 7D and 30D derived history was written and cached
- the full bootstrap completed in about 2 minutes 26 seconds
- the lightweight live collector evaluates the AFK catalogue from `/latest` without time-series requests
- the public page was verified with populated Current, 24H, 7D, 30D, Recommended GP/hour and Stability values

The split live/history refresh architecture remains unchanged by V1.1.

## Bankroll and session planner

The planner is browser-local and stores only:

- available cash
- desired session length

No account, RuneLite or Jagex integration is required.

### Working-capital assumption

The planner uses a conservative one-hour working-capital model. It does not assume that the player has enough GP to pre-buy the entire multi-hour session at once.

For a method:

```text
bankroll_rate = available_cash / capital_per_cycle
session_cycles_per_hour = min(
    mechanical_cycles_per_hour,
    ge_buy_limit_cycles_per_hour,
    bankroll_rate
)
```

For zero-input gathering methods, bankroll does not constrain the rate.

The displayed session profit is:

```text
session_profit = profit_per_cycle
               * session_cycles_per_hour
               * selected_hours
```

The planner reports the tightest deterministic constraint as one of:

- Mechanical rate
- Bankroll
- GE buy limit
- Market liquidity

Market liquidity is currently a warning/diagnostic constraint, not a simulated order-book depth cap. OSRS Wiki/RuneLite observations do not provide guaranteed executable market depth, so V1.1 does not invent a hard fill model.

## Sustainability model

Sustainability is separate from historical Stability.

Stability asks whether the current profit is consistent with 24H/7D/30D references.

Sustainability asks whether the method's throughput looks practical relative to GE buy limits and recent observed 24H volume.

### Throughput retention

```text
throughput_ratio = ge_limit_sustainable_cycles_per_hour
                 / mechanical_cycles_per_hour
```

### Market-share pressure

For every consumed or produced item:

```text
one_hour_share_pct = method_units_per_hour
                   / observed_24h_volume
                   * 100
```

The method uses the largest input/output share as its public market-pressure indicator.

### Public sustainability states

```text
GE limited:
    throughput ratio < 50%

Thin market:
    max one-hour share >= 10%

Constrained:
    throughput ratio < 85%

Liquidity watch:
    max one-hour share >= 5%

Liquidity unknown:
    no usable 24H volume reference

Moderate:
    throughput ratio < 95%
    OR max one-hour share >= 1%

Strong:
    throughput ratio >= 95%
    AND max one-hour share < 1%
```

The session detail view also scales the market-share estimate to the user's selected hours and bankroll-constrained throughput. This remains a liquidity proxy, not guaranteed fill capacity.

## Transparent calculation breakdown

Expanded AFK methods expose the current calculation components used by the application.

For inputs:

- quantity per cycle
- observed current buy-side price used by the method calculation
- subtotal per cycle
- GE buy limit where applicable

For outputs:

- quantity per cycle
- observed current sell-side price used by the method calculation
- GE tax per item
- net output value

The public equation is equivalent to:

```text
input_cost_per_cycle
+ fixed_coin_cost_per_cycle
-> output_net_after_ge_tax
= profit_per_cycle
```

Then:

```text
profit_per_cycle
* GE-limit-sustainable cycles per hour
= current GP/hour
```

The detail view separately shows mechanical cycles/hour and GE-limit-sustainable cycles/hour so a reduced rate is visible rather than hidden inside the final GP/hour number.

## Public/private boundary

V1.1 exposes only calculation fields needed to explain the public ranking. It does not expose raw time series, collector diagnostics, API health internals or the removed Market Explorer.

High Alch remains a separate active-play branch and is not used as an AFK exit strategy.
