from __future__ import annotations

from typing import Any


def expanded_method_catalog() -> dict[str, dict[str, Any]]:
    """Additional deterministic AFK and bankstanding method families.

    Keep this separate from the original catalogue so broad coverage can grow
    without turning catalog.py into one large hand-maintained file. Every entry
    has deterministic inputs/outputs so live market profitability remains
    auditable.
    """
    methods: dict[str, dict[str, Any]] = {}

    def add(
        method_id: str,
        name: str,
        category: str,
        inputs: list[tuple[int, float]],
        outputs: list[tuple[int, float]],
        cycles_per_hour: float,
        theoretical_cycles_per_hour: float,
        interval_seconds: float,
        requirements: dict[str, Any],
        notes: str,
        reference: str,
        *,
        fixed_cost_gp_per_cycle: float = 0,
        intensity: str = "low",
    ) -> None:
        methods[method_id] = {
            "enabled": True,
            "name": name,
            "category": category,
            "inputs": [{"item_id": item_id, "quantity": quantity, "buy_via_ge": True} for item_id, quantity in inputs],
            "outputs": [{"item_id": item_id, "quantity": quantity} for item_id, quantity in outputs],
            "fixed_cost_gp_per_cycle": fixed_cost_gp_per_cycle,
            "cycles_per_hour": cycles_per_hour,
            "theoretical_cycles_per_hour": theoretical_cycles_per_hour,
            "planned_hours_per_day": 4,
            "afk": {"interval_seconds": interval_seconds, "intensity": intensity, "description": notes},
            "requirements": requirements,
            "notes": notes,
            "reference": reference,
        }

    # Missing Plank Make tiers. Nature and astral runes are consumed; an earth
    # rune supplying staff is modelled as reusable equipment.
    for key, log_id, plank_id, coin_cost in (
        ("logs", 1511, 960, 70),
        ("oak", 1521, 8778, 175),
        ("teak", 6333, 8780, 350),
    ):
        add(
            f"{key}_plank_make_afk",
            f"{key.title()} Plank Make - autocast",
            "strict_afk/magic",
            [(log_id, 1), (561, 1), (9075, 2)],
            [(plank_id, 1)],
            833,
            1000,
            90,
            {"members": True, "magic": 86, "quests": ["Dream Mentor"], "equipment": ["Earth-rune supplying staff"]},
            "Autocast Plank Make processes an inventory with a long idle window. Uses the conservative 833 casts/hour model.",
            "https://oldschool.runescape.wiki/w/Plank_Make",
            fixed_cost_gp_per_cycle=coin_cost,
            intensity="very_low",
        )

    # Gem cutting. A chisel occupies one inventory slot; the processing window is
    # long enough to be useful AFK bankstanding while profit remains market-led.
    for key, uncut_id, cut_id, level in (
        ("sapphire", 1623, 1607, 20),
        ("emerald", 1621, 1605, 27),
        ("ruby", 1619, 1603, 34),
        ("diamond", 1617, 1601, 43),
        ("dragonstone", 1631, 1615, 55),
    ):
        add(
            f"cut_uncut_{key}",
            f"Cut uncut {key}s",
            "strict_afk/crafting",
            [(uncut_id, 1)],
            [(cut_id, 1)],
            1500,
            1800,
            48.6,
            {"members": key == "dragonstone", "crafting": level, "equipment": ["Chisel"]},
            "Make-X gem cutting using a conservative 1,500 gems/hour. Live prices decide whether the conversion is worth doing.",
            "https://oldschool.runescape.wiki/w/Crafting",
        )

    # Molten-glass products. Unpowered orbs already exist in the original
    # catalogue, so only the missing products are added here.
    for key, output_id, level in (
        ("beer_glasses", 1919, 1),
        ("candle_lanterns", 4527, 4),
        ("oil_lamps", 4522, 12),
        ("vials", 229, 33),
        ("fishbowls", 6667, 42),
    ):
        add(
            f"blow_{key}",
            f"Blow {key.replace('_', ' ')}",
            "strict_afk/crafting",
            [(1775, 1)],
            [(output_id, 1)],
            1600,
            1750,
            48.6,
            {"members": key not in {"beer_glasses", "vials"}, "crafting": level, "equipment": ["Glassblowing pipe"]},
            "Long Make-X glassblowing batch. Uses a conservative 1,600 molten glass/hour rather than perfect banking.",
            "https://oldschool.runescape.wiki/w/Crafting",
        )

    # Shortbows complete the log-to-bow bankstanding family already represented
    # by longbows.
    for key, log_id, bow_u_id, level in (
        ("maple", 1517, 54, 50),
        ("yew", 1515, 64, 65),
        ("magic", 1513, 68, 80),
    ):
        add(
            f"fletch_{key}_shortbow_u",
            f"Fletch unstrung {key} shortbows",
            "strict_afk/fletching",
            [(log_id, 1)],
            [(bow_u_id, 1)],
            1500,
            1800,
            48.6,
            {"members": True, "fletching": level, "equipment": ["Knife"]},
            "Make-X shortbow cutting at a conservative 1,500 logs/hour.",
            "https://oldschool.runescape.wiki/w/Fletching",
        )

    for key, bow_u_id, bow_id, level in (
        ("maple", 54, 853, 50),
        ("yew", 64, 857, 65),
        ("magic", 68, 861, 80),
    ):
        add(
            f"string_{key}_shortbows",
            f"String {key} shortbows",
            "bankstanding/fletching",
            [(bow_u_id, 1), (1777, 1)],
            [(bow_id, 1)],
            2400,
            2400,
            16.8,
            {"members": True, "fletching": level},
            "Fast Make-X bow stringing. Classified as bankstanding rather than strict AFK because inventories complete quickly.",
            "https://oldschool.runescape.wiki/w/Fletching",
        )

    # Unfinished potions are deterministic two-input bankstanding conversions.
    for key, herb_id, unfinished_id, level in (
        ("guam", 249, 91, 3),
        ("marrentill", 251, 93, 5),
        ("tarromin", 253, 95, 12),
        ("harralander", 255, 97, 22),
        ("ranarr", 257, 99, 30),
        ("irit", 259, 101, 45),
        ("avantoe", 261, 103, 48),
        ("kwuarm", 263, 105, 55),
        ("cadantine", 265, 107, 66),
        ("dwarf_weed", 267, 109, 72),
        ("torstol", 269, 111, 75),
    ):
        add(
            f"make_{key}_unfinished_potion",
            f"Make {key.replace('_', ' ')} unfinished potions",
            "bankstanding/herblore",
            [(227, 1), (herb_id, 1)],
            [(unfinished_id, 1)],
            3900,
            4000,
            12.9,
            {"members": True, "herblore": level},
            "Fast bankstanding conversion using a conservative 3,900 unfinished potions/hour. Profit is entirely determined by live input/output prices.",
            "https://oldschool.runescape.wiki/w/Herblore",
        )

    return methods
