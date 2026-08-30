from __future__ import annotations

from typing import Any


def wave5_method_catalog() -> dict[str, dict[str, Any]]:
    """Large method families whose entries are resolved against Wiki mapping by name."""
    methods: dict[str, dict[str, Any]] = {}

    def item(name: str, quantity: float = 1, **extra: Any) -> dict[str, Any]:
        return {"item_name": name, "quantity": quantity, **extra}

    def ge(name: str, quantity: float = 1, **extra: Any) -> dict[str, Any]:
        return item(name, quantity, buy_via_ge=True, **extra)

    def out(name: str, quantity: float = 1, **extra: Any) -> dict[str, Any]:
        return item(name, quantity, **extra)

    def add(method_id: str, name: str, category: str, inputs: list[dict[str, Any]], outputs: list[dict[str, Any]], cycles_per_hour: float, interval_seconds: float, requirements: dict[str, Any], notes: str, reference: str, **extra: Any) -> None:
        method = {
            "enabled": True, "name": name, "category": category, "inputs": inputs, "outputs": outputs,
            "fixed_cost_gp_per_cycle": extra.pop("fixed_cost_gp_per_cycle", 0),
            "cycles_per_hour": cycles_per_hour,
            "theoretical_cycles_per_hour": extra.pop("theoretical_cycles_per_hour", cycles_per_hour),
            "planned_hours_per_day": 4,
            "afk": {"interval_seconds": interval_seconds, "intensity": extra.pop("intensity", "low"), "description": notes},
            "requirements": requirements, "notes": notes, "reference": reference,
        }
        method.update(extra)
        methods[method_id] = method

    enchant_tiers = {
        "sapphire": (7, (("Cosmic rune", 1), ("Water rune", 1)), "Water-rune supplying staff", {"ring": "Ring of recoil", "necklace": "Games necklace(8)", "bracelet": "Bracelet of clay", "amulet": "Amulet of magic"}),
        "emerald": (27, (("Cosmic rune", 1), ("Air rune", 3)), "Air-rune supplying staff", {"ring": "Ring of dueling(8)", "necklace": "Binding necklace", "bracelet": "Castle wars bracelet(3)", "amulet": "Amulet of defence"}),
        "ruby": (49, (("Cosmic rune", 1), ("Fire rune", 5)), "Fire-rune supplying staff", {"ring": "Ring of forging", "necklace": "Digsite pendant (5)", "bracelet": "Inoculation bracelet", "amulet": "Amulet of strength"}),
        "diamond": (57, (("Cosmic rune", 1), ("Earth rune", 10)), "Earth-rune supplying staff", {"ring": "Ring of life", "necklace": "Phoenix necklace", "bracelet": "Abyssal bracelet(5)", "amulet": "Amulet of power"}),
        "dragonstone": (68, (("Cosmic rune", 1), ("Water rune", 15), ("Earth rune", 15)), "Mud battlestaff or equivalent", {"ring": "Ring of wealth (5)", "necklace": "Skills necklace(4)", "bracelet": "Combat bracelet(4)", "amulet": "Amulet of glory(4)"}),
        "onyx": (87, (("Cosmic rune", 1), ("Earth rune", 20), ("Fire rune", 20)), "Lava battlestaff or equivalent", {"ring": "Ring of stone", "necklace": "Berserker necklace", "bracelet": "Regen bracelet", "amulet": "Amulet of fury"}),
        "zenyte": (93, (("Cosmic rune", 1), ("Blood rune", 20), ("Soul rune", 20)), None, {"ring": "Ring of suffering", "necklace": "Necklace of anguish", "bracelet": "Tormented bracelet", "amulet": "Amulet of torture"}),
    }
    for gem, (level, runes, staff, outputs) in enchant_tiers.items():
        for piece, product in outputs.items():
            raw = "Dragon necklace" if gem == "dragonstone" and piece == "necklace" else f"{gem.title()} {piece}"
            variants = [{"id": "runes", "label": "Runes only", "overrides": {"inputs": [ge(raw), *[ge(n, q) for n, q in runes]], "requirements": {"members": True, "magic": level}}}]
            if staff:
                variants.append({"id": "rune_staff", "label": staff, "overrides": {"inputs": [ge(raw), ge("Cosmic rune")], "requirements": {"members": True, "magic": level, "equipment": [staff]}}})
            add(f"enchant_{gem}_{piece}", f"Enchant {gem} {piece}", "bankstanding/magic", [ge(raw), *[ge(n, q) for n, q in runes]], [out(product)], 1600, 2.25, {"members": True, "magic": level}, "Level-enchant jewellery conversion with full-rune and reusable elemental-staff variants where applicable.", "https://oldschool.runescape.wiki/w/Enchanting", theoretical_cycles_per_hour=1600, variants=variants, method_types=["bankstanding", "variants"], intensity="moderate")

    # Digsite pendants are untradeable in OSRS, so this conversion cannot be
    # valued by the GE profit engine. Keep the catalogue definition for family
    # coverage but disable it until untradeable-output economics are supported.
    methods["enchant_ruby_necklace"]["enabled"] = False
    methods["enchant_ruby_necklace"]["notes"] += " Output is an untradeable Digsite pendant and is intentionally excluded from GE profit ranking."

    orb_specs = {
        "water": (56, "Water orb", "Water-rune supplying staff", (("agility_80", "80 Agility shortcut", 505, 185, {"agility": 80}), ("agility_70", "70 Agility shortcut", 450, 205, {"agility": 70}), ("no_shortcut", "No shortcut", 280, 325, {}))),
        "earth": (60, "Earth orb", "Earth-rune supplying staff", (("edgeville_glory", "Edgeville glory route", 470, 205, {}),)),
        "fire": (63, "Fire orb", "Fire-rune supplying staff", (("agility_80", "80 Agility shortcut", 505, 185, {"agility": 80}), ("agility_70", "70 Agility shortcut", 450, 205, {"agility": 70}), ("no_shortcut", "No shortcut", 280, 325, {}))),
        "air": (66, "Air orb", "Air-rune supplying staff", (("edgeville_energy", "Edgeville + energy potions", 525, 170, {"supplies": ["Energy potions"]}), ("poh_pool", "POH restoration pool", 480, 185, {"construction": 47}))),
    }
    for element, (level, product, staff, routes) in orb_specs.items():
        variants = []
        for route_id, label, rate, round_trip, extra_req in routes:
            req = {"members": True, "magic": level, "equipment": [staff], **extra_req}
            variants.append({"id": route_id, "label": label, "overrides": {"cycles_per_hour": rate, "theoretical_cycles_per_hour": rate, "requirements": req, "workflow": {"process_seconds": 1.8, "bank_seconds": 12 / 26, "travel_seconds": max(0, round_trip / 26 - 1.8 - 12 / 26), "inventory_size": 28, "items_per_inventory": 26}}})
        add(f"charge_{element}_orb", f"Charge {element} orbs", "processing/magic", [ge("Unpowered orb"), ge("Cosmic rune", 3)], [out(product)], routes[0][2], 45, {"members": True, "magic": level, "equipment": [staff]}, "Route-aware orb charging with banking/travel throughput. Elemental runes are supplied by reusable equipment.", f"https://oldschool.runescape.wiki/w/Money_making_guide/Charging_{element}_orbs", variants=variants, method_types=["processing", "variants", "travel"])

    standard = (
        ("varrock", "Varrock teleport (tablet)", 25, (("Law rune", 1), ("Air rune", 3), ("Fire rune", 1)), "Oak lectern", 40),
        ("lumbridge", "Lumbridge teleport (tablet)", 31, (("Law rune", 1), ("Air rune", 3), ("Earth rune", 1)), "Eagle lectern", 47),
        ("falador", "Falador teleport (tablet)", 37, (("Law rune", 1), ("Air rune", 3), ("Water rune", 1)), "Eagle lectern", 47),
        ("house", "Teleport to house (tablet)", 40, (("Law rune", 1), ("Air rune", 1), ("Earth rune", 1)), "Mahogany eagle lectern", 67),
        ("camelot", "Camelot teleport (tablet)", 45, (("Law rune", 1), ("Air rune", 5)), "Teak eagle lectern", 57),
        ("kourend_castle", "Kourend castle teleport (tablet)", 48, (("Law rune", 2), ("Water rune", 1), ("Fire rune", 1)), "Teak eagle lectern", 57),
        ("ardougne", "Ardougne teleport (tablet)", 51, (("Law rune", 2), ("Water rune", 2)), "Teak eagle lectern", 57),
        ("civitas_illa_fortis", "Civitas illa fortis teleport", 54, (("Law rune", 2), ("Earth rune", 1), ("Fire rune", 1)), "Mahogany eagle lectern", 67),
        ("watchtower", "Watchtower teleport (tablet)", 58, (("Law rune", 2), ("Earth rune", 2)), "Mahogany eagle lectern", 67),
        ("summon_boat", "Summon boat", 56, (("Law rune", 2), ("Earth rune", 1), ("Water rune", 1)), "Mahogany eagle lectern", 67),
        ("teleport_to_boat", "Teleport to boat", 67, (("Law rune", 2), ("Earth rune", 2), ("Water rune", 2)), "Mahogany eagle lectern", 67),
    )
    for key, product, level, runes, lectern, construction in standard:
        add(f"make_teleport_tablet_standard_{key}", f"Make {product} tablets", "bankstanding/magic", [ge("Soft clay"), *[ge(n, q) for n, q in runes]], [out(product)], 1200, 2.4, {"members": True, "magic": level, "construction": construction, "poh_features": [lectern]}, "Standard spellbook teleport tablet. Four-tick creation plus banking overhead.", "https://oldschool.runescape.wiki/w/Magic_tablet", theoretical_cycles_per_hour=1500, workflow={"process_seconds": 2.4, "bank_seconds": 0.6, "travel_seconds": 0}, variants=[{"id": "minimum_lectern", "label": lectern, "overrides": {}}, {"id": "marble_lectern", "label": "Marble lectern", "overrides": {"requirements": {"members": True, "magic": level, "construction": 77, "poh_features": ["Marble lectern"]}}}], method_types=["bankstanding", "variants"])

    ancient = (
        ("paddewwa", "Paddewwa teleport (tablet)", 54, (("Law rune", 2), ("Air rune", 1), ("Fire rune", 1))), ("senntisten", "Senntisten teleport (tablet)", 60, (("Law rune", 2), ("Soul rune", 1))), ("kharyrll", "Kharyrll teleport (tablet)", 66, (("Law rune", 2), ("Blood rune", 1))), ("lassar", "Lassar teleport (tablet)", 72, (("Law rune", 2), ("Water rune", 4))), ("dareeyak", "Dareeyak teleport (tablet)", 78, (("Law rune", 2), ("Air rune", 2), ("Fire rune", 3))), ("carrallanger", "Carrallanger teleport (tablet)", 84, (("Law rune", 2), ("Soul rune", 2))), ("annakarl", "Annakarl teleport (tablet)", 90, (("Law rune", 2), ("Blood rune", 2))), ("ghorrock", "Ghorrock teleport (tablet)", 96, (("Law rune", 2), ("Water rune", 8))),
    )
    lunar = (
        ("moonclan", "Moonclan teleport (tablet)", 69, (("Law rune", 1), ("Astral rune", 2), ("Earth rune", 2))), ("ourania", "Ourania teleport (tablet)", 71, (("Law rune", 1), ("Astral rune", 2), ("Earth rune", 6))), ("waterbirth", "Waterbirth teleport (tablet)", 72, (("Law rune", 1), ("Astral rune", 2), ("Water rune", 1))), ("barbarian", "Barbarian teleport (tablet)", 75, (("Law rune", 2), ("Astral rune", 2), ("Fire rune", 3))), ("khazard", "Khazard teleport (tablet)", 78, (("Law rune", 2), ("Astral rune", 2), ("Water rune", 4))), ("fishing_guild", "Fishing guild teleport (tablet)", 85, (("Law rune", 3), ("Astral rune", 3), ("Water rune", 10))), ("catherby", "Catherby teleport (tablet)", 87, (("Law rune", 3), ("Astral rune", 3), ("Water rune", 10))), ("ice_plateau", "Ice plateau teleport (tablet)", 89, (("Law rune", 3), ("Astral rune", 3), ("Water rune", 8))),
    )
    for book, rows, equipment, quest in (("ancient", ancient, "Ancient Pyramid lectern", "Desert Treasure I"), ("lunar", lunar, "Lunar Isle ceremonial building lectern", "Lunar Diplomacy")):
        for key, product, level, runes in rows:
            add(f"make_teleport_tablet_{book}_{key}", f"Make {product} tablets", "bankstanding/magic", [ge("Soft clay"), *[ge(n, q) for n, q in runes]], [out(product)], 1200, 2.4, {"members": True, "magic": level, "quests": [quest], "unlocks": [f"{book}_spellbook"]}, f"{book.title()} teleport tablet with its dedicated lectern requirement.", "https://oldschool.runescape.wiki/w/Magic_tablet", theoretical_cycles_per_hour=1500, workflow={"process_seconds": 2.4, "bank_seconds": 0.6, "travel_seconds": 0}, method_types=["bankstanding"])

    arceuus = (("arceuus_library", "Arceuus library teleport (tablet)", 6), ("draynor_manor", "Draynor manor teleport (tablet)", 17), ("battlefront", "Battlefront teleport (tablet)", 23), ("mind_altar", "Mind altar teleport (tablet)", 28), ("salve_graveyard", "Salve graveyard teleport (tablet)", 40), ("fenkenstrain", "Fenkenstrain's castle teleport (tablet)", 48), ("west_ardougne", "West ardougne teleport (tablet)", 61), ("harmony_island", "Harmony island teleport (tablet)", 65), ("cemetery", "Cemetery teleport (tablet)", 71), ("barrows", "Barrows teleport (tablet)", 83), ("ape_atoll", "Ape atoll teleport (tablet)", 90))
    for key, product, level in arceuus:
        add(f"make_teleport_tablet_arceuus_{key}", f"Make {product} tablets", "bankstanding/magic", [], [out(product)], 1200, 2.4, {"members": True, "magic": level, "mining": 38, "unlocks": ["arceuus_spellbook"], "supplies": ["Self-supplied dark essence block and spell runes"]}, "Arceuus tablets consume an untradeable dark essence block. This catalogue entry intentionally reports market revenue only until an integrated essence/time model is available.", "https://oldschool.runescape.wiki/w/Magic_tablet", theoretical_cycles_per_hour=1500, model={"unpricedInputs": ["Dark essence block", "Spell runes pending recipe audit"]}, method_types=["bankstanding"])

    potions = (
        ("attack", "Guam potion (unf)", "Eye of newt", "Attack potion(3)", 3), ("antipoison", "Marrentill potion (unf)", "Unicorn horn dust", "Antipoison(3)", 5), ("strength", "Tarromin potion (unf)", "Limpwurt root", "Strength potion(3)", 12), ("restore", "Harralander potion (unf)", "Red spiders' eggs", "Restore potion(3)", 22), ("energy", "Harralander potion (unf)", "Chocolate dust", "Energy potion(3)", 26), ("agility", "Toadflax potion (unf)", "Toad's legs", "Agility potion(3)", 34), ("combat", "Harralander potion (unf)", "Goat horn dust", "Combat potion(3)", 36), ("prayer", "Ranarr potion (unf)", "Snape grass", "Prayer potion(3)", 38), ("super_attack", "Irit potion (unf)", "Eye of newt", "Super attack(3)", 45), ("superantipoison", "Irit potion (unf)", "Unicorn horn dust", "Superantipoison(3)", 48), ("fishing", "Avantoe potion (unf)", "Snape grass", "Fishing potion(3)", 50), ("super_energy", "Avantoe potion (unf)", "Mort myre fungus", "Super energy(3)", 52), ("hunter", "Avantoe potion (unf)", "Kebbit teeth dust", "Hunter potion(3)", 53), ("super_strength", "Kwuarm potion (unf)", "Limpwurt root", "Super strength(3)", 55), ("weapon_poison", "Kwuarm potion (unf)", "Dragon scale dust", "Weapon poison", 60), ("super_restore", "Snapdragon potion (unf)", "Red spiders' eggs", "Super restore(3)", 63), ("super_defence", "Cadantine potion (unf)", "White berries", "Super defence(3)", 66), ("antifire", "Lantadyme potion (unf)", "Dragon scale dust", "Antifire potion(3)", 69), ("ranging", "Dwarf weed potion (unf)", "Wine of zamorak", "Ranging potion(3)", 72), ("magic", "Lantadyme potion (unf)", "Potato cactus", "Magic potion(3)", 76), ("zamorak_brew", "Torstol potion (unf)", "Jangerberries", "Zamorak brew(3)", 78), ("saradomin_brew", "Toadflax potion (unf)", "Crushed nest", "Saradomin brew(3)", 81),
    )
    for key, unf, secondary, product3, level in potions:
        chemistry = product3.endswith("(3)")
        variants = [{"id": "standard", "label": "Standard", "overrides": {}}, {"id": "prescription_goggles", "label": "Prescription goggles", "overrides": {"inputs": [ge(unf), ge(secondary, 1, quantity_expected=0.9, quantity_maximum=1)], "requirements": {"members": True, "herblore": level, "equipment": ["Prescription goggles"]}}}]
        if chemistry:
            product4 = product3[:-3] + "(4)"
            variants += [{"id": "amulet_of_chemistry", "label": "Amulet of chemistry", "overrides": {"inputs": [ge(unf), ge(secondary), ge("Amulet of chemistry", 1, quantity_expected=0.01, quantity_maximum=0.2)], "outputs": [out(product3, 1, quantity_expected=0.95, quantity_minimum=0.95), out(product4, 1, quantity_expected=0.05, quantity_minimum=0.05)], "requirements": {"members": True, "herblore": level, "equipment": ["Amulet of chemistry"]}}}, {"id": "chemistry_and_goggles", "label": "Chemistry + goggles", "overrides": {"inputs": [ge(unf), ge(secondary, 1, quantity_expected=0.9, quantity_maximum=1), ge("Amulet of chemistry", 1, quantity_expected=0.01, quantity_maximum=0.2)], "outputs": [out(product3, 1, quantity_expected=0.95, quantity_minimum=0.95), out(product4, 1, quantity_expected=0.05, quantity_minimum=0.05)], "requirements": {"members": True, "herblore": level, "equipment": ["Amulet of chemistry", "Prescription goggles"]}}}]
        add(f"make_{key}_potions_v2", f"Make {product3.replace('(3)', '')}", "bankstanding/herblore", [ge(unf), ge(secondary)], [out(product3)], 2500, 16.8, {"members": True, "herblore": level}, "Potion V2: true dose output, chemistry 4-dose EV and prescription-goggle expected secondary consumption.", "https://oldschool.runescape.wiki/w/Herblore", theoretical_cycles_per_hour=2500, variants=variants, model={"doseModel": {"chemistryProcChance": 0.05 if chemistry else 0, "gogglesSaveChance": 0.10}}, method_types=["bankstanding", "variants", "probabilistic"])

    add("make_stamina_potions_v2", "Make stamina potion(4)", "bankstanding/herblore", [ge("Super energy(4)"), ge("Amylase crystal", 4)], [out("Stamina potion(4)")], 2400, 18, {"members": True, "herblore": 77}, "True four-dose stamina recipe; chemistry is not applied to an already four-dose result.", "https://oldschool.runescape.wiki/w/Stamina_potion", theoretical_cycles_per_hour=2500, method_types=["bankstanding"])
    add("make_super_combat_potions_v2", "Make super combat potion(4)", "bankstanding/herblore", [ge("Super attack(4)"), ge("Super strength(4)"), ge("Super defence(4)"), ge("Torstol")], [out("Super combat potion(4)"), out("Vial", 2)], 2166, 8.6, {"members": True, "herblore": 90}, "Four-dose recipe with two recovered vials. Goggles variant values the 10% torstol save.", "https://oldschool.runescape.wiki/w/Super_combat_potion", theoretical_cycles_per_hour=2400, variants=[{"id": "standard", "label": "Standard", "overrides": {}}, {"id": "prescription_goggles", "label": "Prescription goggles", "overrides": {"inputs": [ge("Super attack(4)"), ge("Super strength(4)"), ge("Super defence(4)"), ge("Torstol", 1, quantity_expected=0.9, quantity_maximum=1)], "cycles_per_hour": 2400, "requirements": {"members": True, "herblore": 90, "equipment": ["Prescription goggles"]}}}], method_types=["bankstanding", "variants", "probabilistic"])

    for key, source, product in (("crushed_nests", "Bird nest (empty)", "Crushed nest"), ("goat_horn_dust", "Goat horn", "Goat horn dust"), ("kebbit_teeth_dust", "Kebbit teeth", "Kebbit teeth dust")):
        add(f"process_secondary_{key}", f"Process {product}", "bankstanding/herblore", [ge(source)], [out(product)], 3600, 7.2, {"members": True, "equipment": ["Pestle and mortar"]}, "Secondary-ingredient processing for potion supply chains.", "https://oldschool.runescape.wiki/w/Herblore", theoretical_cycles_per_hour=5000, method_types=["bankstanding"])

    cooking = {
        "monkfish": ("Raw monkfish", "Monkfish", 62, True, {"fire": (11, 275), "range": (13, 280), "hosidius_5": (25, 292), "hosidius_10": (38, 305), "gauntlets_fire": (24, 290), "gauntlets_range": (24, 290), "gauntlets_hosidius_5": (36, 302), "gauntlets_hosidius_10": (49, 315)}),
        "shark": ("Raw shark", "Shark", 80, True, {"fire": (1, 202), "range": (1, 232), "hosidius_5": (13, 244), "hosidius_10": (26, 257), "gauntlets_fire": (15, 270), "gauntlets_range": (15, 270), "gauntlets_hosidius_5": (27, 282), "gauntlets_hosidius_10": (40, 295)}),
        "anglerfish": ("Raw anglerfish", "Anglerfish", 84, True, {"fire": (1, 200), "range": (1, 220), "hosidius_5": (13, 232), "hosidius_10": (26, 245), "gauntlets_fire": (12, 260), "gauntlets_range": (12, 260), "gauntlets_hosidius_5": (24, 272), "gauntlets_hosidius_10": (37, 285)}),
        "dark_crabs": ("Raw dark crab", "Dark crab", 90, False, {"fire": (10, 222), "range": (10, 222), "hosidius_5": (22, 234), "hosidius_10": (35, 247)}),
    }
    for key, (raw, cooked, level, gauntlets, curves) in cooking.items():
        add(f"cook_probabilistic_{key}", f"Cook {raw.removeprefix('Raw ').lower()}", "strict_afk/cooking", [ge(raw)], [out(cooked)], 1300, 67.2, {"members": True, "cooking": level}, "User-level burn model using Wiki skilling-success chart parameters, location, gauntlets and explicit 99/Cooking-cape zero-burn mode.", "https://oldschool.runescape.wiki/w/Cooking", theoretical_cycles_per_hour=1500, model={"cooking": {"minimumLevel": level, "gauntletsAffected": gauntlets, "curves": {n: {"low": lo, "high": hi} for n, (lo, hi) in curves.items()}, "defaults": {"level": 99, "location": "range", "gauntlets": False, "cookingCape": True}}}, method_types=["bankstanding", "make-x", "probabilistic"])

    for key, log_name, level, rate, members in (("yew_logs", "Yew logs", 60, 200, False), ("magic_logs", "Magic logs", 75, 130, True), ("teak_logs", "Teak logs", 35, 550, True), ("mahogany_logs", "Mahogany logs", 50, 390, True), ("camphor_logs", "Camphor logs", 66, 385, True)):
        add(f"gather_{key}", f"Cut {log_name.lower()}", "gathering/woodcutting", [], [out(log_name)], rate, 75, {"members": members, "woodcutting": level, "equipment": ["Rune axe or better"]}, "Includes only the defensible standard 1/256 bird-nest roll. Forestry event rewards and clue-nest contents are excluded from EV.", "https://oldschool.runescape.wiki/w/Bird_nest", model={"excludedExpectedOutputs": ["Forestry event rewards", "Clue nest contents", "Nest contents"]}, method_types=["gathering", "probabilistic"])

    for key, ore, level, rate, members in (("iron", "Iron ore", 15, 900, False), ("coal", "Coal", 30, 350, False), ("mithril", "Mithril ore", 55, 180, False), ("adamantite", "Adamantite ore", 70, 110, False), ("runite", "Runite ore", 85, 45, False), ("amethyst", "Amethyst", 92, 90, True)):
        add(f"gather_mining_{key}", f"Mine {ore.lower()}", "gathering/mining", [], [out(ore)], rate, 45, {"members": members, "mining": level, "equipment": ["Best available pickaxe"]}, "Primary tradeable mining output only; random secondaries are excluded without a stable source-backed probability.", "https://oldschool.runescape.wiki/w/Mining", method_types=["gathering"])

    for key, raw, level, rate, equipment, members in (("lobster", "Raw lobster", 40, 220, ["Lobster pot"], False), ("swordfish", "Raw swordfish", 50, 190, ["Harpoon"], False), ("monkfish", "Raw monkfish", 62, 320, ["Small fishing net"], True), ("karambwan", "Raw karambwan", 65, 600, ["Karambwan vessel"], True), ("shark", "Raw shark", 76, 150, ["Harpoon"], True), ("anglerfish", "Raw anglerfish", 82, 140, ["Fishing rod"], True), ("dark_crabs", "Raw dark crab", 85, 308, ["Lobster pot"], True)):
        inputs = [ge("Dark fishing bait")] if key == "dark_crabs" else ([ge("Sandworms")] if key == "anglerfish" else [])
        req: dict[str, Any] = {"members": members, "fishing": level, "equipment": equipment}
        if key == "karambwan": req.update({"quests": ["Tai Bwo Wannai Trio"], "supplies": ["Self-supplied raw karambwanji bait"]})
        add(f"gather_fishing_{key}", f"Catch {raw.lower()}", "gathering/fishing", inputs, [out(raw)], rate, 90, req, "Fishing-family primary catch model. Tertiary clue/reward outputs are excluded unless a stable auditable EV rule is available.", "https://oldschool.runescape.wiki/w/Fishing", fixed_cost_gp_per_cycle=50 if key == "dark_crabs" else 0, method_types=["gathering"])

    return methods
