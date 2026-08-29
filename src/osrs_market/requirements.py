from __future__ import annotations

from typing import Any

SKILL_KEYS = {
    "attack", "strength", "defence", "ranged", "prayer", "magic", "runecraft",
    "construction", "hitpoints", "agility", "herblore", "thieving", "crafting",
    "fletching", "slayer", "hunter", "mining", "smithing", "fishing", "cooking",
    "firemaking", "woodcutting", "farming", "sailing",
}


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [str(value)]


def normalise_requirements(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Convert legacy catalogue requirements to the Wave 6 structured schema.

    This is intentionally backwards compatible. Existing catalogue rows can keep
    using top-level skill keys while new rows may use an explicit ``skills`` map.
    """
    source = dict(raw or {})
    skills = {
        str(key).lower(): int(value)
        for key, value in (source.get("skills") or {}).items()
        if str(key).lower() in SKILL_KEYS and isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    for key, value in source.items():
        lowered = str(key).lower()
        if lowered in SKILL_KEYS and isinstance(value, (int, float)) and not isinstance(value, bool):
            skills[lowered] = int(value)

    diaries = source.get("diaries") or {}
    if isinstance(diaries, list):
        diaries = {str(name): True for name in diaries}
    elif not isinstance(diaries, dict):
        diaries = {str(diaries): True} if diaries else {}

    equipment = _strings(source.get("equipment"))
    items = _strings(source.get("items"))
    supplies = _strings(source.get("supplies"))
    recommended = _strings(source.get("recommended"))

    return {
        "members": bool(source.get("members", True)),
        "skills": dict(sorted(skills.items())),
        "quests": _strings(source.get("quests")),
        "items": items,
        "equipment": equipment,
        "diaries": {str(key): value for key, value in diaries.items()},
        "supplies": supplies,
        "recommended": recommended,
    }


def normalise_account_profile(raw: dict[str, Any] | None) -> dict[str, Any]:
    source = dict(raw or {})
    skills = {
        str(key).lower(): max(1, min(99, int(value)))
        for key, value in (source.get("skills") or {}).items()
        if str(key).lower() in SKILL_KEYS and isinstance(value, (int, float))
    }
    equipment = source.get("equipment", source.get("ownedEquipment"))
    items = source.get("items", source.get("ownedItems"))
    quests = source.get("quests")
    diaries = source.get("diaries")
    return {
        "members": source.get("members"),
        "skills": skills,
        "quests": None if quests is None else _strings(quests),
        "items": None if items is None else _strings(items),
        "equipment": None if equipment is None else _strings(equipment),
        "diaries": None if diaries is None else diaries,
    }


def _normalised_set(value: list[str] | None) -> set[str] | None:
    if value is None:
        return None
    return {item.strip().casefold() for item in value}


def _missing_named(required: list[str], owned: list[str] | None) -> tuple[list[str], list[str]]:
    if not required:
        return [], []
    available = _normalised_set(owned)
    if available is None:
        return [], list(required)
    missing = [item for item in required if item.strip().casefold() not in available]
    return missing, []


def _diary_satisfied(required_value: Any, profile_value: Any) -> bool:
    if required_value in (None, False, "", 0):
        return True
    if profile_value is True:
        return True
    if isinstance(required_value, (int, float)) and isinstance(profile_value, (int, float)):
        return float(profile_value) >= float(required_value)
    return str(profile_value).strip().casefold() == str(required_value).strip().casefold()


def evaluate_requirements(requirements: dict[str, Any] | None, profile: dict[str, Any] | None) -> dict[str, Any]:
    req = normalise_requirements(requirements)
    account = normalise_account_profile(profile)
    missing: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []

    if req["members"]:
        if account["members"] is False:
            missing.append({"type": "members", "required": True})
        elif account["members"] is None:
            unknown.append({"type": "members", "required": True})

    for skill, level in req["skills"].items():
        actual = account["skills"].get(skill)
        if actual is None:
            unknown.append({"type": "skill", "skill": skill, "required": level})
        elif actual < level:
            missing.append({"type": "skill", "skill": skill, "required": level, "actual": actual})

    for requirement_type, key in (("quest", "quests"), ("item", "items"), ("equipment", "equipment")):
        failed, unresolved = _missing_named(req[key], account[key])
        missing.extend({"type": requirement_type, "required": item} for item in failed)
        unknown.extend({"type": requirement_type, "required": item} for item in unresolved)

    required_diaries = req["diaries"]
    if required_diaries:
        profile_diaries = account["diaries"]
        if profile_diaries is None:
            unknown.extend({"type": "diary", "diary": name, "required": value} for name, value in required_diaries.items())
        else:
            if isinstance(profile_diaries, list):
                profile_diaries = {str(name): True for name in profile_diaries}
            if not isinstance(profile_diaries, dict):
                profile_diaries = {}
            folded = {str(key).casefold(): value for key, value in profile_diaries.items()}
            for name, required_value in required_diaries.items():
                actual = folded.get(str(name).casefold())
                if actual is None or not _diary_satisfied(required_value, actual):
                    missing.append({"type": "diary", "diary": name, "required": required_value, "actual": actual})

    status = "blocked" if missing else ("unknown" if unknown else "eligible")
    return {
        "status": status,
        "eligible": status == "eligible",
        "blocked": bool(missing),
        "requirements": req,
        "missing": missing,
        "unknown": unknown,
    }
