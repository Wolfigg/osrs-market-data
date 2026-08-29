from __future__ import annotations

from typing import Any


KNOWN_TARGETS: tuple[dict[str, Any], ...] = (
    {"key": "tanning", "label": "Tanning hides", "matchPrefixes": ["tan_"], "engine": "deterministic", "priority": "high", "reference": "https://oldschool.runescape.wiki/w/Tanning"},
    {"key": "grinding", "label": "Grinding and crushing ingredients", "matchPrefixes": ["grind_", "process_secondary_"], "engine": "deterministic", "priority": "high", "reference": "https://oldschool.runescape.wiki/w/Pestle_and_mortar"},
    {"key": "arrows", "label": "Headless arrows and finished arrows", "matchPrefixes": ["make_headless_arrows", "make_bronze_arrows", "make_iron_arrows", "make_steel_arrows", "make_mithril_arrows", "make_adamant_arrows", "make_rune_arrows", "make_amethyst_arrows"], "engine": "deterministic", "priority": "high", "reference": "https://oldschool.runescape.wiki/w/Arrow"},
    {"key": "spin_flax", "label": "Spin flax variants", "matchPrefixes": ["spin_flax"], "engine": "variants", "priority": "medium", "reference": "https://oldschool.runescape.wiki/w/Flax"},
    {"key": "superglass", "label": "Superglass Make", "matchPrefixes": ["superglass_make_"], "engine": "probabilistic", "priority": "high", "reference": "https://oldschool.runescape.wiki/w/Superglass_Make"},
    {"key": "karambwan", "label": "Raw karambwan fishing", "matchPrefixes": ["catch_raw_karambwan", "gather_fishing_karambwan"], "engine": "gathering", "priority": "high", "reference": "https://oldschool.runescape.wiki/w/Money_making_guide/Catching_raw_karambwan"},
    {"key": "enchant_jewellery", "label": "Jewellery enchanting", "matchPrefixes": ["enchant_"], "engine": "variants", "priority": "high", "reference": "https://oldschool.runescape.wiki/w/Enchanting"},
    {"key": "teleport_tablets", "label": "Teleport tablets", "matchPrefixes": ["make_teleport_tablet_"], "engine": "travel", "priority": "high", "reference": "https://oldschool.runescape.wiki/w/Magic_tablet"},
    {"key": "orb_charging", "label": "Charging elemental orbs", "matchPrefixes": ["charge_air_orb", "charge_water_orb", "charge_earth_orb", "charge_fire_orb"], "engine": "travel", "priority": "high", "reference": "https://oldschool.runescape.wiki/w/Charge_Air_Orb"},
    {"key": "potion_v2", "label": "Potion system V2", "matchPrefixes": ["make_prayer_potions_v2", "make_super_attack_potions_v2", "make_stamina_potions_v2", "make_super_combat_potions_v2"], "engine": "probabilistic-input-output", "priority": "high", "reference": "https://oldschool.runescape.wiki/w/Herblore"},
    {"key": "cooking_burns", "label": "Cooking with burn probability", "matchPrefixes": ["cook_probabilistic_"], "engine": "probabilistic", "priority": "high", "reference": "https://oldschool.runescape.wiki/w/Cooking"},
    {"key": "more_gathering", "label": "Additional stochastic gathering", "matchPrefixes": ["gather_", "catch_", "cut_"], "engine": "gathering", "priority": "medium", "reference": "https://oldschool.runescape.wiki/w/Money_making_guide"},
    {"key": "forestry_outputs", "label": "Defensible Forestry secondary outputs", "matchPrefixes": ["gather_yew_logs", "gather_magic_logs", "gather_teak_logs", "gather_mahogany_logs", "gather_camphor_logs"], "engine": "probabilistic", "priority": "medium", "reference": "https://oldschool.runescape.wiki/w/Bird_nest"},
)


def build_catalog_gap_report(methods: dict[str, dict[str, Any]], discovery_audit: dict[str, Any] | None = None) -> dict[str, Any]:
    ids = sorted(str(method_id) for method_id in methods)
    rows: list[dict[str, Any]] = []
    for target in KNOWN_TARGETS:
        prefixes = list(target["matchPrefixes"])
        matches = sorted(method_id for method_id in ids if any(method_id.startswith(prefix) for prefix in prefixes))
        rows.append({"key": target["key"], "label": target["label"], "status": "covered" if matches else "missing", "engineCompatibility": target["engine"], "priority": target["priority"], "reference": target["reference"], "matchedMethodIds": matches})
    missing = [row for row in rows if row["status"] == "missing"]
    result = {"schemaVersion": 2, "catalogueMethodCount": len(ids), "targetFamilyCount": len(rows), "coveredFamilyCount": len(rows) - len(missing), "missingFamilyCount": len(missing), "coveragePct": round((len(rows) - len(missing)) / len(rows) * 100, 1) if rows else 100.0, "families": rows, "missing": missing, "discoveryPolicy": "Known-family coverage is deterministic. Wiki discovery is advisory and never auto-promotes a page or changed assumption into production."}
    if discovery_audit is not None:
        result["wikiDiscovery"] = {"pageCount": discovery_audit.get("pageCount"), "findingCount": discovery_audit.get("findingCount"), "requiresReview": discovery_audit.get("requiresReview"), "findings": discovery_audit.get("findings", [])}
    return result
