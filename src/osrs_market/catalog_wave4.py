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

    # Tanning is deterministic but its achievable rate depends heavily on the
    # run between bank and tanner, so the workflow model is explicit.
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

    # Grinding/crushing conversions. Pestle and mortar is reusable equipment.
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

    # A real variant example: the same flax-to-bow-string conversion can be
    # performed manually or with Lunar magic. Both are evaluated independently.
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

    # Probabilistic output example. Superglass Make has variable yield, so the
    # expected and lower-bound output are explicit rather than hidden in CPH.
    add(
        "superglass_make_giant_seaweed",
        "Superglass Make with giant seaweed",
        "bankstanding/magic",
        [ge(21504, 3), ge(1783, 18), ge(9075, 2)],
        [out(1775, 28.5, quantity_expected=28.5, quantity_minimum=27.0, quantity_maximum=30.0)],
        480,
        7.5,
        {"members": True, "magic": 77, "quests": ["Lunar Diplomacy"]},
        "Variable molten-glass yield is represented explicitly. Expected profit uses expected yield; Conservative can use the configured lower-bound yield.",
        "https://oldschool.runescape.wiki/w/Superglass_Make",
        theoretical_cycles_per_hour=500,
        workflow={"process_seconds": 3.0, "bank_seconds": 4.5, "travel_seconds": 0, "inventory_size": 27, "items_per_inventory": 21},
        intensity="moderate",
    )

    # Stochastic/gathering examples. Primary output is deterministic at the
    # configured observed rate; secondary drops use expected-value quantities.
    add(
        "cut_yew_logs_with_nests",
        "Cut yew logs with nest value",
        "gathering/woodcutting",
        [],
        [out(1515, 1), out(5075, 0.012, quantity_expected=0.012, quantity_minimum=0.0, quantity_maximum=0.03)],
        130,
        75,
        {"members": False, "woodcutting": 60, "equipment": ["Rune axe or better"]},
        "Adds a small expected bird-nest component to the primary yew-log output. Nest EV is visible and separable from deterministic log value.",
        "https://oldschool.runescape.wiki/w/Woodcutting",
        theoretical_cycles_per_hour=150,
        intensity="very_low",
    )

    add(
        "catch_raw_karambwan",
        "Catch raw karambwan",
        "gathering/fishing",
        [ge(3150)],
        [out(3142, 1)],
        600,
        120,
        {"members": True, "fishing": 65, "quests": ["Tai Bwo Wannai Trio"]},
        "High-AFK primary catch method. Rate is deliberately conservative and excludes clue bottles or other incidental value.",
        "https://oldschool.runescape.wiki/w/Money_making_guide/Catching_raw_karambwan",
        theoretical_cycles_per_hour=650,
        intensity="very_low",
    )

    return methods
