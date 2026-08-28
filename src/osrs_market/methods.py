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


def _rune_price(record: dict[str, Any] | None, scenario: str) -> float | None:
    if record is None:
        return None
    if scenario.startswith("HISTORICAL_INSTANT_"):
        window = _window_key_for_scenario(scenario)
        return record["windows"].get(window, {}).get("highVwap") if window else None
    return record["current"].get("high")


def _alchemy_rune_cost(item_records: dict[int, dict[str, Any]], scenario: str, settings: dict[str, Any], nature_id: int) -> dict[str, float | None]:
    nature_price = _rune_price(item_records.get(nature_id), scenario)
    use_fire_staff = bool(settings.get("alchemy", {}).get("use_fire_staff", True))
    fire_price = None
    fire_cost = 0.0
    if not use_fire_staff:
        fire_id = int(settings.get("alchemy", {}).get("fire_rune_item_id", 554))
        fire_price = _rune_price(item_records.get(fire_id), scenario)
        if fire_price is not None:
            fire_cost = float(fire_price) * int(settings.get("alchemy", {}).get("fire_runes_per_cast", 5))
    total = None if nature_price is None or (not use_fire_staff and fire_price is None) else float(nature_price) + fire_cost
    return {"naturePrice": nature_price, "firePrice": fire_price, "totalPerCast": total}


def evaluate_method(
    method_id: str,
    method: dict[str, Any],
    item_records: dict[int, dict[str, Any]],
    exempt_item_ids: set[int],
    settings: dict[str, Any],
    nature_rune_item_id: int,
    generated_at: int,
) -> list[dict[str, Any]]:
    if method.get("enabled", True) is False:
        return []
    results = []
    for scenario in SCENARIOS:
        results.append(
            _evaluate_scenario(
                method_id,
                method,
                scenario,
                item_records,
                exempt_item_ids,
                settings,
                nature_rune_item_id,
                generated_at,
            )
        )
    return results


def _evaluate_scenario(
    method_id: str,
    method: dict[str, Any],
    scenario: str,
    item_records: dict[int, dict[str, Any]],
    exempt_item_ids: set[int],
    settings: dict[str, Any],
    nature_rune_item_id: int,
    generated_at: int,
) -> dict[str, Any]:
    warnings: list[str] = []
    missing: list[str] = []
    mechanical_cph = float(method.get("cycles_per_hour", 0))
    fixed_cost = float(method.get("fixed_cost_gp_per_cycle", 0))
    planned_hours = float(method.get("planned_hours_per_day", settings.get("methods", {}).get("default_planned_hours_per_day", 1)))
    input_cost = 0.0
    input_details: list[dict[str, Any]] = []
    output_gross = 0.0
    output_tax = 0.0
    output_net = 0.0
    output_details: list[dict[str, Any]] = []
    buy_limit_cycle_caps: list[float] = []
    alch_units_per_cycle = 0.0
    rune_cost = _alchemy_rune_cost(item_records, scenario, settings, nature_rune_item_id)
    nature_price = rune_cost["naturePrice"]
    alchemy_rune_cost = rune_cost["totalPerCast"]

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
        alch_value = record["item"].get("highalch")
        alch_net_each = None
        if alch_value is not None and alchemy_rune_cost is not None:
            alch_net_each = float(alch_value) - float(alchemy_rune_cost)

        exit_strategy = str(entry.get("exit", "ge")).lower()
        chosen_exit = "GE"
        chosen_net_each = ge_net_each
        if exit_strategy == "high_alch":
            if alch_net_each is None:
                missing.append(f"MISSING_ALCH_EXIT_{item_id}")
            else:
                chosen_exit = "HIGH_ALCH"
                chosen_net_each = alch_net_each
                alch_units_per_cycle += quantity
        elif exit_strategy == "best_immediate" and alch_net_each is not None and alch_net_each > ge_net_each:
            chosen_exit = "HIGH_ALCH"
            chosen_net_each = alch_net_each
            alch_units_per_cycle += quantity

        if chosen_exit == "HIGH_ALCH" and scenario.startswith("CURRENT_"):
            nature_record = item_records.get(nature_rune_item_id)
            if nature_record is not None:
                _append_current_warning(nature_record, "high", warnings)
            if not bool(settings.get("alchemy", {}).get("use_fire_staff", True)):
                fire_id = int(settings.get("alchemy", {}).get("fire_rune_item_id", 554))
                fire_record = item_records.get(fire_id)
                if fire_record is not None:
                    _append_current_warning(fire_record, "high", warnings)

        output_gross += float(ge_price) * quantity
        output_tax += tax_each * quantity
        output_net += chosen_net_each * quantity
        output_details.append(
            {
                "itemId": item_id,
                "name": record["item"]["name"],
                "quantity": quantity,
                "gePrice": ge_price,
                "geTaxPerItem": tax_each,
                "geNetPerItem": ge_net_each,
                "highAlchValue": alch_value,
                "natureRunePrice": nature_price,
                "fireRunePrice": rune_cost["firePrice"],
                "alchemyRuneCostPerCast": alchemy_rune_cost,
                "alchNetPerItem": alch_net_each,
                "configuredExit": exit_strategy,
                "chosenExit": chosen_exit,
                "chosenNetPerItem": chosen_net_each,
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

    combined_cph = mechanical_cph
    profit_with_sequential_alch = profit_mechanical
    if mechanical_cph > 0 and alch_units_per_cycle > 0:
        processing_seconds_per_cycle = 3600.0 / mechanical_cph
        alch_seconds_per_cycle = 3.0 * alch_units_per_cycle
        combined_cph = 3600.0 / (processing_seconds_per_cycle + alch_seconds_per_cycle)
        profit_with_sequential_alch = profit_per_cycle * combined_cph if profit_per_cycle is not None else None

    liquidity = _method_liquidity(method, item_records, mechanical_cph, planned_hours, settings["liquidity"])
    for item in liquidity["outputs"] + liquidity["inputs"]:
        warnings.extend(item["warnings"])
    warnings.extend(missing)
    warnings = list(dict.fromkeys(warnings))

    valid = not missing
    if scenario.startswith("CURRENT_") and any(w.startswith("CURRENT_") or w == "CROSSED_CURRENT_PRICE" for w in warnings):
        valid = False
    if scenario == "CURRENT_PATIENT_PROXY":
        warnings.insert(0, "NOT_GUARANTEED_TO_FILL")

    reported_profit_per_cycle = profit_per_cycle if valid else None
    reported_profit_mechanical = profit_mechanical if valid else None
    reported_profit_sustainable = profit_sustainable if valid else None
    reported_profit_sequential_alch = profit_with_sequential_alch if valid else None

    return {
        "schemaVersion": 1,
        "methodId": method_id,
        "name": method.get("name", method_id),
        "generatedAt": generated_at,
        "scenario": scenario,
        "valid": valid,
        "mechanics": {
            "cyclesPerHour": mechanical_cph,
            "cyclesPerHourByBuyLimits": sustainable_cph,
            "combinedCyclesPerHourWithSequentialAlch": combined_cph,
            "alchUnitsPerCycle": alch_units_per_cycle,
        },
        "economics": {
            "inputGpPerCycle": input_cost,
            "fixedCostGpPerCycle": fixed_cost,
            "totalCostGpPerCycle": total_cost,
            "outputGrossGeGpPerCycle": output_gross,
            "geTaxGpPerCycle": output_tax,
            "outputChosenNetGpPerCycle": output_net,
            "profitGpPerCycle": reported_profit_per_cycle,
            "profitGpPerHourMechanical": reported_profit_mechanical,
            "profitGpPerHourBuyLimitSustainable": reported_profit_sustainable,
            "profitGpPerHourAlchTimeExcluded": reported_profit_mechanical,
            "profitGpPerHourSequentialAlchIncluded": reported_profit_sequential_alch,
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
        "account": method.get("account", {}),
        "notes": method.get("notes", ""),
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
            volume_24h = float(record["windows"].get("24h", {}).get("totalVolume") or 0)
            share = planned_quantity / volume_24h * 100.0 if volume_24h > 0 else None
            buy_via_ge = bool(entry.get("buy_via_ge", True)) if kind == "inputs" else False
            row = {
                "itemId": item_id,
                "name": record["item"]["name"],
                "observedVolume6h": record["windows"].get("6h", {}).get("totalVolume"),
                "observedVolume24h": record["windows"].get("24h", {}).get("totalVolume"),
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
        return "current observed low"
    if scenario == "CURRENT_PATIENT_PROXY":
        return "current observed high, patient-order proxy"
    return f"{_window_key_for_scenario(scenario)} low VWAP"
