from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import yaml

from .catalog_schema import compile_gathering_pacing, compile_jewellery_enchanting, load_catalogue_document


def _item(name: str, quantity: float = 1, *, buy: bool = False, **extra: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"item_name": str(name), "quantity": float(quantity), **extra}
    if buy:
        row["buy_via_ge"] = True
    return row


def _method(
    *, name: str, category: str, inputs: list[dict[str, Any]], outputs: list[dict[str, Any]],
    cycles: float, theoretical: float, interval: float, requirements: dict[str, Any],
    notes: str, reference: str, method_types: list[str], source: dict[str, Any], **extra: Any,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "enabled": True,
        "name": name,
        "category": category,
        "inputs": inputs,
        "outputs": outputs,
        "fixed_cost_gp_per_cycle": 0,
        "cycles_per_hour": float(cycles),
        "theoretical_cycles_per_hour": float(theoretical),
        "planned_hours_per_day": 4,
        "afk": {"interval_seconds": float(interval), "intensity": "low", "description": notes},
        "requirements": deepcopy(requirements),
        "notes": notes,
        "reference": reference,
        "method_types": list(method_types),
        "source": deepcopy(source),
    }
    row.update(extra)
    return row


def compile_orb_charging(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = load_catalogue_document(path)
    if payload.get("family") != "orb_charging":
        raise ValueError("expected orb_charging family")
    defaults = payload.get("defaults") or {}
    source = dict(payload.get("source") or {})
    result: dict[str, dict[str, Any]] = {}
    inv = int(defaults.get("itemsPerInventory", 26))
    bank_inventory = float(defaults.get("bankSecondsPerInventory", 12))
    process_seconds = float(defaults.get("processSeconds", 1.8))
    for element, spec in (payload.get("elements") or {}).items():
        routes = spec.get("routes") or []
        if not routes:
            raise ValueError(f"charge_{element}_orb: at least one route is required")
        magic = int(spec["magicLevel"])
        staff = str(spec["staff"])
        base_requirements = {"members": True, "magic": magic, "equipment": [staff]}
        variants = []
        for route in routes:
            cph = float(route["cyclesPerHour"])
            round_trip = float(route["roundTripSeconds"])
            req = deepcopy(base_requirements)
            req.update(deepcopy(route.get("requirements") or {}))
            bank_per_item = bank_inventory / inv
            travel = max(0.0, round_trip / inv - process_seconds - bank_per_item)
            variants.append({
                "id": str(route["id"]),
                "label": str(route["label"]),
                "overrides": {
                    "cycles_per_hour": cph,
                    "theoretical_cycles_per_hour": cph,
                    "requirements": req,
                    "workflow": {
                        "process_seconds": process_seconds,
                        "bank_seconds": bank_per_item,
                        "travel_seconds": travel,
                        "inventory_size": int(defaults.get("inventorySize", 28)),
                        "items_per_inventory": inv,
                    },
                },
            })
        method_id = f"charge_{element}_orb"
        notes = str(defaults.get("notes") or "Route-aware orb charging.")
        result[method_id] = _method(
            name=f"Charge {element} orbs",
            category=str(defaults.get("category", "processing/magic")),
            inputs=[_item("Unpowered orb", buy=True), _item("Cosmic rune", float(defaults.get("cosmicRunes", 3)), buy=True)],
            outputs=[_item(str(spec["product"]))],
            cycles=float(routes[0]["cyclesPerHour"]),
            theoretical=float(routes[0]["cyclesPerHour"]),
            interval=45,
            requirements=base_requirements,
            notes=notes,
            reference=str(spec.get("reference") or source.get("url")),
            method_types=["processing", "variants", "travel"],
            source=source,
            variants=variants,
        )
    return result


def _rune_inputs(raw: list[list[Any]]) -> list[dict[str, Any]]:
    return [_item(str(name), float(quantity), buy=True) for name, quantity in raw]


def compile_teleport_tablets(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = load_catalogue_document(path)
    if payload.get("family") != "teleport_tablets":
        raise ValueError("expected teleport_tablets family")
    defaults = payload.get("defaults") or {}
    source = dict(payload.get("source") or {})
    reference = str(source.get("url"))
    category = str(defaults.get("category", "bankstanding/magic"))
    cycles = float(defaults.get("cyclesPerHour", 1200))
    theoretical = float(defaults.get("theoreticalCyclesPerHour", 1500))
    interval = float(defaults.get("intervalSeconds", 2.4))
    workflow = deepcopy(defaults.get("workflow") or {})
    methods: dict[str, dict[str, Any]] = {}

    for row in payload.get("standard") or []:
        magic = int(row["magic"]); construction = int(row["construction"]); lectern = str(row["lectern"])
        req = {"members": True, "magic": magic, "construction": construction, "poh_features": [lectern]}
        methods[f"make_teleport_tablet_standard_{row['id']}"] = _method(
            name=f"Make {row['product']} tablets", category=category,
            inputs=[_item("Soft clay", buy=True), *_rune_inputs(row.get("runes") or [])], outputs=[_item(str(row["product"]))],
            cycles=cycles, theoretical=theoretical, interval=interval, requirements=req,
            notes="Standard spellbook teleport tablet. Four-tick creation plus banking overhead.", reference=reference,
            method_types=["bankstanding", "variants"], source=source, workflow=deepcopy(workflow),
            variants=[
                {"id": "minimum_lectern", "label": lectern, "overrides": {}},
                {"id": "marble_lectern", "label": "Marble lectern", "overrides": {"requirements": {"members": True, "magic": magic, "construction": 77, "poh_features": ["Marble lectern"]}}},
            ],
        )

    for book in ("ancient", "lunar"):
        spec = payload.get(book) or {}
        quest = str(spec.get("quest") or "")
        for row in spec.get("rows") or []:
            magic = int(row["magic"])
            req = {"members": True, "magic": magic, "quests": [quest], "unlocks": [f"{book}_spellbook"]}
            methods[f"make_teleport_tablet_{book}_{row['id']}"] = _method(
                name=f"Make {row['product']} tablets", category=category,
                inputs=[_item("Soft clay", buy=True), *_rune_inputs(row.get("runes") or [])], outputs=[_item(str(row["product"]))],
                cycles=cycles, theoretical=theoretical, interval=interval, requirements=req,
                notes=f"{book.title()} teleport tablet with its dedicated lectern requirement.", reference=reference,
                method_types=["bankstanding"], source=source, workflow=deepcopy(workflow),
            )

    for row in (payload.get("arceuus") or {}).get("rows") or []:
        magic = int(row["magic"])
        methods[f"make_teleport_tablet_arceuus_{row['id']}"] = _method(
            name=f"Make {row['product']} tablets", category=category, inputs=[], outputs=[_item(str(row["product"]))],
            cycles=cycles, theoretical=theoretical, interval=interval,
            requirements={"members": True, "magic": magic, "mining": 38, "unlocks": ["arceuus_spellbook"], "supplies": ["Self-supplied dark essence block and spell runes"]},
            notes="Arceuus tablets consume an untradeable dark essence block. This catalogue entry intentionally reports market revenue only until an integrated essence/time model is available.",
            reference=reference, method_types=["bankstanding"], source=source,
            model={"unpricedInputs": ["Dark essence block", "Spell runes pending recipe audit"]},
        )
    return methods


def _potion_base(name: str, unf: str, secondary: str, product: str, level: int, defaults: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    chemistry = product.endswith("(3)")
    primary = _item(product, role="primary")
    method = _method(
        name=f"Make {product.replace('(3)', '')}", category=str(defaults.get("category", "bankstanding/herblore")),
        inputs=[_item(unf, buy=True, role="unfinished"), _item(secondary, buy=True, role="secondary")], outputs=[primary],
        cycles=float(defaults.get("cyclesPerHour", 2500)), theoretical=float(defaults.get("theoreticalCyclesPerHour", 2500)),
        interval=float(defaults.get("intervalSeconds", 16.8)), requirements={"members": True, "herblore": int(level)},
        notes="Potion V2: true dose output, chemistry 4-dose EV and prescription-goggle expected secondary consumption.",
        reference=str(source.get("url")), method_types=["bankstanding", "probabilistic", "modifiers"], source=source,
        variants=[], model={"doseModel": {"chemistryProcChance": float(defaults.get("chemistryProcChance", .05)) if chemistry else 0, "gogglesSaveChance": float(defaults.get("gogglesSaveChance", .10))}, "modifierEngine": "v2"}, modifiers=[],
    )
    method["modifiers"].append({
        "id": "prescription_goggles", "requirements": {"equipment": ["Prescription goggles"]},
        "input_modifiers": [{"role": "secondary", "expected_multiplier": .9, "maximum_multiplier": 1.0}],
    })
    if chemistry:
        product4 = product[:-3] + "(4)"
        method["modifiers"].append({
            "id": "amulet_of_chemistry", "requirements": {"equipment": ["Amulet of chemistry"]},
            "output_modifiers": [{"role": "primary", "expected_multiplier": .95, "minimum_multiplier": .95, "maximum_multiplier": .95}],
            "added_items": [
                {"side": "outputs", "item_name": product4, "quantity": 1.0, "quantity_expected": .05, "quantity_minimum": .05, "quantity_maximum": .05, "role": "chemistry_proc"},
                {"side": "inputs", "item_name": "Amulet of chemistry", "quantity": 1.0, "quantity_expected": .01, "quantity_maximum": .2, "role": "chemistry_charge"},
            ],
            "metadata": {"procChance": .05},
        })
    return method


def compile_potion_v2(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = load_catalogue_document(path)
    if payload.get("family") != "potion_v2":
        raise ValueError("expected potion_v2 family")
    defaults = payload.get("defaults") or {}; source = dict(payload.get("source") or {})
    methods: dict[str, dict[str, Any]] = {}
    for key, unf, secondary, product, level in payload.get("rows") or []:
        methods[f"make_{key}_potions_v2"] = _potion_base(str(key), str(unf), str(secondary), str(product), int(level), defaults, source)

    for special_id, row in (payload.get("special") or {}).items():
        inputs = [_item(str(name), float(qty), buy=True) for name, qty in row.get("inputs") or []]
        outputs = [_item(str(name), float(qty)) for name, qty in row.get("outputs") or []]
        method = _method(
            name=str(row["name"]), category=str(defaults.get("category", "bankstanding/herblore")), inputs=inputs, outputs=outputs,
            cycles=float(row["cyclesPerHour"]), theoretical=float(row["theoreticalCyclesPerHour"]), interval=float(row["intervalSeconds"]),
            requirements=deepcopy(row.get("requirements") or {}), notes=("True four-dose stamina recipe; chemistry is not applied to an already four-dose result." if special_id == "stamina" else "Four-dose recipe with two recovered vials. Goggles modifier values the 10% torstol save."),
            reference=str(row.get("reference") or source.get("url")), method_types=["bankstanding"], source=source,
        )
        if special_id == "super_combat":
            method["inputs"][-1]["role"] = "secondary"
            method["modifiers"] = [{
                "id": "prescription_goggles", "requirements": {"equipment": ["Prescription goggles"]},
                "input_modifiers": [{"role": "secondary", "expected_multiplier": .9, "maximum_multiplier": 1.0}],
                "throughput_multiplier": 2400 / float(row["cyclesPerHour"]),
            }]
            method["method_types"] = ["bankstanding", "modifiers", "probabilistic"]
            method["model"] = {"modifierEngine": "v2"}
        methods[str(row["methodId"])] = method
    return methods


def compile_probabilistic_cooking(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = load_catalogue_document(path)
    if payload.get("family") != "probabilistic_cooking":
        raise ValueError("expected probabilistic_cooking family")
    defaults = payload.get("defaults") or {}; source = dict(payload.get("source") or {})
    methods: dict[str, dict[str, Any]] = {}
    for key, row in (payload.get("foods") or {}).items():
        curves = {str(name): {"low": float(values[0]), "high": float(values[1])} for name, values in (row.get("curves") or {}).items()}
        level = int(row["minimumLevel"]); raw = str(row["raw"]); cooked = str(row["cooked"])
        methods[f"cook_probabilistic_{key}"] = _method(
            name=f"Cook {raw.removeprefix('Raw ').lower()}", category=str(defaults.get("category", "strict_afk/cooking")),
            inputs=[_item(raw, buy=True)], outputs=[_item(cooked)], cycles=float(defaults.get("cyclesPerHour", 1300)),
            theoretical=float(defaults.get("theoreticalCyclesPerHour", 1500)), interval=float(defaults.get("intervalSeconds", 67.2)),
            requirements={"members": True, "cooking": level},
            notes="User-level burn model using Wiki skilling-success chart parameters, location, gauntlets and explicit 99/Cooking-cape zero-burn mode.",
            reference=str(source.get("url")), method_types=["bankstanding", "make-x", "probabilistic"], source=source,
            model={"cooking": {"minimumLevel": level, "gauntletsAffected": bool(row.get("gauntletsAffected")), "curves": curves, "defaults": {"level": 99, "location": "range", "gauntlets": False, "cookingCape": True}}},
        )
    return methods


_REPLACEMENT_COMPILERS: dict[str, Callable[[str | Path], dict[str, dict[str, Any]]]] = {
    "jewellery_enchanting": compile_jewellery_enchanting,
    "orb_charging": compile_orb_charging,
    "teleport_tablets": compile_teleport_tablets,
    "potion_v2": compile_potion_v2,
    "probabilistic_cooking": compile_probabilistic_cooking,
}


def compile_catalogue_manifest(path: str | Path, base_methods: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    manifest_path = Path(path).resolve()
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if int(payload.get("schemaVersion", 0)) != 1:
        raise ValueError("unsupported catalogue manifest schema")
    families = payload.get("families") or []
    effective = deepcopy(base_methods)
    owners: dict[str, str] = {}
    family_rows: list[dict[str, Any]] = []

    for family in families:
        family_id = str(family["id"]); compiler_id = str(family["compiler"]); mode = str(family.get("mode") or "replace")
        raw_path = Path(str(family["path"]))
        source_path = raw_path if raw_path.is_absolute() else manifest_path.parent / raw_path
        source_path = source_path.resolve()
        if mode == "transform":
            if compiler_id != "gathering_pacing":
                raise ValueError(f"unsupported transform compiler: {compiler_id}")
            compiled = compile_gathering_pacing(source_path, effective)
        else:
            compiler = _REPLACEMENT_COMPILERS.get(compiler_id)
            if compiler is None:
                raise ValueError(f"unknown catalogue compiler: {compiler_id}")
            compiled = compiler(source_path)
        collisions = sorted(method_id for method_id in compiled if method_id in owners and owners[method_id] != family_id)
        if collisions:
            raise ValueError(f"catalogue method IDs owned by multiple data families: {collisions}")
        for method_id, method in compiled.items():
            effective[method_id] = method
            owners[method_id] = family_id
        family_rows.append({"id": family_id, "compiler": compiler_id, "mode": mode, "path": str(source_path), "methodCount": len(compiled)})

    # Preserve the explicit GE exclusion of the untradeable Digsite pendant.
    ruby = effective.get("enchant_ruby_necklace")
    if ruby is not None:
        ruby["enabled"] = False
        suffix = " Output is an untradeable Digsite pendant and is intentionally excluded from GE profit ranking."
        if suffix.strip() not in str(ruby.get("notes") or ""):
            ruby["notes"] = str(ruby.get("notes") or "") + suffix

    report = {
        "schemaVersion": 1,
        "catalogueVersion": int(payload.get("catalogueVersion", 0)),
        "policy": deepcopy(payload.get("policy") or {}),
        "familyCount": len(family_rows),
        "dataOwnedMethodCount": len(owners),
        "families": family_rows,
        "methodOwners": dict(sorted(owners.items())),
    }
    return effective, report
