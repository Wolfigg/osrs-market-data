from osrs_market.catalog_wave5 import wave5_method_catalog
from osrs_market.personalisation import materialise_method_for_player
from osrs_market.player_profile import PlayerProfile, SkillProfile


def test_ancient_tablet_requires_spellbook_unlock():
    method = wave5_method_catalog()["make_teleport_tablet_ancient_paddewwa"]
    base = dict(
        members=True,
        skills=SkillProfile(magic=99, construction=99),
        quests={"Desert Treasure I"},
    )
    unavailable = materialise_method_for_player(
        "make_teleport_tablet_ancient_paddewwa",
        method,
        PlayerProfile(**base),
    )
    assert unavailable.available is False
    assert "Requires unlock ancient_spellbook" in unavailable.unavailable_reasons

    available = materialise_method_for_player(
        "make_teleport_tablet_ancient_paddewwa",
        method,
        PlayerProfile(**base, unlocks={"Ancient spellbook"}),
    )
    assert available.available is True


def test_standard_tablet_uses_poh_feature_not_equipment():
    method = wave5_method_catalog()["make_teleport_tablet_standard_varrock"]
    missing = materialise_method_for_player(
        "make_teleport_tablet_standard_varrock",
        method,
        PlayerProfile(members=True, skills=SkillProfile(magic=99, construction=99)),
    )
    assert missing.available is False
    assert any("Oak lectern" in reason for reason in missing.unavailable_reasons)

    available = materialise_method_for_player(
        "make_teleport_tablet_standard_varrock",
        method,
        PlayerProfile(
            members=True,
            skills=SkillProfile(magic=99, construction=99),
            poh_features={"Oak lectern"},
        ),
    )
    assert available.available is True
    assert available.selected_variant_id == "minimum_lectern"


def test_no_profile_preserves_catalogue_default_contract():
    method = wave5_method_catalog()["charge_water_orb"]
    result = materialise_method_for_player("charge_water_orb", method, None)
    assert result.available is True
    assert result.selected_variant_id is None
    assert result.cycles_per_hour > 0
    assert result.method["cycles_per_hour"] == method["cycles_per_hour"]
