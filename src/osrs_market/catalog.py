from __future__ import annotations

from typing import Any


def generated_method_catalog() -> dict[str, dict[str, Any]]:
    """Return the built-in AFK and bankstanding method catalog.

    The hand-maintained config/methods.yaml file is merged on top of this catalog,
    so individual assumptions can be overridden without editing Python.
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
        intensity: str = "very_low",
        fixed_cost_gp_per_cycle: float = 0,
    ) -> None:
        methods[method_id] = {
            "enabled": True,
            "name": name,
            "category": category,
            "inputs": [
                {"item_id": item_id, "quantity": quantity, "buy_via_ge": True}
                for item_id, quantity in inputs
            ],
            "outputs": [
                {"item_id": item_id, "quantity": quantity}
                for item_id, quantity in outputs
            ],
            "fixed_cost_gp_per_cycle": fixed_cost_gp_per_cycle,
            "cycles_per_hour": cycles_per_hour,
            "theoretical_cycles_per_hour": theoretical_cycles_per_hour,
            "planned_hours_per_day": 4,
            "afk": {
                "interval_seconds": interval_seconds,
                "intensity": intensity,
                "description": notes,
            },
            "requirements": requirements,
            "notes": notes,
            "reference": reference,
        }

    # Gem -> bolt tips. 12 tips per gem, about 3 seconds per gem.
    bolt_tips = (
        ("opal", 1609, 45, 11),
        ("jade", 1611, 9187, 26),
        ("red_topaz", 1613, 9188, 48),
        ("dragonstone", 1615, 9193, 71),
        ("onyx", 6573, 9194, 73),
    )
    for key, gem_id, tip_id, level in bolt_tips:
        label = key.replace("_", " ")
        add(
            f"{key}_bolt_tips",
            f"Cut {label} bolt tips",
            "strict_afk/fletching",
            [(gem_id, 1)],
            [(tip_id, 12)],
            1150,
            1200,
            81,
            {"members": True, "fletching": level, "equipment": ["Chisel"]},
            "Make-X gem cutting gives about 81 seconds per 27-gem inventory. Live prices determine whether the method is profitable.",
            "https://oldschool.runescape.wiki/w/Fletching",
        )

    # Rune dart tips were not in the original hand-tuned list.
    add(
        "rune_dart_tips",
        "Smith rune dart tips",
        "strict_afk/smithing",
        [(2363, 1)],
        [(824, 10)],
        1060,
        1300,
        81,
        {"members": True, "smithing": 89, "quests": ["The Tourist Trap"], "equipment": ["Hammer"]},
        "A full Make-X inventory takes about 81 seconds. Uses the no-Smiths'-Uniform rate of about 10,600 dart tips/hour.",
        "https://oldschool.runescape.wiki/w/Pay-to-play_Smithing_training",
    )

    # Cutting logs into unstrung longbows. These are long Make-X bankstanding batches.
    for key, log_id, bow_u_id, level in (
        ("maple", 1517, 62, 55),
        ("yew", 1515, 66, 70),
        ("magic", 1513, 70, 85),
    ):
        add(
            f"fletch_{key}_longbow_u",
            f"Fletch unstrung {key} longbows",
            "strict_afk/fletching",
            [(log_id, 1)],
            [(bow_u_id, 1)],
            1500,
            1600,
            49,
            {"members": True, "fletching": level, "equipment": ["Knife"]},
            "Longbow Make-X bankstanding. Uses a conservative 1,500 logs/hour and about 49 seconds per 27-log inventory.",
            f"https://oldschool.runescape.wiki/w/Money_making_guide/Fletching_unstrung_{key}_longbows",
            intensity="low",
        )

    # Stringing is profitable bankstanding but below the strict 30-second AFK threshold.
    for key, bow_u_id, bow_id, level in (
        ("maple", 62, 851, 55),
        ("yew", 66, 855, 70),
        ("magic", 70, 859, 85),
    ):
        add(
            f"string_{key}_longbows",
            f"String {key} longbows",
            "bankstanding/fletching",
            [(bow_u_id, 1), (1777, 1)],
            [(bow_id, 1)],
            2400,
            2400,
            17,
            {"members": True, "fletching": level},
            "Fast Make-X bankstanding at up to about 2,400 bows/hour. It is intentionally classified as bankstanding rather than strict AFK.",
            f"https://oldschool.runescape.wiki/w/Money_making_guide/Stringing_{key}_longbows",
            intensity="low",
        )

    # Cooking is configured at 99 Cooking with the cape so burns do not make the
    # deterministic input/output engine overstate output.
    for key, raw_id, cooked_id, minimum_level in (
        ("karambwan", 3142, 3144, 30),
        ("sharks", 383, 385, 80),
        ("monkfish", 7944, 7946, 62),
        ("anglerfish", 13439, 13441, 84),
        ("dark_crabs", 11934, 11936, 90),
    ):
        add(
            f"cook_{key}",
            f"Cook raw {key.replace('_', ' ')}",
            "strict_afk/cooking",
            [(raw_id, 1)],
            [(cooked_id, 1)],
            1300,
            1400,
            65,
            {"members": True, "cooking": 99, "minimum_cooking": minimum_level, "equipment": ["Cooking cape"]},
            "Configured at 99 Cooking with the Cooking cape for deterministic zero-burn output. Uses about 1,300 food/hour and roughly a minute per inventory.",
            f"https://oldschool.runescape.wiki/w/Money_making_guide/Cooking_raw_{key}",
        )

    # Gold and gem jewellery. Gold-only inventories are more AFK; gem jewellery
    # uses 13+13 inventories and still clears the 30-second strict-AFK threshold
    # at the standard ~1,400 items/hour model.
    gems = (
        ("sapphire", 1607),
        ("emerald", 1605),
        ("ruby", 1603),
        ("diamond", 1601),
        ("dragonstone", 1615),
    )
    jewellery = (
        ("ring", "ring", "Ring mould", 1635, 5, ((1637, 20), (1639, 27), (1641, 34), (1643, 43), (1645, 55))),
        ("necklace", "necklace", "Necklace mould", 1654, 6, ((1656, 22), (1658, 29), (1660, 40), (1662, 56), (1664, 72))),
        ("bracelet", "bracelet", "Bracelet mould", 11069, 7, ((11072, 23), (11076, 30), (11085, 42), (11092, 58), (11115, 74))),
        ("amulet_u", "amulet (u)", "Amulet mould", 1673, 8, ((1675, 24), (1677, 31), (1679, 50), (1681, 70), (1683, 80))),
    )
    for type_key, type_label, mould, gold_output, gold_level, gem_outputs in jewellery:
        add(
            f"craft_gold_{type_key}",
            f"Craft gold {type_label}",
            "strict_afk/crafting",
            [(2357, 1)],
            [(gold_output, 1)],
            1400,
            1450,
            69,
            {"members": False, "crafting": gold_level, "equipment": [mould]},
            "Gold-only jewellery uses nearly a full inventory of bars, producing a long furnace Make-X window. Uses about 1,400 jewellery/hour.",
            "https://oldschool.runescape.wiki/w/Crafting",
            intensity="low",
        )
        for (gem_name, gem_id), (output_id, level) in zip(gems, gem_outputs):
            add(
                f"craft_{gem_name}_{type_key}",
                f"Craft {gem_name} {type_label}",
                "strict_afk/crafting",
                [(2357, 1), (gem_id, 1)],
                [(output_id, 1)],
                1400,
                1450,
                33,
                {"members": True, "crafting": level, "equipment": [mould]},
                "Gem jewellery uses 13 bars and 13 gems per inventory. At roughly 1,400 jewellery/hour this gives about 33 seconds of furnace processing.",
                "https://oldschool.runescape.wiki/w/Crafting",
                intensity="low",
            )

    add(
        "blow_unpowered_orbs",
        "Blow unpowered orbs",
        "strict_afk/crafting",
        [(1775, 1)],
        [(567, 1)],
        1600,
        1800,
        54,
        {"members": True, "crafting": 46, "equipment": ["Glassblowing pipe"]},
        "Classic long-inventory bankstanding glassblowing. Uses a conservative 1,600 molten glass/hour.",
        "https://oldschool.runescape.wiki/w/Pay-to-play_Crafting_training",
    )

    for key, orb_id, staff_id, level in (
        ("water", 571, 1395, 54),
        ("earth", 575, 1399, 58),
        ("fire", 569, 1393, 62),
        ("air", 573, 1397, 66),
    ):
        add(
            f"craft_{key}_battlestaves",
            f"Craft {key} battlestaves",
            "bankstanding/crafting",
            [(1391, 1), (orb_id, 1)],
            [(staff_id, 1)],
            2450,
            2500,
            20,
            {"members": True, "crafting": level},
            "Attaching charged orbs to battlestaves is fast bankstanding processing rather than strict AFK. Uses about 2,450 staves/hour.",
            "https://oldschool.runescape.wiki/w/Pay-to-play_Crafting_training",
            intensity="low",
        )

    # Gathering methods that fit the current deterministic market model. Random
    # secondary drops are omitted so the displayed GP/hour is conservative.
    add(
        "mine_amethyst",
        "Mine amethyst",
        "gathering/mining",
        [],
        [(21347, 1)],
        90,
        100,
        45,
        {"members": True, "mining": 92, "equipment": ["Rune, dragon or crystal pickaxe"]},
        "Wiki estimates 80-100 amethyst/hour; configured at the midpoint 90. Unidentified minerals are omitted from profit.",
        "https://oldschool.runescape.wiki/w/Money_making_guide/Mining_amethyst",
    )
    add(
        "cut_magic_logs",
        "Cut magic logs",
        "gathering/woodcutting",
        [],
        [(1513, 1)],
        130,
        130,
        90,
        {"members": True, "woodcutting": 75},
        "Wiki guide estimates about 130 magic logs/hour. Forestry leaves and attachment value are omitted so the calculation isolates tradeable logs.",
        "https://oldschool.runescape.wiki/w/Money_making_guide/Cutting_magic_logs",
    )
    add(
        "cut_redwood_logs",
        "Cut redwood logs",
        "gathering/woodcutting",
        [],
        [(19669, 1)],
        160,
        180,
        180,
        {"members": True, "woodcutting": 90},
        "Wiki estimates 140-180 redwood logs/hour; configured at 160. Bird nests are omitted from profit.",
        "https://oldschool.runescape.wiki/w/Money_making_guide/Cutting_redwood_logs",
    )
    add(
        "cut_camphor_logs",
        "Cut camphor logs",
        "gathering/woodcutting",
        [],
        [(32904, 1)],
        385,
        395,
        75,
        {"members": True, "woodcutting": 66},
        "Configured around 385 logs/hour from current Wiki feedback reporting roughly 380-395/hour at 89 Woodcutting with a dragon axe and log basket.",
        "https://oldschool.runescape.wiki/w/Money_making_guide/Cutting_camphor_logs",
    )
    add(
        "catch_dark_crabs",
        "Catch dark crabs",
        "gathering/fishing",
        [(11940, 1)],
        [(11934, 1)],
        308,
        308,
        120,
        {"members": True, "fishing": 85, "recommended": ["Wilderness Elite Diary", "Rada's blessing"]},
        "Wiki guide uses 308 raw dark crabs/hour with Wilderness Elite. Includes the 50 gp Piles noting fee per catch; Wilderness PK risk is not monetised.",
        "https://oldschool.runescape.wiki/w/Money_making_guide/Catching_dark_crabs",
        fixed_cost_gp_per_cycle=50,
    )

    return methods
