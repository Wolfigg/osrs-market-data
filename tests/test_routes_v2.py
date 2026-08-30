import pytest

from osrs_market.player_profile import PlayerProfile, SkillProfile
from osrs_market.routes_v2 import MethodRoute, RouteSegment, banking_frequency, select_fastest_route


def orb_routes():
    return [
        MethodRoute(
            id="no_shortcut",
            start="bank",
            destination="obelisk",
            outbound=(RouteSegment("out", 130),),
            return_route=(RouteSegment("back", 130),),
            bank_seconds=12,
            process_seconds=47,
            inventory_capacity=28,
            items_per_trip=26,
        ),
        MethodRoute(
            id="agility_70",
            start="bank",
            destination="obelisk",
            outbound=(RouteSegment("out", 70, {"agility": 70}),),
            return_route=(RouteSegment("back", 70, {"agility": 70}),),
            bank_seconds=12,
            process_seconds=47,
            inventory_capacity=28,
            items_per_trip=26,
        ),
        MethodRoute(
            id="agility_80",
            start="bank",
            destination="obelisk",
            outbound=(RouteSegment("out", 58, {"agility": 80}),),
            return_route=(RouteSegment("back", 58, {"agility": 80}),),
            bank_seconds=12,
            process_seconds=47,
            inventory_capacity=28,
            items_per_trip=26,
        ),
    ]


@pytest.mark.parametrize(
    ("level", "expected"),
    [(69, "no_shortcut"), (70, "agility_70"), (79, "agility_70"), (80, "agility_80")],
)
def test_orb_route_selection_by_agility(level, expected):
    profile = PlayerProfile(skills=SkillProfile(agility=level))
    route = select_fastest_route(orb_routes(), profile)
    assert route is not None
    assert route.id == expected


def test_shared_bank_time_and_capacity_are_reusable():
    route = orb_routes()[0]
    assert route.cycle_seconds == 319
    assert route.effective_capacity == 26
    assert route.units_per_hour == pytest.approx(3600 / 319 * 26)
    assert banking_frequency(100, 28) == 4
