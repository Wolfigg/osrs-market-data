from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from .api import ApiSettings
from .catalog import generated_method_catalog
from .catalog_expansion import expanded_method_catalog
from .catalog_wave4 import wave4_method_catalog
from .catalog_wave5 import wave5_method_catalog
from .catalog_wave6 import wave6_method_catalog

_SKILL_KEYS = {"attack", "strength", "defence", "ranged", "prayer", "magic", "runecraft", "construction", "hitpoints", "agility", "herblore", "thieving", "crafting", "fletching", "slayer", "hunter", "mining", "smithing", "fishing", "cooking", "firemaking", "woodcutting", "farming", "sailing"}


def _infer_method_types(method: dict[str, Any]) -> list[str]:
    explicit = method.get("method_types")
    if isinstance(explicit, list) and explicit:
        return sorted({str(x) for x in explicit})
    category = str(method.get("category") or "").lower()
    prefix = category.split("/", 1)[0]
    types: set[str] = set()
    if prefix == "gathering": types.add("gathering")
    elif prefix in {"bankstanding", "processing"}: types.add("bankstanding")
    elif prefix == "strict_afk": types.update(("bankstanding", "make-x"))
    text = f"{method.get('name', '')} {(method.get('afk') or {}).get('description', '')}".lower()
    if "autocast" in text or "auto-cast" in text: types.add("autocast")
    if method.get("variants"): types.add("variants")
    if method.get("modifiers"): types.add("modifiers")
    if any(entry.get(key) is not None for side in ("inputs", "outputs") for entry in method.get(side, []) for key in ("quantity_expected", "quantity_minimum", "quantity_maximum", "probability")): types.add("probabilistic")
    return sorted(types)


def _set_generated_audit(methods: dict[str, Any]) -> None:
    for method in methods.values():
        method["audit"] = {"status": "verified", "verified_at": "2026-08-29", "source": method.get("reference"), "notes": "Verified in the 2026-08-29 catalogue family audit."}


def _apply_known_catalog_corrections(methods: dict[str, Any]) -> None:
    f2p_gems = ("sapphire", "emerald", "ruby", "diamond")
    for type_key in ("ring", "necklace", "amulet_u"):
        gold = methods.get(f"craft_gold_{type_key}")
        if gold:
            gold.setdefault("requirements", {})["members"] = False
            gold["theoretical_cycles_per_hour"] = 1600
        for gem in f2p_gems:
            if method := methods.get(f"craft_{gem}_{type_key}"): method.setdefault("requirements", {})["members"] = False
        if method := methods.get(f"craft_dragonstone_{type_key}"): method.setdefault("requirements", {})["members"] = True
    if method := methods.get("craft_gold_bracelet"):
        method.setdefault("requirements", {})["members"] = True
        method["theoretical_cycles_per_hour"] = 1600
    for type_key in ("ring", "necklace", "bracelet", "amulet_u"):
        for gem in (*f2p_gems, "dragonstone"):
            if method := methods.get(f"craft_{gem}_{type_key}"): method["theoretical_cycles_per_hour"] = 1400
    if (method := methods.get("onyx_bolt_tips")) and method.get("outputs"): method["outputs"][0]["quantity"] = 24
    for wood in ("maple", "yew", "magic"):
        if method := methods.get(f"fletch_{wood}_longbow_u"):
            method["theoretical_cycles_per_hour"] = 1800
            method.setdefault("afk", {})["interval_seconds"] = 48.6
        if method := methods.get(f"string_{wood}_longbows"): method.setdefault("afk", {})["interval_seconds"] = 16.8
    for food in ("karambwan", "sharks", "monkfish", "anglerfish", "dark_crabs"):
        if method := methods.get(f"cook_{food}"):
            method["theoretical_cycles_per_hour"] = 1500
            method.setdefault("afk", {})["interval_seconds"] = 67.2
    if method := methods.get("blow_unpowered_orbs"):
        method["theoretical_cycles_per_hour"] = 1750
        method.setdefault("afk", {})["interval_seconds"] = 48.6
    for element in ("water", "earth", "fire", "air"):
        if method := methods.get(f"craft_{element}_battlestaves"): method["theoretical_cycles_per_hour"] = 2625
    if method := methods.get("cut_magic_logs"): method.setdefault("requirements", {})["equipment"] = ["Dragon or crystal axe"]
    if method := methods.get("cut_redwood_logs"): method.setdefault("requirements", {})["equipment"] = ["Dragon axe"]
    if method := methods.get("cut_camphor_logs"):
        req = method.setdefault("requirements", {}); req.update({"sailing": 45, "quests": ["Troubled Tortugans (partial)"], "equipment": ["Dragon axe", "Log basket"]})
    if method := methods.get("catch_dark_crabs"): method.setdefault("requirements", {})["equipment"] = ["Lobster pot"]
    if method := methods.get("cook_karambwan"): method.setdefault("requirements", {})["quests"] = ["Tai Bwo Wannai Trio"]


def _normalise_requirement_metadata(method: dict[str, Any]) -> None:
    requirements = method.get("requirements") or {}
    if not isinstance(requirements, dict): return
    metadata = dict(method.get("requirement_metadata") or {})
    for key in list(requirements):
        value = requirements[key]
        if not isinstance(value, bool) and isinstance(value, (int, float)) and str(key).lower() not in _SKILL_KEYS:
            metadata[key] = requirements.pop(key)
    if metadata: method["requirement_metadata"] = metadata


def _validate_entry(method_id: str, side: str, entry: dict[str, Any], errors: list[str]) -> None:
    if float(entry.get("quantity", 0) or 0) <= 0: errors.append(f"{method_id}: {side} quantity must be > 0")
    if entry.get("item_id") is None and not str(entry.get("item_name") or "").strip(): errors.append(f"{method_id}: {side} requires item_id or item_name")
    if entry.get("item_id") is not None and int(entry["item_id"]) <= 0: errors.append(f"{method_id}: {side} item_id must be > 0")
    for key in ("quantity_expected", "quantity_minimum", "quantity_maximum"):
        if entry.get(key) is not None and float(entry[key]) < 0: errors.append(f"{method_id}: {side} {key} must be >= 0")
    if entry.get("probability") is not None and not 0 <= float(entry["probability"]) <= 1: errors.append(f"{method_id}: {side} probability must be between 0 and 1")


def _validate_method_catalog(methods: dict[str, Any]) -> None:
    errors: list[str] = []
    for method_id, method in methods.items():
        if method.get("enabled", True) is False: continue
        _normalise_requirement_metadata(method)
        cph = float(method.get("cycles_per_hour", 0) or 0)
        theoretical = method.get("theoretical_cycles_per_hour")
        interval = (method.get("afk") or {}).get("interval_seconds")
        if cph <= 0: errors.append(f"{method_id}: cycles_per_hour must be > 0")
        if theoretical is not None and float(theoretical) + 1e-9 < cph: errors.append(f"{method_id}: theoretical_cycles_per_hour is below cycles_per_hour")
        if interval is None or float(interval) <= 0: errors.append(f"{method_id}: afk.interval_seconds must be > 0")
        if not method.get("outputs"): errors.append(f"{method_id}: at least one output is required")
        for side in ("inputs", "outputs"):
            for entry in method.get(side, []): _validate_entry(method_id, side, entry, errors)
        for key in ("process_seconds", "bank_seconds", "travel_seconds"):
            value = (method.get("workflow") or {}).get(key)
            if value is not None and float(value) < 0: errors.append(f"{method_id}: workflow.{key} must be >= 0")
        variant_ids: set[str] = set()
        for variant in method.get("variants") or []:
            variant_id = str(variant.get("id") or "")
            if not variant_id: errors.append(f"{method_id}: variant id is required")
            elif variant_id in variant_ids: errors.append(f"{method_id}: duplicate variant id {variant_id}")
            variant_ids.add(variant_id)
        modifier_ids: set[str] = set()
        for modifier in method.get("modifiers") or []:
            modifier_id = str(modifier.get("id") or "")
            if not modifier_id: errors.append(f"{method_id}: modifier id is required")
            elif modifier_id in modifier_ids: errors.append(f"{method_id}: duplicate modifier id {modifier_id}")
            modifier_ids.add(modifier_id)
            for added in modifier.get("added_items") or []:
                _validate_entry(method_id, str(added.get("side") or "modifier item"), added, errors)
        reference = str(method.get("reference") or "")
        if not reference.startswith("https://oldschool.runescape.wiki/"): errors.append(f"{method_id}: reference must point to the OSRS Wiki")
        method["method_types"] = _infer_method_types(method)
        if not method["method_types"]: errors.append(f"{method_id}: method_types could not be determined")
        audit = method.get("audit") or {}
        if audit.get("status") != "verified": errors.append(f"{method_id}: mechanical audit must be verified")
        if not str(audit.get("source") or "").startswith("https://oldschool.runescape.wiki/"): errors.append(f"{method_id}: audit source must point to the OSRS Wiki")
    if errors: raise ValueError("invalid method catalog: " + "; ".join(errors))


def load_yaml(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if source.name == "methods.yaml":
        generated = generated_method_catalog()
        generated.update(expanded_method_catalog())
        generated.update(wave4_method_catalog())
        generated.update(wave5_method_catalog())
        generated.update(wave6_method_catalog())
        _apply_known_catalog_corrections(generated)
        _set_generated_audit(generated)
        generated.update(payload.get("methods", {}) or {})
        audit_path = source.with_name("method_audit.yaml")
        audit_payload = (yaml.safe_load(audit_path.read_text(encoding="utf-8")) or {}) if audit_path.exists() else {}
        for method_id, audit in (audit_payload.get("methods", {}) or {}).items():
            if method_id not in generated: raise ValueError(f"method audit references unknown method: {method_id}")
            if isinstance(audit, dict):
                if audit.get("method_types"): generated[method_id]["method_types"] = list(audit["method_types"])
                generated[method_id]["audit"] = {"status": audit.get("status"), "verified_at": audit.get("verified_at"), "source": audit.get("source"), "notes": audit.get("notes")}
        _validate_method_catalog(generated)
        payload["methods"] = generated
    return payload


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def api_settings(settings: dict[str, Any]) -> ApiSettings:
    raw = settings["api"]
    user_agent = os.environ.get("OSRS_MARKET_USER_AGENT") or str(raw["user_agent"])
    if "set OSRS_MARKET_USER_AGENT" in user_agent: raise ValueError("set OSRS_MARKET_USER_AGENT to a descriptive contact/repository User-Agent before collecting")
    return ApiSettings(base_url=str(raw["base_url"]), user_agent=user_agent, request_spacing_ms=int(raw.get("request_spacing_ms", 250)), timeout_seconds=int(raw.get("timeout_seconds", 20)), retries=int(raw.get("retries", 4)))
