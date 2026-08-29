from __future__ import annotations

from typing import Any


def evaluate_route(route: dict[str, Any] | None) -> dict[str, Any] | None:
    if not route:
        return None
    total = 0.0
    variance = 0.0
    movement_cost = 0.0
    steps: list[dict[str, Any]] = []
    for index, raw in enumerate(route.get("steps") or []):
        seconds = max(0.0, float(raw.get("seconds", 0) or 0))
        variance_seconds = max(0.0, float(raw.get("variance_seconds", 0) or 0))
        cost = max(0.0, float(raw.get("cost_gp", 0) or 0))
        total += seconds
        variance += variance_seconds * variance_seconds
        movement_cost += cost
        steps.append({"index": index, "kind": str(raw.get("kind") or "other"), "label": str(raw.get("label") or "Step"), "seconds": seconds, "varianceSeconds": variance_seconds, "costGp": cost})
    items = float(route.get("items_per_trip", 0) or 0)
    trips = 3600.0 / total if total > 0 else None
    return {"routeId": route.get("id"), "label": route.get("label"), "tripSeconds": total, "tripStdDevSeconds": variance ** 0.5, "itemsPerTrip": items, "tripsPerHour": trips, "itemsPerHour": items * trips if trips is not None else None, "movementCostGpPerTrip": movement_cost, "movementCostGpPerHour": movement_cost * trips if trips is not None else None, "runEnergyAssumption": route.get("run_energy"), "steps": steps}


def route_cycles_per_hour(method: dict[str, Any]) -> float | None:
    result = evaluate_route(method.get("route"))
    return float(result["itemsPerHour"]) if result and result.get("itemsPerHour") is not None else None


def route_fixed_cost_per_cycle(method: dict[str, Any]) -> float:
    result = evaluate_route(method.get("route"))
    if not result:
        return 0.0
    items = float(result.get("itemsPerTrip") or 0)
    cost = float(result.get("movementCostGpPerTrip") or 0)
    return cost / items if items > 0 else 0.0
