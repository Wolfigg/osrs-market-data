from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


SKILL_NAMES = (
    "attack", "strength", "defence", "ranged", "prayer", "magic", "runecraft",
    "construction", "hitpoints", "agility", "herblore", "thieving", "crafting",
    "fletching", "slayer", "hunter", "mining", "smithing", "fishing", "cooking",
    "firemaking", "woodcutting", "farming", "sailing",
)


def stable_id(value: str) -> str:
    return "_".join(
        part for part in "".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split() if part
    )


@dataclass(slots=True)
class SkillProfile:
    attack: int = 1
    strength: int = 1
    defence: int = 1
    ranged: int = 1
    prayer: int = 1
    magic: int = 1
    runecraft: int = 1
    construction: int = 1
    hitpoints: int = 10
    agility: int = 1
    herblore: int = 1
    thieving: int = 1
    crafting: int = 1
    fletching: int = 1
    slayer: int = 1
    hunter: int = 1
    mining: int = 1
    smithing: int = 1
    fishing: int = 1
    cooking: int = 1
    firemaking: int = 1
    woodcutting: int = 1
    farming: int = 1
    sailing: int = 1

    def __post_init__(self) -> None:
        for name in SKILL_NAMES:
            value = getattr(self, name)
            if isinstance(value, bool):
                value = 1
            setattr(self, name, max(1, min(99, int(value))))


@dataclass(slots=True)
class PlayerProfile:
    members: bool = True
    skills: SkillProfile = field(default_factory=SkillProfile)
    equipment: set[str] = field(default_factory=set)
    unlocks: set[str] = field(default_factory=set)
    quests: set[str] = field(default_factory=set)
    diaries: set[str] = field(default_factory=set)
    poh_features: set[str] = field(default_factory=set)
    method_settings: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("equipment", "unlocks", "quests", "diaries", "poh_features"):
            setattr(self, field_name, {stable_id(value) for value in getattr(self, field_name)})

    def owns(self, value: str, *, collection: str = "equipment") -> bool:
        return stable_id(value) in getattr(self, collection)

    def to_dict(self) -> dict[str, Any]:
        return {
            "members": self.members,
            "skills": asdict(self.skills),
            "equipment": sorted(self.equipment),
            "unlocks": sorted(self.unlocks),
            "quests": sorted(self.quests),
            "diaries": sorted(self.diaries),
            "pohFeatures": sorted(self.poh_features),
            "methodSettings": self.method_settings,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "PlayerProfile":
        source = dict(raw or {})
        skills_raw = source.get("skills") or {}
        skill_values = {
            name: skills_raw.get(name, 10 if name == "hitpoints" else 1)
            for name in SKILL_NAMES
        }
        return cls(
            members=bool(source.get("members", True)),
            skills=SkillProfile(**skill_values),
            equipment=set(source.get("equipment") or source.get("ownedEquipment") or []),
            unlocks=set(source.get("unlocks") or []),
            quests=set(source.get("quests") or []),
            diaries=set(source.get("diaries") or []),
            poh_features=set(source.get("pohFeatures") or source.get("poh_features") or []),
            method_settings=dict(source.get("methodSettings") or source.get("method_settings") or {}),
        )


@dataclass(frozen=True, slots=True)
class RequirementResult:
    met: bool
    reason: str | None = None


class Requirement(Protocol):
    def evaluate(self, profile: PlayerProfile) -> RequirementResult: ...


@dataclass(frozen=True, slots=True)
class SkillRequirement:
    skill: str
    level: int

    def evaluate(self, profile: PlayerProfile) -> RequirementResult:
        actual = int(getattr(profile.skills, self.skill, 1))
        required = int(self.level)
        return RequirementResult(actual >= required, None if actual >= required else f"Requires {required} {self.skill.title()}")


@dataclass(frozen=True, slots=True)
class MembershipRequirement:
    required: bool = True

    def evaluate(self, profile: PlayerProfile) -> RequirementResult:
        met = not self.required or profile.members
        return RequirementResult(met, None if met else "Requires membership")


@dataclass(frozen=True, slots=True)
class NamedRequirement:
    value: str
    collection: str
    label: str

    def evaluate(self, profile: PlayerProfile) -> RequirementResult:
        met = stable_id(self.value) in getattr(profile, self.collection)
        return RequirementResult(met, None if met else f"Requires {self.label} {self.value}")


class EquipmentRequirement(NamedRequirement):
    def __init__(self, value: str):
        super().__init__(value, "equipment", "equipment")


class QuestRequirement(NamedRequirement):
    def __init__(self, value: str):
        super().__init__(value, "quests", "quest")


class DiaryRequirement(NamedRequirement):
    def __init__(self, value: str):
        super().__init__(value, "diaries", "diary")


class UnlockRequirement(NamedRequirement):
    def __init__(self, value: str):
        super().__init__(value, "unlocks", "unlock")


class PohFeatureRequirement(NamedRequirement):
    def __init__(self, value: str):
        super().__init__(value, "poh_features", "POH feature")


@dataclass(frozen=True, slots=True)
class AllRequirements:
    requirements: tuple[Requirement, ...]

    def evaluate(self, profile: PlayerProfile) -> RequirementResult:
        reasons = [result.reason for requirement in self.requirements if not (result := requirement.evaluate(profile)).met]
        return RequirementResult(not reasons, "; ".join(reason for reason in reasons if reason) or None)


@dataclass(frozen=True, slots=True)
class AnyRequirement:
    requirements: tuple[Requirement, ...]

    def evaluate(self, profile: PlayerProfile) -> RequirementResult:
        results = [requirement.evaluate(profile) for requirement in self.requirements]
        if any(result.met for result in results):
            return RequirementResult(True)
        return RequirementResult(False, " or ".join(result.reason for result in results if result.reason) or "No alternative requirement met")


def requirements_from_catalogue(raw: dict[str, Any] | None) -> list[Requirement]:
    source = dict(raw or {})
    result: list[Requirement] = []
    if source.get("members"):
        result.append(MembershipRequirement())
    skills = dict(source.get("skills") or {})
    for key, value in source.items():
        lowered = str(key).lower()
        if lowered in SKILL_NAMES and isinstance(value, (int, float)) and not isinstance(value, bool):
            skills[lowered] = int(value)
    result.extend(SkillRequirement(skill, int(level)) for skill, level in skills.items())
    result.extend(EquipmentRequirement(value) for value in source.get("equipment") or [])
    result.extend(QuestRequirement(value) for value in source.get("quests") or [])
    result.extend(DiaryRequirement(value) for value in source.get("diaries") or [])
    result.extend(UnlockRequirement(value) for value in source.get("unlocks") or [])
    result.extend(PohFeatureRequirement(value) for value in source.get("poh_features") or source.get("pohFeatures") or [])
    return result


def evaluate_requirements(raw: dict[str, Any] | None, profile: PlayerProfile) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for requirement in requirements_from_catalogue(raw):
        evaluated = requirement.evaluate(profile)
        if not evaluated.met and evaluated.reason:
            reasons.append(evaluated.reason)
    return not reasons, reasons
