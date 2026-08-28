from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import MappingItem

GE_TAX_RATE_NUMERATOR = 2
GE_TAX_RATE_DENOMINATOR = 100
GE_TAX_CAP_GP = 5_000_000


def ge_tax_per_item(sell_price: int, item_id: int, exempt_item_ids: set[int]) -> int:
    if sell_price < 0:
        raise ValueError("sell_price cannot be negative")
    if item_id in exempt_item_ids:
        return 0
    raw_tax = sell_price * GE_TAX_RATE_NUMERATOR // GE_TAX_RATE_DENOMINATOR
    return min(raw_tax, GE_TAX_CAP_GP)


def net_ge_sell_price(sell_price: int, item_id: int, exempt_item_ids: set[int]) -> int:
    return sell_price - ge_tax_per_item(sell_price, item_id, exempt_item_ids)


def load_and_resolve_exemptions(path: str | Path, mapping: dict[int, MappingItem]) -> tuple[set[int], list[str]]:
    """Load explicit IDs and resolve configured names against current /mapping.

    Names keep the external exemption list auditable while allowing the runtime to
    derive stable item IDs from the canonical API mapping. Explicit IDs always win.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    ids = {int(item_id) for item_id in raw.get("itemIds", [])}
    names: Iterable[str] = raw.get("itemNames", [])
    by_name = {item.name.casefold(): item.id for item in mapping.values()}
    unresolved: list[str] = []
    for name in names:
        item_id = by_name.get(str(name).casefold())
        if item_id is None:
            unresolved.append(str(name))
        else:
            ids.add(item_id)
    return ids, unresolved
