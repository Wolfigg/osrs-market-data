from __future__ import annotations

from typing import Any

from .models import LatestPrice, MappingItem
from .tax import ge_tax_per_item


def _number(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _age(timestamp: int | None, generated_at: int) -> int | None:
    if timestamp is None or timestamp <= 0:
        return None
    return max(0, generated_at - int(timestamp))


def _freshness(age_seconds: int | None, settings: dict[str, Any]) -> dict[str, str]:
    if age_seconds is None:
        return {"state": "unknown", "label": "Unknown"}
    fresh = int(settings["freshness"]["fresh_seconds"])
    acceptable = int(settings["freshness"]["acceptable_seconds"])
    very_stale = int(settings["freshness"]["very_stale_seconds"])
    if age_seconds <= fresh:
        return {"state": "fresh", "label": "Fresh"}
    if age_seconds <= acceptable:
        return {"state": "recent", "label": "Recent"}
    if age_seconds <= very_stale:
        return {"state": "stale", "label": "Stale"}
    return {"state": "very_stale", "label": "Very stale"}


def _margin(buy_price: float | None, sell_price: float | None, item_id: int, exempt_ids: set[int]) -> dict[str, float | int | None]:
    if buy_price is None or sell_price is None or buy_price <= 0 or sell_price <= 0:
        return {"tax": None, "netSell": None, "margin": None, "roi": None}
    sell_int = int(sell_price)
    tax = ge_tax_per_item(sell_int, item_id, exempt_ids)
    net_sell = sell_price - tax
    margin = net_sell - buy_price
    return {
        "tax": tax,
        "netSell": net_sell,
        "margin": margin,
        "roi": margin / buy_price * 100.0,
    }


def _window(row: dict[str, Any] | None, item_id: int, exempt_ids: set[int]) -> dict[str, float | int | None]:
    if not row:
        return {
            "buyPrice": None,
            "sellPrice": None,
            "tax": None,
            "netSell": None,
            "margin": None,
            "roi": None,
            "buyFlow": None,
            "sellFlow": None,
            "balancedFlow": None,
            "buySellRatio": None,
            "flowBalancePct": None,
        }
    buy_price = _number(row.get("avgLowPrice"))
    sell_price = _number(row.get("avgHighPrice"))
    economics = _margin(buy_price, sell_price, item_id, exempt_ids)
    buy_flow = _number(row.get("lowPriceVolume"))
    sell_flow = _number(row.get("highPriceVolume"))
    balanced = min(buy_flow, sell_flow) if buy_flow is not None and sell_flow is not None else None
    ratio = buy_flow / sell_flow if buy_flow is not None and sell_flow is not None and sell_flow > 0 else None
    balance = min(buy_flow, sell_flow) / max(buy_flow, sell_flow) * 100.0 if buy_flow and sell_flow else None
    return {
        "buyPrice": buy_price,
        "sellPrice": sell_price,
        **economics,
        "buyFlow": buy_flow,
        "sellFlow": sell_flow,
        "balancedFlow": balanced,
        "buySellRatio": ratio,
        "flowBalancePct": balance,
    }


def _spread_state(current: float | None, five_minute: float | None, one_hour: float | None) -> dict[str, str]:
    if current is None or current <= 0:
        return {"state": "negative", "label": "Not profitable"}
    if five_minute is not None and one_hour is not None and five_minute > 0 and one_hour > 0:
        return {"state": "persistent", "label": "Persistent"}
    return {"state": "current_only", "label": "Current only"}


def build_public_flipping(
    generated_at: int,
    mapping: dict[int, MappingItem],
    latest: dict[int, LatestPrice],
    five_minute: dict[int, dict[str, Any]],
    one_hour: dict[int, dict[str, Any]],
    exempt_ids: set[int],
    settings: dict[str, Any],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for item_id, item in mapping.items():
        quote = latest.get(item_id)
        buy_limit = item.limit
        if quote is None or not buy_limit or buy_limit <= 0 or not quote.low or not quote.high:
            continue

        buy_price = float(quote.low)
        sell_price = float(quote.high)
        current = _margin(buy_price, sell_price, item_id, exempt_ids)
        high_age = _age(quote.high_time, generated_at)
        low_age = _age(quote.low_time, generated_at)
        quote_age = max(high_age, low_age) if high_age is not None and low_age is not None else None
        avg5m = _window(five_minute.get(item_id), item_id, exempt_ids)
        avg1h = _window(one_hour.get(item_id), item_id, exempt_ids)
        spread = _spread_state(current["margin"], avg5m["margin"], avg1h["margin"])

        balanced_flow = avg1h["balancedFlow"]
        flow_capped_quantity = min(float(buy_limit), float(balanced_flow)) if balanced_flow is not None else None
        flow_capped_profit = current["margin"] * flow_capped_quantity if current["margin"] is not None and flow_capped_quantity is not None else None
        flow_capped_capital = buy_price * flow_capped_quantity if flow_capped_quantity is not None else None
        flow_coverage_pct = float(balanced_flow) / float(buy_limit) * 100.0 if balanced_flow is not None else None

        items.append({
            "itemId": item_id,
            "name": item.name,
            "members": item.members,
            "buyLimit": buy_limit,
            "buyPrice": buy_price,
            "sellPrice": sell_price,
            "highTime": quote.high_time,
            "lowTime": quote.low_time,
            "highAge": high_age,
            "lowAge": low_age,
            "quoteAge": quote_age,
            "freshness": _freshness(quote_age, settings),
            **current,
            "avg5m": avg5m,
            "avg1h": avg1h,
            "spread": spread,
            "flowCappedQuantity": flow_capped_quantity,
            "flowCappedProfit": flow_capped_profit,
            "flowCappedCapital": flow_capped_capital,
            "flowCoveragePct": flow_coverage_pct,
            "capitalAtLimit": buy_price * buy_limit,
            "limitProfit4h": current["margin"] * buy_limit if current["margin"] is not None else None,
        })

    items.sort(key=lambda row: row["flowCappedProfit"] if row["flowCappedProfit"] is not None else float("-inf"), reverse=True)
    return {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "source": "RuneScape Wiki real-time prices API (prices.runescape.wiki)",
        "items": items,
    }
