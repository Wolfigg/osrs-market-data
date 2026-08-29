from __future__ import annotations

import time
from pathlib import Path

from osrs_market.public_site import write_public_site


def afk_method(method_id: str, name: str, category: str, *, members: bool, gp_per_hour: float, capital: int, tags: list[str], skills: dict[str, int], quests: list[str] | None = None, stability: str = "stable", sustainability: str = "strong") -> dict:
    cycles = 100.0
    cost_per_cycle = capital / cycles if capital else 0.0
    profit_per_cycle = gp_per_hour / cycles
    output_volume = 100_000
    return {
        "methodId": method_id,
        "name": name,
        "category": category,
        "tags": [category.lower(), *tags, "members" if members else "f2p"],
        "members": members,
        "requirements": {"skills": skills, "quests": quests or [], "equipment": []},
        "current": {"valid": True, "gpPerHour": gp_per_hour},
        "recommended": {"gpPerHour": gp_per_hour * 0.9, "referenceGpPerHour": gp_per_hour * 0.85},
        "history": {"6hGpPerHour": gp_per_hour * 0.88, "24hGpPerHour": gp_per_hour * 0.85, "7dGpPerHour": gp_per_hour * 0.84, "30dGpPerHour": gp_per_hour * 0.83},
        "stability": {"state": stability, "label": stability.replace("_", " ").title(), "currentVs24hPct": 4.0, "currentVs7dPct": 5.0, "currentVs30dPct": 6.0, "referenceSpreadPct": 2.0, "reasons": ["Synthetic browser fixture."]},
        "sustainability": {"state": sustainability, "label": sustainability.replace("_", " ").title(), "throughputRatioPct": 100.0, "maxOneHourSharePct24h": 0.1, "limitingFactor": "mechanics", "reasons": ["Synthetic sustainability fixture."]},
        "afk": {"classification": "AFK", "intervalSeconds": 60, "gpPerInteraction": gp_per_hour / 60, "description": "Synthetic browser fixture."},
        "mechanics": {"cyclesPerHour": cycles, "cyclesPerHourByBuyLimits": cycles},
        "economics": {"capitalPerCycle": cost_per_cycle, "capitalOneHour": capital, "capitalFourHours": capital * 4, "buyLimitConstrained": False, "profitPerCycle": profit_per_cycle, "inputGpPerCycle": cost_per_cycle, "fixedCostGpPerCycle": 0, "outputGrossGpPerCycle": cost_per_cycle + profit_per_cycle, "geTaxGpPerCycle": 0, "outputNetGpPerCycle": cost_per_cycle + profit_per_cycle},
        "liquidity": {"inputs": [] if capital == 0 else [{"itemId": 100 + len(method_id), "name": "Synthetic input", "unitsPerHour": 100, "volume24h": 100_000, "oneHourSharePct24h": 0.1}], "outputs": [{"itemId": 200 + len(method_id), "name": "Output", "unitsPerHour": 100, "volume24h": output_volume, "oneHourSharePct24h": 0.1}]},
        "risk": {"level": "normal", "label": "Normal market risk", "reasons": []},
        "inputs": [] if capital == 0 else [{"itemId": 100 + len(method_id), "name": "Synthetic input", "quantity": 1, "price": cost_per_cycle, "subtotal": cost_per_cycle, "buyViaGe": True, "geBuyLimit": 10_000, "maxCyclesPerHourByLimit": 2_500}],
        "outputs": [{"itemId": 200 + len(method_id), "name": "Output", "quantity": 1, "gePrice": cost_per_cycle + profit_per_cycle, "geTaxPerItem": 0, "geNetPerItem": cost_per_cycle + profit_per_cycle}],
        "description": "Synthetic browser fixture.",
        "reference": "https://oldschool.runescape.wiki/",
    }


def main() -> None:
    now = int(time.time())
    afk = {
        "schemaVersion": 1,
        "generatedAt": now,
        "methods": [
            afk_method("ruby", "Cut ruby bolt tips", "Fletching", members=True, gp_per_hour=180_000, capital=900_000, tags=["bankstanding", "make-x"], skills={"fletching": 63}, sustainability="moderate"),
            afk_method("camphor", "Cut camphor logs", "Woodcutting", members=True, gp_per_hour=120_000, capital=0, tags=["gathering"], skills={"woodcutting": 66, "sailing": 45}, quests=["Troubled Tortugans (partial)"]),
            afk_method("gold-ring", "Craft gold ring", "Crafting", members=False, gp_per_hour=-5_000, capital=300_000, tags=["bankstanding", "make-x"], skills={"crafting": 5}, stability="watch", sustainability="watch"),
        ],
    }
    alchemy = {
        "schemaVersion": 1,
        "generatedAt": now,
        "assumptions": {"magicLevel": 55, "castsPerHour": 1200, "natureRuneCost": 100, "fireStaff": True},
        "items": [
            {"itemId": 1, "name": "Rune platebody", "members": False, "buyPrice": 38_000, "highAlchValue": 39_000, "runeCost": 100, "profitPerCast": 900, "roi": 2.3, "buyLimit": 70, "quantity4h": 70, "profit4h": 63_000, "capitalRequired": 800_000, "volume24h": 10_000, "freshness": "Fresh", "history": {"24hProfitPerCast": 850, "7dProfitPerCast": 820, "30dProfitPerCast": 800}, "history24hProfitPerCast": 850, "risk": {"level": "normal", "label": "Normal market risk", "reasons": []}},
            {"itemId": 2, "name": "Exact million item", "members": True, "buyPrice": 1_000, "highAlchValue": 1_500, "runeCost": 100, "profitPerCast": 400, "roi": 36.4, "buyLimit": 1000, "quantity4h": 1000, "profit4h": 400_000, "capitalRequired": 1_000_000, "volume24h": 20_000, "freshness": "Fresh", "history": {"24hProfitPerCast": 390, "7dProfitPerCast": 380, "30dProfitPerCast": 370}, "history24hProfitPerCast": 390, "risk": {"level": "normal", "label": "Normal market risk", "reasons": []}},
            {"itemId": 3, "name": "Unavailable item", "members": False, "buyPrice": None, "highAlchValue": 2_000, "runeCost": None, "profitPerCast": None, "roi": None, "buyLimit": 100, "quantity4h": None, "profit4h": None, "capitalRequired": None, "volume24h": 0, "freshness": "Stale", "history": {"24hProfitPerCast": None, "7dProfitPerCast": None, "30dProfitPerCast": None}, "history24hProfitPerCast": None, "risk": {"level": "unavailable", "label": "Unavailable", "reasons": ["Synthetic stale item."]}},
        ],
    }
    status = {"schemaVersion": 1, "generatedAt": now, "liveGeneratedAt": now, "shortHistoryGeneratedAt": now - 1800, "longHistoryGeneratedAt": now - 7200, "state": "current", "ageSeconds": 9000}
    write_public_site(Path("build/browser-test"), afk, alchemy, status)


if __name__ == "__main__":
    main()
