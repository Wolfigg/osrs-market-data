from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from .api import ApiSettings
from .catalog import generated_method_catalog

_SKILL_KEYS = {
    "attack", "strength", "defence", "ranged", "prayer", "magic", "runecraft",
    "construction", "hitpoints", "agility", "herblore", "thieving", "crafting",
    "fletching", "slayer", "hunter", "mining", "smithing", "fishing", "cooking",
    "firemaking", "woodcutting", "farming",
}


def _infer_method_types(method: dict[str, Any]) -> list[str]:
    explicit = method.get("method_types")
    if isinstance(explicit, list) and explicit:
        return sorted({str(value) for value in explicit})

    category = str(method.get("category") or "").lower()
    prefix = category.split("/", 1)[0]
    types: set[str] = set()
    if prefix == "gathering":
        types.add("gathering")
    elif prefix == "bankstanding":
        types.add("bankstanding")
    elif prefix == "strict_afk":
        types.update(("bankstanding", "make-x"))

    name = str(method.get("name") or "").lower()
    description = str((method.get("afk") or {}).get("description") or "").lower()
    if "autocast" in name or "auto-cast" in description:
        types.add("autocast")
    return sorted(types)


def _apply_known_catalog_corrections(methods: dict[str, Any]) -> None:
    """Apply source-verified corrections to generated catalogue defaults.

    Hand-maintained methods.yaml overrides are applied after this function, so
    explicit config remains authoritative when a method needs custom modelling.
    """
    # F2P supports gold plus sapphire-through-diamond rings, necklaces and
    # unstrung amulets. Bracelets and dragonstone jewellery are members-only.
    f2p_gems = ("sapphire", "emerald", "ruby", "diamond")
    for type_key in ("ring", "necklace", "amulet_u"):
        gold = methods.get(f"craft_gold_{type_key}")
        if gold:
            gold.setdefault("requirements", {})["members"] = False
            # Current Crafting guidance models metal-only jewellery at 1,600/h.
            # Keep the configured 1,400/h realistic rate conservative, but use
            # the sourced 1,600/h value as the theoretical ceiling.
            gold["theoretical_cycles_per_hour"] = 1600
        for gem in f2p_gems:
            method = methods.get(f"craft_{gem}_{type_key}")
            if method:
                method.setdefault("requirements", {})["members"] = False
        dragonstone = methods.get(f"craft_dragonstone_{type_key}")
        if dragonstone:
            dragonstone.setdefault("requirements", {})["members"] = True

    gold_bracelet = methods.get("craft_gold_bracelet")
    if gold_bracelet:
        gold_bracelet.setdefault("requirements", {})["members"] = True
        gold_bracelet["theoretical_cycles_per_hour"] = 1600
    for gem in (*f2p_gems, "dragonstone"):
        method = methods.get(f"craft_{gem}_bracelet")
        if method:
            method.setdefault("requirements", {})["members"] = True

    # Current Crafting guidance uses 1,400/h for gem + metal jewellery. The
    # generated methods already use 1,400/h mechanically, so do not advertise
    # an unsupported 1,450/h theoretical rate.
    for type_key in ("ring", "necklace", "bracelet", "amulet_u"):
        for gem in (*f2p_gems, "dragonstone"):
            method = methods.get(f"craft_{gem}_{type_key}")
            if method:
                method["theoretical_cycles_per_hour"] = 1400

    # An onyx is the exception among the standard precious-gem bolt tips: it
    # produces 24 tips per gem, not 12.
    onyx_tips = methods.get("onyx_bolt_tips")
    if onyx_tips and onyx_tips.get("outputs"):
        onyx_tips["outputs"][0]["quantity"] = 24

    # Current Crafting training guidance uses 2,450 battlestaves/hour and states
    # that perfect banking can reach 2,625/hour.
    for element in ("water", "earth", "fire", "air"):
        method = methods.get(f"craft_{element}_battlestaves")
        if method:
            method["theoretical_cycles_per_hour"] = 2625

    # Keep displayed requirements aligned with the gear assumptions behind the
    # sourced gathering rates. Secondary-drop boosting gear is omitted when the
    # corresponding secondary value is intentionally excluded from profit.
    magic_logs = methods.get("cut_magic_logs")
    if magic_logs:
        magic_logs.setdefault("requirements", {})["equipment"] = ["Dragon or crystal axe"]
    redwood_logs = methods.get("cut_redwood_logs")
    if redwood_logs:
        redwood_logs.setdefault("requirements", {})["equipment"] = ["Dragon axe"]
    camphor_logs = methods.get("cut_camphor_logs")
    if camphor_logs:
        camphor_logs.setdefault("requirements", {})["equipment"] = ["Dragon axe", "Log basket"]
    dark_crabs = methods.get("catch_dark_crabs")
    if dark_crabs:
        dark_crabs.setdefault("requirements", {})["equipment"] = ["Lobster pot"]


def _normalise_requirement_metadata(method: dict[str, Any]) -> None:
    requirements = method.get("requirements") or {}
    if not isinstance(requirements, dict):
        return
    metadata = dict(method.get("requirement_metadata") or {})
    for key in list(requirements):
        value = requirements[key]
        lowered = str(key).lower()
        # bool is a subclass of int in Python. Preserve flags such as
        # `members: false` instead of misclassifying them as numeric metadata.
        if not isinstance(value, bool) and isinstance(value, (int, float)) and lowered not in _SKILL_KEYS:
            metadata[key] = requirements.pop(key)
    if metadata:
        method["requirement_metadata"] = metadata


def _validate_method_catalog(methods: dict[str, Any]) -> None:
    errors: list[str] = []
    for method_id, method in methods.items():
        if method.get("enabled", True) is False:
            continue
        _normalise_requirement_metadata(method)
        cph = float(method.get("cycles_per_hour", 0) or 0)
        theoretical = method.get("theoretical_cycles_per_hour")
        interval = (method.get("afk") or {}).get("interval_seconds")
        reference = str(method.get("reference") or "")
        outputs = method.get("outputs") or []
        if cph <= 0:
            errors.append(f"{method_id}: cycles_per_hour must be > 0")
        if theoretical is not None and float(theoretical) + 1e-9 < cph:
            errors.append(f"{method_id}: theoretical_cycles_per_hour is below cycles_per_hour")
        if interval is None or float(interval) <= 0:
            errors.append(f"{method_id}: afk.interval_seconds must be > 0")
        if not outputs:
            errors.append(f"{method_id}: at least one output is required")
        for side in ("inputs", "outputs"):
            for entry in method.get(side, []):
                if float(entry.get("quantity", 0) or 0) <= 0:
                    errors.append(f"{method_id}: {side} quantity must be > 0")
                if int(entry.get("item_id", 0) or 0) <= 0:
                    errors.append(f"{method_id}: {side} item_id must be > 0")
        if not reference.startswith("https://oldschool.runescape.wiki/"):
            errors.append(f"{method_id}: reference must point to the OSRS Wiki")
        method_types = _infer_method_types(method)
        if not method_types:
            errors.append(f"{method_id}: method_types could not be determined")
        method["method_types"] = method_types
    if errors:
        raise ValueError("invalid method catalog: " + "; ".join(errors))


def load_yaml(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if source.name == "methods.yaml":
        generated = generated_method_catalog()
        _apply_known_catalog_corrections(generated)
        configured = payload.get("methods", {}) or {}
        generated.update(configured)

        audit_path = source.with_name("method_audit.yaml")
        audit_payload = (yaml.safe_load(audit_path.read_text(encoding="utf-8")) or {}) if audit_path.exists() else {}
        audits = audit_payload.get("methods", {}) or {}
        for method_id, audit in audits.items():
            if method_id not in generated:
                raise ValueError(f"method audit references unknown method: {method_id}")
            if isinstance(audit, dict):
                if audit.get("method_types"):
                    generated[method_id]["method_types"] = list(audit["method_types"])
                generated[method_id]["audit"] = {
                    "status": audit.get("status"),
                    "verified_at": audit.get("verified_at"),
                    "source": audit.get("source"),
                    "notes": audit.get("notes"),
                }

        _validate_method_catalog(generated)
        payload["methods"] = generated
    return payload


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def api_settings(settings: dict[str, Any]) -> ApiSettings:
    raw = settings["api"]
    user_agent = os.environ.get("OSRS_MARKET_USER_AGENT") or str(raw["user_agent"])
    if "set OSRS_MARKET_USER_AGENT" in user_agent:
        raise ValueError("set OSRS_MARKET_USER_AGENT to a descriptive contact/repository User-Agent before collecting")
    return ApiSettings(
        base_url=str(raw["base_url"]),
        user_agent=user_agent,
        request_spacing_ms=int(raw.get("request_spacing_ms", 250)),
        timeout_seconds=int(raw.get("timeout_seconds", 20)),
        retries=int(raw.get("retries", 4)),
    )
