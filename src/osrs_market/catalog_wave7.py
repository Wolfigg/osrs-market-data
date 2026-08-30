from __future__ import annotations

from copy import deepcopy
from typing import Any

from .catalog_wave5 import wave5_method_catalog
from .catalog_wave6 import wave6_method_catalog


def _paced(method: dict[str, Any], *, activity: str, realistic: float = 0.90, afk: float = 0.75) -> dict[str, Any]:
    result = deepcopy(method)
    if result.get("enabled", True) is False:
        return result
    base_rate = float(result.get("cycles_per_hour") or 0)
    if base_rate <= 0:
        return result

    base_requirements = deepcopy(result.get("requirements") or {})
    result["variants"] = [
        {
            "id": "active",
            "label": "Active",
            "description": "Source-backed baseline throughput with sustained attention.",
            "overrides": {
                "cycles_per_hour": base_rate,
                "requirements": deepcopy(base_requirements),
            },
        },
        {
            "id": "realistic",
            "label": "Realistic",
            "description": "Continuous normal play with reaction, movement and banking losses.",
            "overrides": {
                "cycles_per_hour": round(base_rate * realistic, 3),
                "requirements": deepcopy(base_requirements),
            },
        },
        {
            "id": "afk",
            "label": "AFK",
            "description": "Lower-attention pacing. This is deliberately below the active guide baseline.",
            "overrides": {
                "cycles_per_hour": round(base_rate * afk, 3),
                "requirements": deepcopy(base_requirements),
            },
        },
    ]
    result["include_base_variant"] = False
    model = result.setdefault("model", {})
    model["gatheringV2"] = {
        "activityType": activity,
        "baselineCyclesPerHour": base_rate,
        "pacingProfiles": {"active": 1.0, "realistic": realistic, "afk": afk},
        "throughputPolicy": "Guide/catalogue baseline is the active anchor. Realistic and AFK profiles are explicit scenario multipliers, not claims of universal player rates.",
        "secondaryOutputPolicy": "Only source-backed deterministic or statistically defensible outputs are valued. Unverified random secondaries remain excluded.",
    }
    types = set(result.get("method_types") or [])
    types.update(("gathering", "variants"))
    result["method_types"] = sorted(types)
    return result


def _fishing(method: dict[str, Any]) -> dict[str, Any]:
    result = _paced(method, activity="fishing", realistic=0.90, afk=0.75)
    if result.get("enabled", True) is False:
        return result
    model = result.setdefault("model", {}).setdefault("gatheringV2", {})
    requirements = result.get("requirements") or {}
    equipment = list(requirements.get("equipment") or [])
    model.update({
        "minimumLevel": requirements.get("fishing"),
        "toolOptions": equipment,
        "supportsFishBarrel": bool(requirements.get("members", True)),
        "supportsRadasBlessing": bool(requirements.get("members", True)),
        "supportsSpiritFlakes": bool(requirements.get("members", True)),
        "mixedCatch": len(result.get("outputs") or []) > 1,
        "bankingModel": "Capacity and bank frequency are setup-dependent. Fish barrel changes capacity, not catch probability.",
        "modifierPolicy": "Rada's blessing and Spirit flakes are account modifiers and must not be silently assumed in generic baseline profit.",
    })
    return result


def _woodcutting(method: dict[str, Any]) -> dict[str, Any]:
    result = _paced(method, activity="woodcutting", realistic=0.88, afk=0.70)
    if result.get("enabled", True) is False:
        return result
    model = result.setdefault("model", {}).setdefault("gatheringV2", {})
    model.update({
        "depletionModel": "Tree-specific depletion and respawn effects are represented through pacing profiles until a source-backed per-tree stochastic model is available.",
        "forestryOutputsIncluded": False,
    })
    return result


def _mining(method: dict[str, Any]) -> dict[str, Any]:
    result = _paced(method, activity="mining", realistic=0.88, afk=0.68)
    if result.get("enabled", True) is False:
        return result
    model = result.setdefault("model", {}).setdefault("gatheringV2", {})
    model.update({
        "successModel": "Catalogue baseline remains the source anchor; player-level and pickaxe-specific success functions can replace pacing multipliers without changing the public method contract.",
        "randomSecondariesIncluded": False,
    })
    return result


def wave7_method_catalog() -> dict[str, dict[str, Any]]:
    """Final Wave 7 production overrides for gathering intelligence.

    This deliberately preserves existing source-backed baseline rates while
    removing the false implication that every account sustains exactly one rate.
    """
    base = wave5_method_catalog()
    base.update(wave6_method_catalog())
    result: dict[str, dict[str, Any]] = {}

    for method_id, method in base.items():
        if method_id.startswith("gather_fishing_"):
            result[method_id] = _fishing(method)
        elif method_id.startswith("gather_") and "woodcutting" in str(method.get("category") or ""):
            result[method_id] = _woodcutting(method)
        elif method_id.startswith("gather_mining_"):
            result[method_id] = _mining(method)

    return result
