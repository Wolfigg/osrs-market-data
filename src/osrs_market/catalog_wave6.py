from __future__ import annotations

from typing import Any


def wave6_method_catalog() -> dict[str, dict[str, Any]]:
    methods: dict[str, dict[str, Any]] = {}

    def out(name: str, quantity: float = 1, **extra: Any) -> dict[str, Any]:
        return {"item_name": name, "quantity": quantity, **extra}

    def add(method_id: str, name: str, category: str, outputs: list[dict[str, Any]], rate: float, level_key: str, level: int, equipment: list[str], reference: str, *, members: bool = True, quantiles: tuple[float, float, float, float, float] | None = None, model: dict[str, Any] | None = None, variants: list[dict[str, Any]] | None = None, interval: float = 60) -> None:
        q = quantiles or (rate * .82, rate * .92, rate, rate * 1.08, rate * 1.15)
        methods[method_id] = {
            "enabled": True,
            "name": name,
            "category": category,
            "inputs": [],
            "outputs": outputs,
            "fixed_cost_gp_per_cycle": 0,
            "cycles_per_hour": rate,
            "theoretical_cycles_per_hour": q[4],
            "planned_hours_per_day": 4,
            "afk": {"interval_seconds": interval, "intensity": "low", "description": "Wave 6 account-aware gathering model with explicit throughput uncertainty."},
            "requirements": {"members": members, level_key: level, "equipment": equipment},
            "throughput": {"quantiles": {"p10": q[0], "p25": q[1], "p50": q[2], "p75": q[3], "p90": q[4]}},
            "model": model or {},
            "variants": variants or [],
            "notes": "Account-specific rate modifiers are modelled separately from market pricing. Untradeable rewards are never silently valued as GP.",
            "reference": reference,
            "method_types": ["gathering", "probabilistic", "variants"] if variants else ["gathering", "probabilistic"],
            "provenance": {"assumptions": [{"key": "base_throughput", "value": rate, "unit": "items_per_hour", "source": "osrs_wiki", "sourceUrl": reference, "verifiedAt": "2026-08-30", "confidence": "medium", "kind": "wiki_documented_rate"}]},
        }

    # Mixed catch is represented as expected composition rather than pretending each
    # harpoon action is a swordfish. The distribution is intentionally configurable.
    add(
        "fishing_v2_tuna_swordfish",
        "Harpoon tuna and swordfish",
        "gathering/fishing",
        [out("Raw tuna", quantity_expected=.58, quantity_minimum=0), out("Raw swordfish", quantity_expected=.42, quantity_minimum=0)],
        360, "fishing", 50, ["Harpoon"], "https://oldschool.runescape.wiki/w/Harpoon",
        members=False, quantiles=(255, 315, 360, 405, 445),
        model={"fishing": {"mixedCatch": True, "composition": {"Raw tuna": .58, "Raw swordfish": .42}, "levelScaling": True, "supportsRadasBlessing": True, "supportsSpiritFlakes": True, "fishBarrelAffectsBanking": True}},
        variants=[
            {"id": "standard", "label": "Standard", "overrides": {}},
            {"id": "dragon_harpoon", "label": "Dragon harpoon", "overrides": {"requirements": {"members": True, "fishing": 61, "equipment": ["Dragon harpoon"]}, "throughput": {"quantiles": {"p10": 275, "p25": 335, "p50": 385, "p75": 430, "p90": 470}}}},
            {"id": "crystal_harpoon", "label": "Crystal harpoon", "overrides": {"requirements": {"members": True, "fishing": 71, "equipment": ["Crystal harpoon"]}, "throughput": {"quantiles": {"p10": 290, "p25": 350, "p50": 400, "p75": 445, "p90": 485}}}},
        ], interval=45,
    )
    add("fishing_v2_anglerfish", "Catch anglerfish", "gathering/fishing", [out("Raw anglerfish")], 135, "fishing", 82, ["Fishing rod"], "https://oldschool.runescape.wiki/w/Anglerfish", quantiles=(85, 110, 135, 160, 185), model={"fishing": {"levelScaling": True, "supportsRadasBlessing": True, "supportsSpiritFlakes": True, "fishBarrelAffectsBanking": True}}, interval=90)
    add("fishing_v2_karambwan", "Catch raw karambwan", "gathering/fishing", [out("Raw karambwan")], 600, "fishing", 65, ["Karambwan vessel"], "https://oldschool.runescape.wiki/w/Raw_karambwan", quantiles=(430, 520, 600, 670, 720), model={"fishing": {"levelScaling": True, "supportsRadasBlessing": True, "supportsSpiritFlakes": True, "fishBarrelAffectsBanking": True}}, interval=120)

    for key, ore, level, rate, q in (
        ("amethyst", "Amethyst", 92, 90, (55, 72, 90, 105, 118)),
        ("runite", "Runite ore", 85, 45, (20, 32, 45, 58, 70)),
        ("gem_rocks", "Uncut sapphire", 40, 420, (280, 350, 420, 485, 535)),
    ):
        add(f"mining_v2_{key}", f"Mine {key.replace('_', ' ')}", "gathering/mining", [out(ore)], rate, "mining", level, ["Best available pickaxe"], "https://oldschool.runescape.wiki/w/Mining", quantiles=q, model={"mining": {"levelScaling": True, "pickaxeTier": True, "celestialRing": True, "varrockArmour": True, "miningGloves": True, "miningGuildBonus": True, "depletionModel": True}})

    add("mining_v2_motherlode", "Motherlode Mine", "gathering/mining", [out("Coal", quantity_expected=.55, quantity_minimum=0), out("Gold ore", quantity_expected=.18, quantity_minimum=0), out("Mithril ore", quantity_expected=.17, quantity_minimum=0), out("Adamantite ore", quantity_expected=.08, quantity_minimum=0), out("Runite ore", quantity_expected=.02, quantity_minimum=0)], 300, "mining", 30, ["Pickaxe"], "https://oldschool.runescape.wiki/w/Motherlode_Mine", quantiles=(200, 250, 300, 345, 380), model={"mining": {"payDirtEV": True, "nuggetEV": "untradeable_separate", "levelScaling": True, "depletionModel": True}})

    for key, log, level, rate, members, q in (
        ("yew", "Yew logs", 60, 200, False, (120, 160, 200, 235, 260)),
        ("magic", "Magic logs", 75, 130, True, (75, 100, 130, 155, 175)),
        ("redwood", "Redwood logs", 90, 160, True, (110, 135, 160, 185, 205)),
        ("camphor", "Camphor logs", 66, 385, True, (275, 330, 385, 430, 465)),
    ):
        add(f"woodcutting_v2_{key}", f"Cut {key} logs", "gathering/woodcutting", [out(log, quantity_expected=255/256, quantity_minimum=255/256), out("Bird nest", quantity_expected=1/256, quantity_minimum=0)], rate, "woodcutting", level, ["Best available axe"], "https://oldschool.runescape.wiki/w/Woodcutting", members=members, quantiles=q, model={"woodcutting": {"levelScaling": True, "axeTier": True, "forestryWorld": True, "logBasket": True, "twoHandedAxes": True, "treeRespawnDepletion": True, "forestryEventEV": "separate_untradeable", "animaBark": "separate_untradeable", "leaves": "separate", "nestRoll": 1/256, "fellingAxeRationCost": True, "locationBanking": True}})

    return methods
