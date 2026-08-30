from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .method_model import effective_cycles_per_hour, iter_method_variants
from .player_profile import PlayerProfile, evaluate_requirements, stable_id


@dataclass(slots=True)
class MaterialisedMethod:
    method_id: str
    available: bool
    unavailable_reasons: list[str] = field(default_factory=list)
    selected_variant_id: str | None = None
    applied_modifier_ids: list[str] = field(default_factory=list)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    cycles_per_hour: float = 0.0
    units_per_hour: float = 0.0
    model_metadata: dict[str, Any] = field(default_factory=dict)
    method: dict[str, Any] = field(default_factory=dict, repr=False)


def _variant_id(method: dict[str, Any]) -> str | None:
    variant = method.get("variant") or {}
    return str(variant.get("id")) if variant.get("id") else None


def available_variants(method_id: str, method: dict[str, Any], profile: PlayerProfile) -> list[tuple[str, dict[str, Any]]]:
    available: list[tuple[str, dict[str, Any]]] = []
    for variant_method_id, variant in iter_method_variants(method_id, method):
        met, _ = evaluate_requirements(variant.get("requirements"), profile)
        if met:
            available.append((variant_method_id, variant))
    return available


def _variant_specificity(method: dict[str, Any]) -> int:
    requirements = method.get("requirements") or {}
    return (
        len(requirements.get("equipment") or [])
        + len(requirements.get("unlocks") or [])
        + len(requirements.get("poh_features") or requirements.get("pohFeatures") or [])
        + len(requirements.get("quests") or [])
    )


def select_best_variant(method_id: str, method: dict[str, Any], profile: PlayerProfile) -> tuple[str, dict[str, Any]] | None:
    variants = available_variants(method_id, method, profile)
    if not variants:
        return None
    # Route variants primarily compete on sustainable throughput. For equal-rate
    # equipment variants prefer the most specific setup the player actually owns,
    # which selects e.g. chemistry+goggles over either single-equipment variant.
    return max(variants, key=lambda row: (effective_cycles_per_hour(row[1]), _variant_specificity(row[1]), row[0]))


def _apply_profile_settings(method: dict[str, Any], profile: PlayerProfile) -> dict[str, Any]:
    result = deepcopy(method)
    cooking = ((result.get("model") or {}).get("cooking") or {})
    if cooking:
        defaults = cooking.setdefault("defaults", {})
        defaults["level"] = profile.skills.cooking
        defaults["gauntlets"] = profile.owns("cooking_gauntlets") or profile.owns("cooking gauntlets")
        defaults["cookingCape"] = profile.skills.cooking >= 99 and (profile.owns("cooking_cape") or profile.owns("cooking cape"))
        cooking_settings = profile.method_settings.get("cooking") or {}
        if cooking_settings.get("location"):
            defaults["location"] = str(cooking_settings["location"])
    return result


def materialise_method_for_player(method_id: str, method: dict[str, Any], profile: PlayerProfile | dict[str, Any] | None) -> MaterialisedMethod:
    if profile is None:
        generic = _apply_profile_settings(method, PlayerProfile()) if False else deepcopy(method)
        return MaterialisedMethod(
            method_id=method_id,
            available=bool(generic.get("enabled", True)),
            inputs=deepcopy(generic.get("inputs") or []),
            outputs=deepcopy(generic.get("outputs") or []),
            cycles_per_hour=effective_cycles_per_hour(generic),
            units_per_hour=effective_cycles_per_hour(generic),
            model_metadata=deepcopy(generic.get("model") or {}),
            method=generic,
        )

    account = profile if isinstance(profile, PlayerProfile) else PlayerProfile.from_dict(profile)
    base_met, base_reasons = evaluate_requirements(method.get("requirements"), account)
    if not base_met and not method.get("variants"):
        personalised = _apply_profile_settings(method, account)
        return MaterialisedMethod(method_id=method_id, available=False, unavailable_reasons=base_reasons, method=personalised)

    selected = select_best_variant(method_id, method, account) if method.get("variants") else (method_id, deepcopy(method))
    if selected is None:
        reasons: list[str] = []
        for _, variant in iter_method_variants(method_id, method):
            _, missing = evaluate_requirements(variant.get("requirements"), account)
            reasons.extend(missing)
        return MaterialisedMethod(method_id=method_id, available=False, unavailable_reasons=sorted(set(reasons)), method=deepcopy(method))

    selected_method_id, selected_method = selected
    selected_method = _apply_profile_settings(selected_method, account)
    met, reasons = evaluate_requirements(selected_method.get("requirements"), account)
    variant_id = _variant_id(selected_method)
    equipment = (selected_method.get("requirements") or {}).get("equipment") or []
    modifier_ids = [stable_id(value) for value in equipment if stable_id(value) in account.equipment]
    cycles = effective_cycles_per_hour(selected_method)
    selected_method.setdefault("personalisation", {}).update({
        "available": met,
        "selectedVariantId": variant_id,
        "appliedModifierIds": modifier_ids,
        "unavailableReasons": reasons,
    })
    return MaterialisedMethod(
        method_id=selected_method_id,
        available=met,
        unavailable_reasons=reasons,
        selected_variant_id=variant_id,
        applied_modifier_ids=modifier_ids,
        inputs=deepcopy(selected_method.get("inputs") or []),
        outputs=deepcopy(selected_method.get("outputs") or []),
        cycles_per_hour=cycles,
        units_per_hour=cycles,
        model_metadata=deepcopy(selected_method.get("model") or {}),
        method=selected_method,
    )
