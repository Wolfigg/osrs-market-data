from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Any

from .player_profile import PlayerProfile, evaluate_requirements


@dataclass(frozen=True, slots=True)
class RouteSegment:
    id: str
    seconds: float
    requirements: dict[str, Any] = field(default_factory=dict)
    resource_costs: tuple[dict[str, Any], ...] = ()

    def available(self, profile: PlayerProfile) -> bool:
        return evaluate_requirements(self.requirements, profile)[0]


@dataclass(frozen=True, slots=True)
class MethodRoute:
    id: str
    start: str
    destination: str
    outbound: tuple[RouteSegment, ...]
    return_route: tuple[RouteSegment, ...]
    bank_seconds: float
    process_seconds: float
    inventory_capacity: int
    requirements: dict[str, Any] = field(default_factory=dict)
    items_per_trip: int | None = None

    def available(self, profile: PlayerProfile) -> bool:
        if not evaluate_requirements(self.requirements, profile)[0]:
            return False
        return all(segment.available(profile) for segment in (*self.outbound, *self.return_route))

    @property
    def travel_seconds(self) -> float:
        return sum(segment.seconds for segment in (*self.outbound, *self.return_route))

    @property
    def cycle_seconds(self) -> float:
        return self.travel_seconds + self.bank_seconds + self.process_seconds

    @property
    def effective_capacity(self) -> int:
        return max(1, self.items_per_trip or self.inventory_capacity)

    @property
    def trips_per_hour(self) -> float:
        return 3600.0 / self.cycle_seconds if self.cycle_seconds > 0 else 0.0

    @property
    def units_per_hour(self) -> float:
        return self.trips_per_hour * self.effective_capacity


def select_fastest_route(routes: list[MethodRoute], profile: PlayerProfile) -> MethodRoute | None:
    eligible = [route for route in routes if route.available(profile)]
    if not eligible:
        return None
    return max(eligible, key=lambda route: (route.units_per_hour, route.effective_capacity, route.id))


def banking_frequency(units: float, capacity: int) -> int:
    if units <= 0:
        return 0
    return ceil(units / max(1, capacity))


def route_to_workflow(route: MethodRoute) -> dict[str, Any]:
    capacity = route.effective_capacity
    return {
        "process_seconds": route.process_seconds / capacity,
        "bank_seconds": route.bank_seconds / capacity,
        "travel_seconds": route.travel_seconds / capacity,
        "inventory_capacity": route.inventory_capacity,
        "items_per_inventory": capacity,
        "route_id": route.id,
        "trip_seconds": route.cycle_seconds,
        "trips_per_hour": route.trips_per_hour,
    }
