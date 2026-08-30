from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .player_profile import SKILL_NAMES, stable_id


@dataclass(slots=True)
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            raise ValueError("catalogue validation failed: " + "; ".join(self.errors))


def _check_probability(method_id: str, side: str, row: dict[str, Any], report: ValidationReport) -> None:
    probability = row.get("probability")
    if probability is not None and not 0 <= float(probability) <= 1:
        report.errors.append(f"{method_id}: {side} probability must be in [0,1]")
    minimum = row.get("quantity_minimum")
    expected = row.get("quantity_expected")
    maximum = row.get("quantity_maximum")
    if minimum is not None and float(minimum) < 0:
        report.errors.append(f"{method_id}: {side} minimum quantity must be >= 0")
    if expected is not None and float(expected) < 0:
        report.errors.append(f"{method_id}: {side} expected quantity must be >= 0")
    if maximum is not None and float(maximum) < 0:
        report.errors.append(f"{method_id}: {side} maximum quantity must be >= 0")
    if minimum is not None and expected is not None and float(minimum) > float(expected) + 1e-9:
        report.errors.append(f"{method_id}: {side} minimum quantity exceeds expected")
    if expected is not None and maximum is not None and float(expected) > float(maximum) + 1e-9:
        report.errors.append(f"{method_id}: {side} expected quantity exceeds maximum")


def _check_requirements(method_id: str, raw: dict[str, Any], report: ValidationReport, known_ids: dict[str, set[str]] | None) -> None:
    requirements = raw or {}
    skills = dict(requirements.get("skills") or {})
    for key, value in requirements.items():
        lowered = str(key).lower()
        if lowered in SKILL_NAMES and isinstance(value, (int, float)) and not isinstance(value, bool):
            skills[lowered] = value
    for skill, level in skills.items():
        if skill not in SKILL_NAMES:
            report.errors.append(f"{method_id}: unknown skill {skill}")
        if not 1 <= int(level) <= 99:
            report.errors.append(f"{method_id}: {skill} requirement must be 1-99")
    if not known_ids:
        return
    for field_name, known_key in (("quests", "quests"), ("equipment", "equipment"), ("unlocks", "unlocks"), ("diaries", "diaries"), ("poh_features", "poh_features")):
        known = known_ids.get(known_key)
        if not known:
            continue
        for value in requirements.get(field_name) or requirements.get("pohFeatures" if field_name == "poh_features" else field_name) or []:
            if stable_id(str(value)) not in known:
                report.errors.append(f"{method_id}: unknown {field_name} id {value}")


def validate_catalogue_v2(
    methods: dict[str, dict[str, Any]],
    *,
    known_item_ids: set[int] | None = None,
    known_ids: dict[str, set[str]] | None = None,
) -> ValidationReport:
    report = ValidationReport()
    method_ids: set[str] = set()
    for method_id, method in methods.items():
        if method_id in method_ids:
            report.errors.append(f"duplicate method id: {method_id}")
        method_ids.add(method_id)
        if method.get("enabled", True) is False:
            continue

        cycles = float(method.get("cycles_per_hour", 0) or 0)
        if cycles <= 0:
            report.errors.append(f"{method_id}: cycles/hour must be > 0")
        workflow = method.get("workflow") or {}
        for key in ("process_seconds", "bank_seconds", "travel_seconds"):
            if workflow.get(key) is not None and float(workflow[key]) < 0:
                report.errors.append(f"{method_id}: workflow {key} must be >= 0")
        if workflow.get("inventory_capacity") is not None and int(workflow["inventory_capacity"]) <= 0:
            report.errors.append(f"{method_id}: inventory capacity must be > 0")
        if workflow.get("inventory_size") is not None and int(workflow["inventory_size"]) <= 0:
            report.errors.append(f"{method_id}: inventory size must be > 0")

        _check_requirements(method_id, method.get("requirements") or {}, report, known_ids)
        variant_ids: set[str] = set()
        for variant in method.get("variants") or []:
            variant_id = str(variant.get("id") or "")
            if not variant_id:
                report.errors.append(f"{method_id}: variant id is required")
            elif variant_id in variant_ids:
                report.errors.append(f"{method_id}: duplicate variant id {variant_id}")
            variant_ids.add(variant_id)
            _check_requirements(f"{method_id}/{variant_id}", (variant.get("overrides") or {}).get("requirements") or method.get("requirements") or {}, report, known_ids)

        for side in ("inputs", "outputs"):
            rows = method.get(side) or []
            if side == "outputs" and not rows:
                report.errors.append(f"{method_id}: at least one output required")
            for row in rows:
                quantity = float(row.get("quantity", 0) or 0)
                if quantity <= 0:
                    report.errors.append(f"{method_id}: {side} quantity must be > 0")
                item_id = row.get("item_id")
                if item_id is None and not str(row.get("item_name") or "").strip():
                    report.errors.append(f"{method_id}: {side} item must resolve")
                if item_id is not None and known_item_ids is not None and int(item_id) not in known_item_ids:
                    report.errors.append(f"{method_id}: {side} item id {item_id} missing from mapping")
                _check_probability(method_id, side, row, report)

        model = method.get("model") or {}
        distribution = model.get("outputDistribution") or model.get("output_distribution")
        if distribution:
            total = sum(float(row.get("probability", 0)) for row in distribution)
            if abs(total - 1.0) > 1e-6:
                report.errors.append(f"{method_id}: output probability distribution sums to {total}, expected 1")

        cooking = model.get("cooking") or {}
        if cooking:
            if int(cooking.get("minimumLevel", 1)) not in range(1, 100):
                report.errors.append(f"{method_id}: cooking minimum level must be 1-99")
            if cooking.get("gauntletsAffected") is False and any(str(key).startswith("gauntlets_") for key in (cooking.get("curves") or {})):
                report.warnings.append(f"{method_id}: gauntlet curves present for food marked ineligible")

        source = method.get("source") or model.get("source")
        if not source:
            report.warnings.append(f"{method_id}: missing structured source provenance")

    return report
