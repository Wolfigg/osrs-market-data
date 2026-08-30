from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .player_profile import PlayerProfile, evaluate_requirements, stable_id
from .routes_v2 import MethodRoute, select_fastest_route


@dataclass(frozen=True, slots=True)
class CatchDistributionEntry:
    item_name: str
    probability: float
    quantity: float = 1.0

    def expected_quantity(self) -> float:
        return self.probability * self.quantity


@dataclass(frozen=True, slots=True)
class PacingProfile:
    id: str
    multiplier: float
    description: str = ""


@dataclass(frozen=True, slots=True)
class FishingModel:
    spot_id: str
    minimum_level: int
    base_catches_per_hour: float
    catches: tuple[CatchDistributionEntry, ...]
    banking_routes: tuple[MethodRoute, ...] = ()
    supports_fish_barrel: bool = False
    supports_spirit_flakes: bool = False
    supports_radas_blessing: bool = False
    tool_options: tuple[str, ...] = ()
    requirements: dict[str, Any] = field(default_factory=dict)
    pacing_profiles: tuple[PacingProfile, ...] = (
        PacingProfile("active", 1.0, "Sustained active play."),
        PacingProfile("realistic", 0.90, "Realistic continuous play with normal reaction delay."),
        PacingProfile("afk", 0.75, "Lower-attention play with missed spot movement and banking delay."),
    )
    source: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GatheringModel:
    activity_type: str
    minimum_level: int
    base_actions_per_hour: float
    output_distribution: tuple[CatchDistributionEntry, ...]
    banking_routes: tuple[MethodRoute, ...] = ()
    requirements: dict[str, Any] = field(default_factory=dict)
    supported_modifiers: tuple[str, ...] = ()
    action_ticks: float | None = None
    success_model: dict[str, Any] | None = None
    depletion_model: dict[str, Any] | None = None
    respawn_model: dict[str, Any] | None = None
    source: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GatheringResult:
    available: bool
    reasons: list[str]
    actions_per_hour: float
    outputs_per_hour: dict[str, float]
    inputs_per_hour: dict[str, float]
    selected_route_id: str | None
    banks_per_hour: float | None
    capacity: int | None
    applied_modifiers: list[str]
    pacing: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _pacing_multiplier(profiles: tuple[PacingProfile, ...], pacing: str) -> float:
    wanted = stable_id(pacing)
    for profile in profiles:
        if stable_id(profile.id) == wanted:
            return max(0.0, float(profile.multiplier))
    raise ValueError(f"unknown pacing profile: {pacing}")


def _rada_extra_probability(profile: PlayerProfile) -> tuple[str | None, float]:
    # Kourend & Kebos diary blessing tiers use a 2/4/6/8% extra-fish chance.
    # Keep public modifier IDs stable while accepting canonical item names.
    tiers = (
        ("radas_blessing_4", "Rada's blessing 4", 0.08),
        ("radas_blessing_3", "Rada's blessing 3", 0.06),
        ("radas_blessing_2", "Rada's blessing 2", 0.04),
        ("radas_blessing_1", "Rada's blessing 1", 0.02),
    )
    for modifier_id, equipment_name, chance in tiers:
        if profile.owns(equipment_name) or profile.owns(modifier_id):
            return modifier_id, chance
    return None, 0.0


def materialise_fishing(model: FishingModel, profile: PlayerProfile, *, pacing: str = "realistic") -> GatheringResult:
    reasons: list[str] = []
    if profile.skills.fishing < model.minimum_level:
        reasons.append(f"Requires {model.minimum_level} Fishing")
    met, missing = evaluate_requirements(model.requirements, profile)
    if not met:
        reasons.extend(missing)
    if model.tool_options and not any(profile.owns(tool) for tool in model.tool_options):
        reasons.append("Requires one supported fishing tool")
    if reasons:
        return GatheringResult(False, sorted(set(reasons)), 0.0, {}, {}, None, None, None, [], pacing)

    actions = model.base_catches_per_hour * _pacing_multiplier(model.pacing_profiles, pacing)
    route = select_fastest_route(list(model.banking_routes), profile) if model.banking_routes else None
    capacity: int | None = route.effective_capacity if route else None
    applied: list[str] = []

    if model.supports_fish_barrel and profile.owns("fish_barrel"):
        applied.append("fish_barrel")
        capacity = (capacity or 28) + 28

    # Keep the unmodified catch count separate. Rada and Spirit flakes are
    # independent expected extra-output rolls. Flake consumption is based on
    # successful flake procs, not on fish added by Rada's blessing.
    base_outputs = {entry.item_name: actions * entry.expected_quantity() for entry in model.catches}
    outputs = dict(base_outputs)
    inputs: dict[str, float] = {}

    if model.supports_radas_blessing:
        blessing_id, chance = _rada_extra_probability(profile)
        if blessing_id and chance > 0:
            applied.append(blessing_id)
            for item_name, quantity in base_outputs.items():
                outputs[item_name] += quantity * chance

    if model.supports_spirit_flakes and profile.owns("spirit_flakes"):
        chance = float((model.source or {}).get("spiritFlakeProcChance", 0.50))
        applied.append("spirit_flakes")
        for item_name, quantity in base_outputs.items():
            outputs[item_name] += quantity * chance
        inputs["Spirit flakes"] = sum(base_outputs.values()) * chance

    banks_per_hour = None
    if capacity:
        total_outputs = sum(outputs.values())
        banks_per_hour = total_outputs / capacity
        if route and route.bank_seconds > 0:
            bank_overhead = banks_per_hour * route.bank_seconds
            available_seconds = max(0.0, 3600.0 - bank_overhead)
            base_actions = model.base_catches_per_hour * _pacing_multiplier(model.pacing_profiles, pacing)
            actions *= available_seconds / 3600.0
            scale = actions / base_actions if base_actions > 0 else 1.0
            outputs = {name: qty * scale for name, qty in outputs.items()}
            inputs = {name: qty * scale for name, qty in inputs.items()}
            banks_per_hour = sum(outputs.values()) / capacity

    return GatheringResult(
        available=True,
        reasons=[],
        actions_per_hour=actions,
        outputs_per_hour=outputs,
        inputs_per_hour=inputs,
        selected_route_id=route.id if route else None,
        banks_per_hour=banks_per_hour,
        capacity=capacity,
        applied_modifiers=applied,
        pacing=pacing,
        metadata={"source": model.source, "spotId": model.spot_id},
    )


def materialise_gathering(model: GatheringModel, profile: PlayerProfile) -> GatheringResult:
    reasons: list[str] = []
    skill_name = stable_id(model.activity_type)
    level = int(getattr(profile.skills, skill_name, 1))
    if level < model.minimum_level:
        reasons.append(f"Requires {model.minimum_level} {model.activity_type.title()}")
    met, missing = evaluate_requirements(model.requirements, profile)
    if not met:
        reasons.extend(missing)
    if reasons:
        return GatheringResult(False, sorted(set(reasons)), 0.0, {}, {}, None, None, None, [], "default")

    route = select_fastest_route(list(model.banking_routes), profile) if model.banking_routes else None
    capacity = route.effective_capacity if route else None
    actions = model.base_actions_per_hour
    outputs = {entry.item_name: actions * entry.expected_quantity() for entry in model.output_distribution}
    banks = sum(outputs.values()) / capacity if capacity else None
    return GatheringResult(
        True,
        [],
        actions,
        outputs,
        {},
        route.id if route else None,
        banks,
        capacity,
        [],
        "default",
        {"source": model.source, "activityType": model.activity_type},
    )
