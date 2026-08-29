from __future__ import annotations

from typing import Any


def wave4_method_catalog() -> dict[str, dict[str, Any]]:
    methods: dict[str, dict[str, Any]] = {}

    def add(
        method_id: str,
        name: str,
        category: str,
        inputs: list[dict[str, Any]],
        outputs: list[dict[str, Any]],
        cycles_per_hour: float,
        interval_seconds: float,
        requirements: dict[str, Any],
        notes: str,
        reference: str,
        *,
        theoretical_cycles_per_hour: float | None = None,
        fixed_cost_gp_per_cycle: float = 0,
        workflow: dict[str, Any] | None = None,
        variants: list[dict[str, Any]] | None = None,
        intensity: str = "low",
    ) -> None:
        method: dict[str, Any] = {
            "enabled": True,
            "name": name,
            "category": category,
            "inputs": inputs,
            "outputs": outputs,
            "fixed_cost_gp_per_cycle": fixed_cost_gp_per_cycle,
            "cycles_per_hour": cycles_per_hour,
            "theoretical_cycles_per_hour": theoretical_cycles_per_hour or cycles_per_hour,
            "planned_hours_per_day": 4,
            "afk": {"interval_seconds": interval_seconds, "intensity": intensity, "description": notes},
            "requirements": requirements,
            "notes": notes,
            "reference": reference,
        }
        if workflow:
            method["workflow"] = workflow
        if variants:
            method["variants"] = variants
        methods[method_id] = method

    def ge(item_id: int, quantity: float = 1) -> dict[str, Any]:
        return {"item_id": item_id, "quantity": quantity, "buy_via_ge": True}

    def out(item_id: int, quantity: float = 1, **extra: Any) -> dict[str, Any]:
        return {"item_id": item_id, "quantity": quantity, **extra}

    for key, hide_id, leather_id, fee, members in (
        ("cowhide", 1739, 1741, 1, False),
        ("green_dragonhide", 1753, 1745, 20, True),
        ("blue_dragonhide", 1751, 2505, 20, True),
        ("red_dragonhide", 1749, 2507, 20, True),
        ("black_dragonhide", 1747, 2509, 20, True),
    ):
        add(
            f"tan_{key}",
            f"Tan {key.replace('_', ' ')}",
            "processing/crafting",
            [ge(hide_id)],
            [out(leather_id)],
            2400,
            12,
            {"members": members},
            "Deterministic hide-to-leather conversion. Throughput includes banking and travel rather than assuming bankstanding speed.",
            "https://oldschool.runescape.wiki/w/Tanning",
            theoretical_cycles_per_hour=2800,
            fixed_cost_gp_per_cycle=fee,
            workflow={"process_seconds": 0.7, "bank_seconds": 0.3, "travel_seconds": 0.5, "inventory_size": 27, "items_per_inventory": 27},
        )

    for key, source_id, output_id, members in (
        ("unicorn_horns", 237, 235, True),
        ("blue_dragon_scales", 243, 241, True),
        ("chocolate_bars", 1973, 1975, False),
    ):
        add(
            f"grind_{key}",
            f"Grind {key.replace('_', ' ')}",
            "bankstanding/herblore",
            [ge(source_id)],
            [out(output_id)],
            3600,
            7.2,
            {"members": members, "equipment": ["Pestle and mortar"]},
            "Deterministic bankstanding conversion with a conservative rate below perfect repeated Make-X execution.",
            "https://oldschool.runescape.wiki/w/Pestle_and_mortar",
            theoretical_cycles_per_hour=5000,
            workflow={"process_seconds": 0.75, "bank_seconds": 0.25, "travel_seconds": 0, "inventory_size": 27, "items_per_inventory": 27},
        )

    add(
        "make_headless_arrows",
        "Make headless arrows",
        "bankstanding/fletching",
        [ge(52), ge(314)],
        [out(53)],
        45000,
        1.2,
        {"members": False, "fletching": 1},
        "Arrow shafts and feathers combine in batches. The per-unit recipe lets market limits and margins scale correctly.",
        "https://oldschool.runescape.wiki/w/Headless_arrow",
        theoretical_cycles_per_hour=45000,
        intensity="moderate",
    )

    for key, tip_id, arrow_id, level, members in (
        ("bronze", 39, 882, 1, False),
        ("iron", 40, 884, 15, False),
        ("steel", 41, 886, 30, False),
        ("mithril", 42, 888, 45, False),
        ("adamant", 43, 890, 60, False),
        ("rune", 44, 892, 75, True),
        ("amethyst", 21350, 21326, 82, True),
    ):
        add(
            f"make_{key}_arrows",
            f"Make {key} arrows",
            "bankstanding/fletching",
            [ge(53), ge(tip_id)],
            [out(arrow_id)],
            45000,
            1.2,
            {"members": members, "fletching": level},
            "Headless arrows and arrowtips combine in 15-item batches. Rate is expressed per finished arrow.",
            "https://oldschool.runescape.wiki/w/Arrow",
            theoretical_cycles_per_hour=45000,
            intensity="moderate",
        )

    add(
        "spin_flax",
        "Spin flax into bow strings",
        "processing/crafting",
        [ge(1779)],
        [out(1777)],
        1400,
        30,
        {"members": True, "crafting": 10},
        "Variant-aware flax conversion. The manual wheel and Lunar spell have different throughput and consumable requirements.",
        "https://oldschool.runescape.wiki/w/Flax",
        theoretical_cycles_per_hour=1600,
        variants=[
            {
                "id": "spinning_wheel",
                "label": "Spinning wheel",
                "description": "Manual spinning with bank/travel overhead.",
                "overrides": {
                    "cycles_per_hour": 1400,
                    "theoretical_cycles_per_hour": 1600,
                    "workflow": {"process_seconds": 2.0, "bank_seconds": 0.35, "travel_seconds": 0.2, "inventory_size": 28, "items_per_inventory": 28},
                    "requirements": {"members": True, "crafting": 10},
                },
            },
            {
                "id": "lunar_spell",
                "label": "Spin Flax spell",
                "description": "Lunar spell variant processing five flax per cast.",
                "overrides": {
                    "inputs": [ge(1779, 5), ge(561, 1), ge(9075, 1)],
                    "outputs": [out(1777, 5)],
                    "cycles_per_hour": 1200,
                    "theoretical_cycles_per_hour": 1200,
                    "afk": {"interval_seconds": 3, "intensity": "moderate", "description": "Lunar Spin Flax spell, five flax per cast."},
                    "workflow": {"process_seconds": 3.0, "bank_seconds": 0, "travel_seconds": 0, "inventory_size": 0, "items_per_inventory": 5},
                    "requirements": {"members": True, "magic": 76, "quests": ["Lunar Diplomacy"]},
                },
            },
        ],
    )

    # Three giant seaweed + 18 sand averages 26.1 glass/cast when floor drops are
    # ignored, which is the high-throughput Wiki calculator assumption. A smoke
    # battlestaff supplies the air/fire runes, so only astral runes are consumed.
    add(
        "superglass_make_giant_seaweed",
        "Superglass Make with giant seaweed",
        "bankstanding/magic",
        [ge(21504, 3), ge(1783, 18), ge(9075, 2)],
        [out(1775, 26.1, quantity_expected=26.1, quantity_minimum=18.0, quantity_maximum=30.0)],
        600,
        6.0,
        {"members": True, "magic": 77, "crafting": 61, "quests": ["Lunar Diplomacy"], "equipment": ["Smoke battlestaff"]},
        "Variable molten-glass yield is represented explicitly. Expected output uses the Wiki calculator's 26.1 glass per cast when floor drops are ignored; Conservative uses the configured 18-glass floor.",
        "https://oldschool.runescape.wiki/w/Superglass_Make",
        theoretical_cycles_per_hour=850,
        workflow={"process_seconds": 3.6, "bank_seconds": 2.4, "travel_seconds": 0, "inventory_size": 27, "items_per_inventory": 21},
        intensity="moderate",
    )

    # Standard trees roll a bird nest instead of a log at 1/256. The empty nest
    # is used as a conservative tradeable proxy for the nest roll; seed/ring/egg
    # contents are deliberately excluded rather than inventing an EV table.
    add(
        "cut_yew_logs_with_nests",
        "Cut yew logs with nest value",
        "gathering/woodcutting",
        [],
        [
            out(1515, 255 / 256, quantity_expected=255 / 256, quantity_minimum=255 / 256, quantity_maximum=1.0),
            out(5075, 1 / 256, quantity_expected=1 / 256, quantity_minimum=0.0, quantity_maximum=1 / 230),
        ],
        130,
        75,
        {"members": True, "woodcutting": 60, "equipment": ["Rune axe or better"]},
        "Models the source-backed 1/256 standard-tree bird-nest roll. Empty nest value is a conservative proxy and nest contents are excluded.",
        "https://oldschool.runescape.wiki/w/Yew_tree",
        theoretical_cycles_per_hour=150,
        intensity="very_low",
    )

    # Raw karambwanji bait is untradeable and absent from the real-time price
    # mapping, so it must not be represented as a GE input. The method therefore
    # reports market revenue from raw karambwan and states the self-supplied bait
    # requirement explicitly.
    add(
        "catch_raw_karambwan",
        "Catch raw karambwan",
        "gathering/fishing",
        [],
        [out(3142, 1)],
        600,
        120,
        {"members": True, "fishing": 65, "quests": ["Tai Bwo Wannai Trio"], "equipment": ["Karambwan vessel"], "supplies": ["Self-supplied raw karambwanji bait"]},
        "High-AFK primary catch method. Raw karambwanji bait is untradeable, so it is a stated self-supplied requirement rather than a GE-priced input.",
        "https://oldschool.runescape.wiki/w/Money_making_guide/Catching_raw_karambwan",
        theoretical_cycles_per_hour=650,
        intensity="very_low",
    )

    return methods
