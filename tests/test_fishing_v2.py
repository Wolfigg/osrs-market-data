import pytest

from osrs_market.gathering_v2 import CatchDistributionEntry, FishingModel, materialise_fishing
from osrs_market.player_profile import PlayerProfile, SkillProfile
from osrs_market.routes_v2 import MethodRoute, RouteSegment


def route(bank_seconds=12.0):
    return MethodRoute(
        id="bank_route",
        start="bank",
        destination="spot",
        outbound=(RouteSegment("out", 20),),
        return_route=(RouteSegment("back", 20),),
        bank_seconds=bank_seconds,
        process_seconds=0,
        inventory_capacity=28,
        items_per_trip=28,
    )


def mixed_model():
    return FishingModel(
        spot_id="harpoon_tuna_swordfish",
        minimum_level=50,
        base_catches_per_hour=200,
        catches=(
            CatchDistributionEntry("Raw tuna", 0.60),
            CatchDistributionEntry("Raw swordfish", 0.40),
        ),
        banking_routes=(route(0),),
        supports_fish_barrel=True,
        supports_spirit_flakes=True,
        supports_radas_blessing=True,
        tool_options=("Harpoon",),
        source={"spiritFlakeProcChance": 0.50},
    )


def player(*equipment):
    return PlayerProfile(skills=SkillProfile(fishing=99), equipment=set(equipment) | {"Harpoon"})


def test_mixed_catch_exposes_both_expected_outputs():
    result = materialise_fishing(mixed_model(), player(), pacing="active")
    assert result.available
    assert result.outputs_per_hour["Raw tuna"] == pytest.approx(120)
    assert result.outputs_per_hour["Raw swordfish"] == pytest.approx(80)


def test_fish_barrel_changes_bank_frequency_not_catch_distribution():
    base = materialise_fishing(mixed_model(), player(), pacing="active")
    barrel = materialise_fishing(mixed_model(), player("Fish barrel"), pacing="active")

    assert base.outputs_per_hour == barrel.outputs_per_hour
    assert base.capacity == 28
    assert barrel.capacity == 56
    assert barrel.banks_per_hour == pytest.approx(base.banks_per_hour / 2)
    assert "fish_barrel" in barrel.applied_modifiers


@pytest.mark.parametrize(
    ("blessing", "multiplier"),
    [
        ("Rada's blessing 1", 1.02),
        ("Rada's blessing 2", 1.04),
        ("Rada's blessing 3", 1.06),
        ("Rada's blessing 4", 1.08),
    ],
)
def test_radas_blessing_tiers_use_documented_extra_fish_chances(blessing, multiplier):
    base = materialise_fishing(mixed_model(), player(), pacing="active")
    blessed = materialise_fishing(mixed_model(), player(blessing), pacing="active")
    assert sum(blessed.outputs_per_hour.values()) == pytest.approx(sum(base.outputs_per_hour.values()) * multiplier)


def test_radas_blessing_stable_profile_id_is_accepted():
    base = materialise_fishing(mixed_model(), player(), pacing="active")
    blessed = materialise_fishing(mixed_model(), player("radas_blessing_4"), pacing="active")
    assert sum(blessed.outputs_per_hour.values()) == pytest.approx(sum(base.outputs_per_hour.values()) * 1.08)
    assert "radas_blessing_4" in blessed.applied_modifiers


def test_spirit_flakes_add_output_and_expected_flake_cost():
    base = materialise_fishing(mixed_model(), player(), pacing="active")
    flakes = materialise_fishing(mixed_model(), player("Spirit flakes"), pacing="active")

    assert sum(flakes.outputs_per_hour.values()) == pytest.approx(sum(base.outputs_per_hour.values()) * 1.5)
    assert flakes.inputs_per_hour["Spirit flakes"] == pytest.approx(sum(base.outputs_per_hour.values()) * 0.5)
    assert "spirit_flakes" in flakes.applied_modifiers


def test_rada_and_spirit_flakes_stack_without_charging_flakes_for_rada_fish():
    base = materialise_fishing(mixed_model(), player(), pacing="active")
    combined = materialise_fishing(mixed_model(), player("Rada's blessing 4", "Spirit flakes"), pacing="active")
    assert sum(combined.outputs_per_hour.values()) == pytest.approx(sum(base.outputs_per_hour.values()) * 1.58)
    assert combined.inputs_per_hour["Spirit flakes"] == pytest.approx(sum(base.outputs_per_hour.values()) * 0.5)


def test_pacing_profiles_do_not_claim_one_universal_rate():
    active = materialise_fishing(mixed_model(), player(), pacing="active")
    realistic = materialise_fishing(mixed_model(), player(), pacing="realistic")
    afk = materialise_fishing(mixed_model(), player(), pacing="afk")
    assert active.actions_per_hour > realistic.actions_per_hour > afk.actions_per_hour
