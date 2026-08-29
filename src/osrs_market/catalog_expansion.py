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

    # Shortbows complete the log-to-bow family. Correct OSRS item IDs are 64,
    # 68 and 72 for maple/yew/magic unstrung shortbows respectively.
    for key, log_id, bow_u_id, level in (
        ("maple", 1517, 64, 50),
        ("yew", 1515, 68, 65),
        ("magic", 1513, 72, 80),
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
        ("maple", 64, 853, 50),
        ("yew", 68, 857, 65),
        ("magic", 72, 861, 80),
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

    # Lower-tier bows were previously absent. They are useful when a live spread
    # temporarily makes low-value logs/bows profitable and broaden low-level access.
    for key, log_id, short_u, short_bow, short_level, long_u, long_bow, long_level in (
        ("logs", 1511, 50, 841, 5, 48, 839, 10),
        ("oak", 1521, 54, 843, 20, 56, 845, 25),
        ("willow", 1519, 60, 849, 35, 58, 847, 40),
    ):
        for bow_type, output_u, output_bow, level in (
            ("shortbow", short_u, short_bow, short_level),
            ("longbow", long_u, long_bow, long_level),
        ):
            add(
                f"fletch_{key}_{bow_type}_u",
                f"Fletch unstrung {key} {bow_type}s",
                "strict_afk/fletching",
                [(log_id, 1)],
                [(output_u, 1)],
                1500,
                1800,
                48.6,
                {"members": True, "fletching": level, "equipment": ["Knife"]},
                "Long Make-X bow cutting. Uses a conservative 1,500 logs/hour and live market pricing.",
                "https://oldschool.runescape.wiki/w/Fletching",
            )
            add(
                f"string_{key}_{bow_type}s",
                f"String {key} {bow_type}s",
                "bankstanding/fletching",
                [(output_u, 1), (1777, 1)],
                [(output_bow, 1)],
                2400,
                2400,
                16.8,
                {"members": True, "fletching": level},
                "Fast two-input Make-X bow stringing. Included as bankstanding rather than strict AFK.",
                "https://oldschool.runescape.wiki/w/Fletching",
            )

    # Arrow shafts are deterministic log conversion. Higher-tier logs create more
    # shafts per log, so the live engine can identify unusual profitable spreads.
    for key, log_id, shafts, level in (
        ("logs", 1511, 15, 1),
        ("oak", 1521, 30, 15),
        ("willow", 1519, 45, 30),
        ("maple", 1517, 60, 45),
        ("yew", 1515, 75, 60),
        ("magic", 1513, 90, 75),
    ):
        add(
            f"fletch_{key}_arrow_shafts",
            f"Fletch arrow shafts from {key}",
            "strict_afk/fletching",
            [(log_id, 1)],
            [(52, shafts)],
            1800,
            2000,
            48.6,
            {"members": True, "fletching": level, "equipment": ["Knife"]},
            f"One {key} log produces {shafts} arrow shafts. Uses a conservative 1,800 logs/hour Make-X rate.",
            "https://oldschool.runescape.wiki/w/Arrow_shaft",
        )

    # Unfinished potions are deterministic two-input bankstanding conversions.
    for key, herb_id, unfinished_id, level in (
        ("guam", 249, 91, 3),
        ("marrentill", 251, 93, 5),
        ("tarromin", 253, 95, 12),
        ("harralander", 255, 97, 22),
        ("ranarr", 257, 99, 30),
        ("toadflax", 2998, 3002, 34),
        ("irit", 259, 101, 45),
        ("avantoe", 261, 103, 48),
        ("kwuarm", 263, 105, 55),
        ("snapdragon", 3000, 3004, 63),
        ("cadantine", 265, 107, 66),
        ("lantadyme", 2481, 2483, 69),
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

    # Finished potions. No amulet/prescription-goggle proc is assumed, so output
    # is the deterministic three-dose potion only.
    for method_id, name, unf_id, secondary_id, output_id, level in (
        ("prayer", "Prayer potion", 99, 231, 139, 38),
        ("super_attack", "Super attack potion", 101, 221, 145, 45),
        ("super_strength", "Super strength potion", 105, 225, 157, 55),
        ("ranging", "Ranging potion", 109, 245, 169, 72),
        ("magic", "Magic potion", 2483, 3138, 3042, 76),
    ):
        add(
            f"make_{method_id}_potions",
            f"Make {name}s",
            "bankstanding/herblore",
            [(unf_id, 1), (secondary_id, 1)],
            [(output_id, 1)],
            3000,
            3000,
            16.8,
            {"members": True, "herblore": level},
            "Deterministic 14+14 Make-X potion batches. Proc-based extra doses are deliberately excluded from the profit model.",
            "https://oldschool.runescape.wiki/w/Herblore",
        )

    # Humidify converts an entire inventory in one cast. A steam battlestaff
    # supplies fire and water runes, leaving one astral rune as the consumed rune.
    for key, input_id, output_id in (
        ("clay", 434, 1761),
        ("buckets", 1925, 1929),
    ):
        add(
            f"humidify_{key}",
            f"Humidify {key}",
            "bankstanding/magic",
            [(input_id, 27), (9075, 1)],
            [(output_id, 27)],
            800,
            815,
            3.6,
            {"members": True, "magic": 68, "quests": ["Dream Mentor"], "equipment": ["Steam battlestaff"]},
            "One Humidify cast processes 27 inventory items. Uses 800 casts/hour rather than the guide's near-perfect ~815 casts/hour.",
            f"https://oldschool.runescape.wiki/w/Money_making_guide/Humidifying_{'clay' if key == 'clay' else 'buckets_of_water'}",
            intensity="moderate",
        )

    # Simple furnace smelting that has no probabilistic output assumption.
    add(
        "smelt_bronze_bars",
        "Smelt bronze bars",
        "strict_afk/smithing",
        [(436, 1), (438, 1)],
        [(2349, 1)],
        900,
        1000,
        33.6,
        {"members": False, "smithing": 1},
        "Standard furnace Make-X using equal copper and tin ore. Uses a conservative 900 bars/hour.",
        "https://oldschool.runescape.wiki/w/Smithing",
    )
    add(
        "smelt_silver_bars",
        "Smelt silver bars",
        "strict_afk/smithing",
        [(442, 1)],
        [(2355, 1)],
        1100,
        1200,
        67.2,
        {"members": False, "smithing": 20},
        "Standard furnace Make-X silver smelting. Uses a conservative 1,100 bars/hour.",
        "https://oldschool.runescape.wiki/w/Smithing",
    )
    add(
        "smelt_gold_bars",
        "Smelt gold bars",
        "strict_afk/smithing",
        [(444, 1)],
        [(2357, 1)],
        1100,
        1200,
        67.2,
        {"members": False, "smithing": 40},
        "Standard furnace Make-X gold smelting without Goldsmith gauntlet XP assumptions. Uses a conservative 1,100 bars/hour.",
        "https://oldschool.runescape.wiki/w/Smithing",
    )

    # Gathering methods that are deterministic enough for the current engine
    # remain in catalog.py. Random secondary drops stay excluded from expected GP.
    return methods
