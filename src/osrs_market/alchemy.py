from __future__ import annotations

import math
from typing import Any

from .models import LatestPrice, MappingItem
from .quality import liquidity_warnings


def alch_costs(
    item: MappingItem,
    item_buy_price: float | int | None,
    nature_rune_price: float | int | None,
    use_fire_staff: bool,
    fire_rune_price: float | int | None = None,
    fire_runes_per_cast: int = 5,
) -> dict[str, float | None]:
    if item.highalch is None or item_buy_price is None or nature_rune_price is None:
        return {"profit": None, "roiPct": None, "cost": None}
    fire_cost = 0.0
    if not use_fire_staff:
        if fire_rune_price is None:
            return {"profit": None, "roiPct": None, "cost": None}
        fire_cost = float(fire_rune_price) * int(fire_runes_per_cast)
    cost = float(item_buy_price) + float(nature_rune_price) + fire_cost
    profit = float(item.highalch) - cost
    roi = profit / cost * 100.0 if cost > 0 else None
    return {"profit": profit, "roiPct": roi, "cost": cost}


def four_hour_capacity(
    buy_price: float | int,
    nature_rune_price: float | int,
    ge_buy_limit: int | None,
    casts_per_hour: int = 1200,
    available_gp: int | None = None,
    extra_rune_cost_per_cast: float = 0.0,
) -> dict[str, int | None]:
    mechanical = casts_per_hour * 4
    by_limit = ge_buy_limit if ge_buy_limit is not None else mechanical
    capital_per_cast = float(buy_price) + float(nature_rune_price) + float(extra_rune_cost_per_cast)
    by_capital = None
    if available_gp is not None:
        by_capital = math.floor(available_gp / capital_per_cast) if capital_per_cast > 0 else 0
    candidates = [mechanical, by_limit]
    if by_capital is not None:
        candidates.append(by_capital)
    return {
        "mechanicalCasts": mechanical,
        "geBuyLimit": ge_buy_limit,
        "maxByCapital": by_capital,
        "maxQuantity": max(min(candidates), 0),
    }


def preliminary_scan(
    mapping: dict[int, MappingItem],
    latest: dict[int, LatestPrice],
    generated_at: int,
    settings: dict[str, Any],
    exclusions: set[int],
    forced: set[int],
) -> list[dict[str, Any]]:
    alch_settings = settings["alchemy"]
    nature_id = int(alch_settings["nature_rune_item_id"])
    nature_latest = latest.get(nature_id)
    nature_high = nature_latest.high if nature_latest else None
    max_age = int(alch_settings.get("preliminary_max_age_seconds", 86400))
    if nature_high is None or nature_latest is None or nature_latest.high_time is None:
        return []
    if max(generated_at - nature_latest.high_time, 0) > max_age:
        return []
    use_fire_staff = bool(alch_settings.get("use_fire_staff", True))
    fire_cost = 0
    if not use_fire_staff:
        fire_id = int(alch_settings.get("fire_rune_item_id", 554))
        fire_latest = latest.get(fire_id)
        if fire_latest is None or fire_latest.high is None or fire_latest.high_time is None:
            return []
        if max(generated_at - fire_latest.high_time, 0) > max_age:
            return []
        fire_cost = fire_latest.high * int(alch_settings.get("fire_runes_per_cast", 5))

    margin_floor = float(alch_settings.get("preliminary_margin_floor_gp", -50))
    members_filter = str(alch_settings.get("members_filter", "all")).lower()
    candidates: list[dict[str, Any]] = []

    for item_id, item in mapping.items():
        if item_id == nature_id or item_id in exclusions:
            continue
        if item.highalch is None:
            continue
        if members_filter == "f2p" and item.members:
            continue
        if members_filter == "members" and not item.members:
            continue
        price = latest.get(item_id)
        if price is None or price.high is None or price.high_time is None:
            continue
        age = max(generated_at - price.high_time, 0)
        margin = item.highalch - price.high - nature_high - fire_cost
        if item_id not in forced and (age > max_age or margin < margin_floor):
            continue
        candidates.append(
            {
                "itemId": item_id,
                "name": item.name,
                "members": item.members,
                "preliminaryMargin": margin,
                "buyPrice": price.high,
                "buyPriceAgeSeconds": age,
                "highAlch": item.highalch,
                "geBuyLimit": item.limit,
            }
        )

    candidates.sort(key=lambda row: (row["preliminaryMargin"], -row["buyPriceAgeSeconds"]), reverse=True)
    limit = int(alch_settings.get("candidate_timeseries_limit", 100))
    forced_rows = [row for row in candidates if row["itemId"] in forced]
    normal_rows = [row for row in candidates if row["itemId"] not in forced]
    selected = normal_rows[:limit]
    existing = {row["itemId"] for row in selected}
    selected.extend(row for row in forced_rows if row["itemId"] not in existing)
    return selected


def _is_fresh(timestamp: int | None, generated_at: int, acceptable_seconds: int) -> bool:
    return timestamp is not None and max(generated_at - timestamp, 0) <= acceptable_seconds


def _historical_alch(
    item: MappingItem,
    key: str,
    windows: dict[str, dict[str, Any]],
    nature_windows: dict[str, dict[str, Any]],
    use_fire_staff: bool,
    fire_windows: dict[str, dict[str, Any]] | None,
    fire_runes_per_cast: int,
) -> dict[str, Any]:
    item_price = windows.get(key, {}).get("highVwap")
    nature_price = nature_windows.get(key, {}).get("highVwap")
    fire_price = (fire_windows or {}).get(key, {}).get("highVwap") if not use_fire_staff else None
    result = alch_costs(
        item,
        item_price,
        nature_price,
        use_fire_staff,
        fire_price,
        fire_runes_per_cast,
    )
    return {
        "valid": result["profit"] is not None,
        "itemHighVwap": item_price,
        "natureHighVwap": nature_price,
        "fireHighVwap": fire_price,
        "profitPerCast": result["profit"],
        "roiPct": result["roiPct"],
    }


def build_alchemy_candidate(
    item: MappingItem,
    latest_item: LatestPrice,
    latest_nature: LatestPrice,
    windows: dict[str, dict[str, Any]],
    nature_windows: dict[str, dict[str, Any]],
    generated_at: int,
    settings: dict[str, Any],
    latest_fire: LatestPrice | None = None,
    fire_windows: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    alch_settings = settings["alchemy"]
    liquidity_settings = settings["liquidity"]
    use_fire_staff = bool(alch_settings.get("use_fire_staff", True))
    casts_per_hour = int(alch_settings.get("casts_per_hour", 1200))
    xp_per_cast = int(alch_settings.get("xp_per_cast", 65))
    fire_runes_per_cast = int(alch_settings.get("fire_runes_per_cast", 5))
    fire_rune_price = latest_fire.high if latest_fire is not None else None
    available_gp = alch_settings.get("available_gp")
    available_gp = int(available_gp) if available_gp is not None else None
    acceptable_seconds = int(settings.get("freshness", {}).get("acceptable_seconds", 7200))
    nature_fresh = _is_fresh(latest_nature.high_time, generated_at, acceptable_seconds)
    fire_fresh = use_fire_staff or (latest_fire is not None and _is_fresh(latest_fire.high_time, generated_at, acceptable_seconds))
    instant_fresh = _is_fresh(latest_item.high_time, generated_at, acceptable_seconds) and nature_fresh and fire_fresh
    patient_fresh = _is_fresh(latest_item.low_time, generated_at, acceptable_seconds) and nature_fresh and fire_fresh

    instant = alch_costs(item, latest_item.high, latest_nature.high, use_fire_staff, fire_rune_price, fire_runes_per_cast)
    patient = alch_costs(item, latest_item.low, latest_nature.high, use_fire_staff, fire_rune_price, fire_runes_per_cast)
    hist6 = _historical_alch(item, "6h", windows, nature_windows, use_fire_staff, fire_windows, fire_runes_per_cast)
    hist24 = _historical_alch(item, "24h", windows, nature_windows, use_fire_staff, fire_windows, fire_runes_per_cast)
    hist7 = _historical_alch(item, "7d", windows, nature_windows, use_fire_staff, fire_windows, fire_runes_per_cast)
    hist30 = _historical_alch(item, "30d", windows, nature_windows, use_fire_staff, fire_windows, fire_runes_per_cast)
    hist6m = _historical_alch(item, "6m", windows, nature_windows, use_fire_staff, fire_windows, fire_runes_per_cast)

    extra_fire_cost = 0.0
    if not use_fire_staff and fire_rune_price is not None:
        extra_fire_cost = float(fire_rune_price) * fire_runes_per_cast

    capacity = None
    if latest_item.high is not None and latest_nature.high is not None and (use_fire_staff or fire_rune_price is not None):
        capacity = four_hour_capacity(
            latest_item.high,
            latest_nature.high,
            item.limit,
            casts_per_hour=casts_per_hour,
            available_gp=available_gp,
            extra_rune_cost_per_cast=extra_fire_cost,
        )

    max_quantity = capacity["maxQuantity"] if capacity else 0
    profit_per_4h = instant["profit"] * max_quantity if instant["profit"] is not None and instant_fresh else None
    capital_required = instant["cost"] * max_quantity if instant["cost"] is not None and instant_fresh else None
    volume_24h = int(windows.get("24h", {}).get("totalVolume") or 0)
    volume_7d = int(windows.get("7d", {}).get("totalVolume") or 0)
    planned_share = max_quantity / volume_24h * 100.0 if volume_24h > 0 and max_quantity else None
    liquidity_warn = liquidity_warnings(planned_share, liquidity_settings)

    age = max(generated_at - latest_item.high_time, 0) if latest_item.high_time is not None else None
    freshness_max = int(alch_settings.get("preliminary_max_age_seconds", 86400))
    warnings = list(liquidity_warn)
    if age is None or age > freshness_max:
        warnings.append("STALE_CURRENT_BUY_PRICE")
    if not instant_fresh:
        warnings.append("CURRENT_INSTANT_UNUSABLE")
    if not patient_fresh:
        warnings.append("CURRENT_PATIENT_PROXY_UNUSABLE")
    if item.limit is None:
        warnings.append("MISSING_BUY_LIMIT")
    if not use_fire_staff and fire_rune_price is None:
        warnings.append("MISSING_FIRE_RUNE_PRICE")

    return {
        "itemId": item.id,
        "name": item.name,
        "members": item.members,
        "f2p": not item.members,
        "highAlchValue": item.highalch,
        "geBuyLimit": item.limit,
        "buyPriceAgeSeconds": age,
        "currentInstant": {
            "valid": instant["profit"] is not None and instant_fresh,
            "buyPrice": latest_item.high,
            "natureRunePrice": latest_nature.high,
            "fireRunePrice": fire_rune_price if not use_fire_staff else None,
            "profitPerCast": instant["profit"] if instant_fresh else None,
            "roiPct": instant["roiPct"] if instant_fresh else None,
            "profitPerHourAtMechanicalRate": instant["profit"] * casts_per_hour if instant["profit"] is not None and instant_fresh else None,
        },
        "currentPatientProxy": {
            "valid": patient["profit"] is not None and patient_fresh,
            "label": "NOT GUARANTEED TO FILL",
            "buyPrice": latest_item.low,
            "natureRunePrice": latest_nature.high,
            "fireRunePrice": fire_rune_price if not use_fire_staff else None,
            "profitPerCast": patient["profit"] if patient_fresh else None,
            "roiPct": patient["roiPct"] if patient_fresh else None,
        },
        "historicalInstant6h": hist6,
        "historicalInstant24h": hist24,
        "historicalInstant7d": hist7,
        "historicalInstant30d": hist30,
        "historicalInstant6m": hist6m,
        "capacity4h": capacity,
        "profitPer4hGeLimit": profit_per_4h,
        "capitalRequired": capital_required,
        "magicXpPerHour": casts_per_hour * xp_per_cast,
        "magicXpPer4hBatch": max_quantity * xp_per_cast,
        "volume24h": volume_24h,
        "volume7d": volume_7d,
        "highVwap24h": windows.get("24h", {}).get("highVwap"),
        "priceChangePct24h": windows.get("24h", {}).get("changePct"),
        "plannedSharePct24hVolume": planned_share,
        "warnings": warnings,
    }
