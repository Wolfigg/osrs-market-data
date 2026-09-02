from __future__ import annotations

import math
from typing import Any

from .quality import liquidity_warnings
from .tax import ge_tax_per_item

SCENARIOS = (
    "CURRENT_INSTANT",
    "CURRENT_PATIENT_PROXY",
    "HISTORICAL_INSTANT_6H",
    "HISTORICAL_INSTANT_24H",
    "HISTORICAL_INSTANT_7D",
    "HISTORICAL_INSTANT_30D",
    "HISTORICAL_INSTANT_6M",
)


def _window_key_for_scenario(scenario: str) -> str | None:
    if not scenario.startswith("HISTORICAL_INSTANT_"):
        return None
    return scenario.removeprefix("HISTORICAL_INSTANT_").lower()


def _input_price(record: dict[str, Any], scenario: str) -> float | None:
    if scenario == "CURRENT_INSTANT":
        return record["current"].get("high")
    if scenario == "CURRENT_PATIENT_PROXY":
        return record["current"].get("low")
    window = _window_key_for_scenario(scenario)
    return record["windows"].get(window, {}).get("highVwap") if window else None


def _output_price(record: dict[str, Any], scenario: str) -> float | None:
    if scenario == "CURRENT_INSTANT":
        return record["current"].get("low")
    if scenario == "CURRENT_PATIENT_PROXY":
        return record["current"].get("high")
    window = _window_key_for_scenario(scenario)
    return record["windows"].get(window, {}).get("lowVwap") if window else None


def evaluate_method(
    method_id: str,
    method: dict[str, Any],
    item_records: dict[int, dict[str, Any]],
    exempt_item_ids: set[int],
    settings: dict[str, Any],
    generated_at: int,
) -> list[dict[str, Any]]:
    """Evaluate one AFK processing method under each market-execution scenario.

    AFK methods always exit through the Grand Exchange. High Level Alchemy is a
    separate application branch and is intentionally not available as a method
    output strategy here.
    """
    if method.get("enabled", True) is False:
        return []
    return [
        _evaluate_scenario(
            method_id,
            method,
            scenario,
            item_records,
            exempt_item_ids,
            settings,
            generated_at,
        )
        for scenario in SCENARIOS
    ]


def _evaluate_scenario(
    method_id: str,
    method: dict[str, Any],
    scenario: str,
    item_records: dict[int, dict[str, Any]],
    exempt_item_ids: set[int],
    settings: dict[str, Any],
    generated_at: int,
) -> dict[str, Any]:
    warnings: list[str] = []
    missing: list[str] = []

    mechanical_cph = float(method.get("cycles_per_hour", 0))
    theoretical_cph = method.get("theoretical_cycles_per_hour")
    theoretical_cph = float(theoretical_cph) if theoretical_cph is not None else None
    fixed_cost = float(method.get("fixed_cost_gp_per_cycle", 0))
    planned_hours = float(
        method.get(
            "planned_hours_per_day",
            settings.get("methods", {}).get("default_planned_hours_per_day", 1),
        )
    )

    afk_config = method.get("afk", {}) or {}
    afk_interval_seconds = afk_config.get("interval_seconds")
    afk_interval_seconds = float(afk_interval_seconds) if afk_interval_seconds is not None else None
    interaction_windows_per_hour = afk_config.get("interaction_windows_per_hour")
    if interaction_windows_per_hour is None and afk_interval_seconds and afk_interval_seconds > 0:
        interaction_windows_per_hour = 3600.0 / afk_interval_seconds
    elif interaction_windows_per_hour is not None:
        interaction_windows_per_hour = float(interaction_windows_per_hour)

    input_cost = 0.0
    input_details: list[dict[str, Any]] = []
    output_gross = 0.0
    output_tax = 0.0
    output_net = 0.0
    output_details: list[dict[str, Any]] = []
    buy_limit_cycle_caps: list[float] = []

    for entry in method.get("inputs", []):
        item_id = int(entry["item_id"])
        quantity = float(entry.get("quantity", 1))
        record = item_records.get(item_id)
        if record is None:
            missing.append(f"MISSING_ITEM_{item_id}")
            continue

        price = _input_price(record, scenario)
        if price is None:
            missing.append(f"MISSING_INPUT_PRICE_{item_id}")
            continue

        subtotal = quantity * float(price)
        input_cost += subtotal
        limit = record["item"].get("limit")
        buy_via_ge = bool(entry.get("buy_via_ge", True))
        cap = None
        if buy_via_ge and limit is not None and quantity > 0:
            cap = (float(limit) / 4.0) / quantity
            buy_limit_cycle_caps.append(cap)

        input_details.append(
            {
                "itemId": item_id,
                "name": record["item"]["name"],
                "quantity": quantity,
                "price": price,
                "subtotal": subtotal,
                "buyViaGe": buy_via_ge,
                "geBuyLimit": limit,
                "maxCyclesPerHourByLimit": cap,
            }
        )
        if scenario.startswith("CURRENT_"):
            needed_side = "high" if scenario == "CURRENT_INSTANT" else "low"
            _append_current_warning(record, needed_side, warnings)

    for entry in method.get("outputs", []):
        item_id = int(entry["item_id"])
        quantity = float(entry.get("quantity", 1))
        record = item_records.get(item_id)
        if record is None:
            missing.append(f"MISSING_ITEM_{item_id}")
            continue

        ge_price = _output_price(record, scenario)
        if ge_price is None:
            missing.append(f"MISSING_OUTPUT_PRICE_{item_id}")
            continue

        ge_price_rounded = max(math.floor(float(ge_price)), 0)
        tax_each = ge_tax_per_item(ge_price_rounded, item_id, exempt_item_ids)
        ge_net_each = float(ge_price) - tax_each

        output_gross += float(ge_price) * quantity
        output_tax += tax_each * quantity
        output_net += ge_net_each * quantity
        output_details.append(
            {
                "itemId": item_id,
                "name": record["item"]["name"],
                "quantity": quantity,
                "gePrice": ge_price,
                "geTaxPerItem": tax_each,
                "geNetPerItem": ge_net_each,
            }
        )
        if scenario.startswith("CURRENT_"):
            needed_side = "low" if scenario == "CURRENT_INSTANT" else "high"
            _append_current_warning(record, needed_side, warnings)

    total_cost = input_cost + fixed_cost
    profit_per_cycle = output_net - total_cost if not missing else None
    sustainable_cph = min([mechanical_cph, *buy_limit_cycle_caps]) if mechanical_cph > 0 else 0.0
    profit_mechanical = profit_per_cycle * mechanical_cph if profit_per_cycle is not None else None
    profit_sustainable = profit_per_cycle * sustainable_cph if profit_per_cycle is not None else None

    output_units_per_cycle = sum(float(entry.get("quantity", 1)) for entry in method.get("outputs", []))
    output_units_per_hour = output_units_per_cycle * mechanical_cph
    sustainable_output_units_per_hour = output_units_per_cycle * sustainable_cph

    liquidity = _method_liquidity(
        method,
        item_records,
        mechanical_cph,
        planned_hours,
        settings["liquidity"],
    )
    for item in liquidity["outputs"] + liquidity["inputs"]:
        warnings.extend(item["warnings"])
    warnings.extend(missing)
    warnings = list(dict.fromkeys(warnings))

    valid = not missing
    if scenario.startswith("CURRENT_") and any(
        w.startswith("CURRENT_") or w == "CROSSED_CURRENT_PRICE" for w in warnings
    ):
        valid = False
    if scenario == "CURRENT_PATIENT_PROXY":
        warnings.insert(0, "NOT_GUARANTEED_TO_FILL")

    reported_profit_per_cycle = profit_per_cycle if valid else None
    reported_profit_mechanical = profit_mechanical if valid else None
    reported_profit_sustainable = profit_sustainable if valid else None
    gp_per_interaction = None
    if reported_profit_sustainable is not None and interaction_windows_per_hour and interaction_windows_per_hour > 0:
        gp_per_interaction = reported_profit_sustainable / interaction_windows_per_hour

    return {
        "schemaVersion": 2,
        "methodId": method_id,
        "name": method.get("name", method_id),
        "category": method.get("category", "processing"),
        "methodTypes": method.get("method_types", []),
        "audit": method.get("audit", {}),
        "generatedAt": generated_at,
        "scenario": scenario,
        "valid": valid,
        "mechanics": {
            "cyclesPerHour": mechanical_cph,
            "theoreticalCyclesPerHour": theoretical_cph,
            "cyclesPerHourByBuyLimits": sustainable_cph,
            "outputUnitsPerHour": output_units_per_hour,
            "outputUnitsPerHourByBuyLimits": sustainable_output_units_per_hour,
        },
        "afk": {
            "intervalSeconds": afk_interval_seconds,
            "interactionWindowsPerHour": interaction_windows_per_hour,
            "intensity": afk_config.get("intensity"),
            "description": afk_config.get("description", ""),
            "gpPerInteractionWindow": gp_per_interaction,
        },
        "economics": {
            "inputGpPerCycle": input_cost,
            "fixedCostGpPerCycle": fixed_cost,
            "totalCostGpPerCycle": total_cost,
            "outputGrossGeGpPerCycle": output_gross,
            "geTaxGpPerCycle": output_tax,
            "outputNetGeGpPerCycle": output_net,
            "profitGpPerCycle": reported_profit_per_cycle,
            "profitGpPerHourMechanical": reported_profit_mechanical,
            "profitGpPerHourBuyLimitSustainable": reported_profit_sustainable,
        },
        "inputs": input_details,
        "outputs": output_details,
        "liquidity": liquidity,
        "sources": {
            "inputPriceBasis": _input_basis(scenario),
            "outputPriceBasis": _output_basis(scenario),
            "historicalVolumeNote": "Historical observed volume is a liquidity proxy, not executable market depth.",
        },
        "warnings": warnings,
        "requirements": method.get("requirements", {}),
        "account": method.get("account", {}),
        "notes": method.get("notes", ""),
        "reference": method.get("reference"),
    }


def _append_current_warning(record: dict[str, Any], side: str, warnings: list[str]) -> None:
    current = record["current"]
    if current.get(side) is None:
        warnings.append(f"CURRENT_{side.upper()}_MISSING")
    elif current.get(f"{side}Freshness") not in {"fresh", "acceptable"}:
        warnings.append(f"CURRENT_{side.upper()}_STALE")
    if current.get("crossed"):
        warnings.append("CROSSED_CURRENT_PRICE")


def _method_liquidity(
    method: dict[str, Any],
    records: dict[int, dict[str, Any]],
    cycles_per_hour: float,
    planned_hours: float,
    liquidity_settings: dict[str, Any],
) -> dict[str, Any]:
    result = {"plannedHoursPerDay": planned_hours, "inputs": [], "outputs": []}
    for kind in ("inputs", "outputs"):
        for entry in method.get(kind, []):
            item_id = int(entry["item_id"])
            record = records.get(item_id)
            if record is None:
                continue
            quantity_per_cycle = float(entry.get("quantity", 1))
            planned_quantity = quantity_per_cycle * cycles_per_hour * planned_hours
            window_24h = record["windows"].get("24h", {})
            volume_24h = float(window_24h.get("totalVolume") or 0)
            share = planned_quantity / volume_24h * 100.0 if volume_24h > 0 else None
            buy_via_ge = bool(entry.get("buy_via_ge", True)) if kind == "inputs" else False
            row = {
                "itemId": item_id,
                "name": record["item"]["name"],
                "observedVolume6h": record["windows"].get("6h", {}).get("totalVolume"),
                "observedVolume24h": window_24h.get("totalVolume"),
                "observedHighVolume24h": window_24h.get("highVolume"),
                "observedLowVolume24h": window_24h.get("lowVolume"),
                "observedHighVolume6h": record["windows"].get("6h", {}).get("highVolume"),
                "observedLowVolume6h": record["windows"].get("6h", {}).get("lowVolume"),
                "observedVolume7d": record["windows"].get("7d", {}).get("totalVolume"),
                "observedVolume30d": record["windows"].get("30d", {}).get("totalVolume"),
                "plannedQuantity24h": planned_quantity,
                "plannedSharePct24hVolume": share,
                "geBuyLimit": record["item"].get("limit"),
                "fourHourBuyLimitThroughput": record["item"].get("limit") if buy_via_ge else None,
                "warnings": liquidity_warnings(share, liquidity_settings),
            }
            result[kind].append(row)
    return result


def _input_basis(scenario: str) -> str:
    if scenario == "CURRENT_INSTANT":
        return "current observed high"
    if scenario == "CURRENT_PATIENT_PROXY":
        return "current observed low, patient-order proxy"
    return f"{_window_key_for_scenario(scenario)} high VWAP"


def _output_basis(scenario: str) -> str:
    if scenario == "CURRENT_INSTANT":
        return "current observed low minus GE seller tax"
    if scenario == "CURRENT_PATIENT_PROXY":
        return "current observed high minus GE seller tax, patient-order proxy"
    return f"{_window_key_for_scenario(scenario)} low VWAP minus GE seller tax"
