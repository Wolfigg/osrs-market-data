from osrs_market.catalog_wave5 import wave5_method_catalog
from osrs_market.personalisation import materialise_method_for_player
from osrs_market.player_profile import PlayerProfile, SkillProfile, evaluate_requirements


def profile(**overrides):
    values = {
        "members": True,
        "skills": SkillProfile(magic=99, agility=99, herblore=99, cooking=99, construction=99, mining=99),
        "equipment": set(),
        "unlocks": set(),
        "quests": set(),
        "poh_features": set(),
    }
    values.update(overrides)
    return PlayerProfile(**values)


def test_skill_requirement_blocks_and_explains():
    met, reasons = evaluate_requirements({"members": True, "agility": 80}, profile(skills=SkillProfile(agility=79)))
    assert met is False
    assert reasons == ["Requires 80 Agility"]


def test_orb_route_selection_matches_agility_thresholds():
    method = wave5_method_catalog()["charge_water_orb"]
    equipment = {"water_rune_supplying_staff"}
    expected = {69: "no_shortcut", 70: "agility_70", 79: "agility_70", 80: "agility_80"}
    for agility, variant_id in expected.items():
        account = profile(skills=SkillProfile(magic=99, agility=agility), equipment=equipment)
        result = materialise_method_for_player("charge_water_orb", method, account)
        assert result.available is True
        assert result.selected_variant_id == variant_id


def test_potion_equipment_selects_most_specific_available_variant():
    method = wave5_method_catalog()["make_prayer_potions_v2"]
    account = profile(
        skills=SkillProfile(herblore=99),
        equipment={"prescription_goggles", "amulet_of_chemistry"},
    )
    result = materialise_method_for_player("make_prayer_potions_v2", method, account)
    assert result.available is True
    assert result.selected_variant_id == "chemistry_and_goggles"
    assert set(result.applied_modifier_ids) == {"prescription_goggles", "amulet_of_chemistry"}


def test_cooking_profile_overrides_catalogue_defaults():
    method = wave5_method_catalog()["cook_probabilistic_shark"]
    account = profile(
        skills=SkillProfile(cooking=92),
        equipment={"cooking_gauntlets"},
        method_settings={"cooking": {"location": "hosidius_10"}},
    )
    result = materialise_method_for_player("cook_probabilistic_shark", method, account)
    defaults = result.method["model"]["cooking"]["defaults"]
    assert defaults == {"level": 92, "location": "hosidius_10", "gauntlets": True, "cookingCape": False}


def test_cooking_cape_is_only_applied_at_99():
    method = wave5_method_catalog()["cook_probabilistic_shark"]
    ninety_eight = materialise_method_for_player(
        "cook_probabilistic_shark", method,
        profile(skills=SkillProfile(cooking=98), equipment={"cooking_cape"}),
    )
    ninety_nine = materialise_method_for_player(
        "cook_probabilistic_shark", method,
        profile(skills=SkillProfile(cooking=99), equipment={"cooking_cape"}),
    )
    assert ninety_eight.method["model"]["cooking"]["defaults"]["cookingCape"] is False
    assert ninety_nine.method["model"]["cooking"]["defaults"]["cookingCape"] is True


def test_profile_serialisation_uses_stable_ids():
    account = PlayerProfile(
        equipment={"Cooking gauntlets", "Amulet of chemistry"},
        unlocks={"Ancient spellbook"},
        poh_features={"Oak lectern"},
    )
    encoded = account.to_dict()
    assert encoded["equipment"] == ["amulet_of_chemistry", "cooking_gauntlets"]
    assert PlayerProfile.from_dict(encoded).unlocks == {"ancient_spellbook"}
