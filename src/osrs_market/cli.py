from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION
from .alchemy import build_alchemy_candidate, preliminary_scan
from .api import ApiError, MarketApiClient
from .cache import item_windows, load_history, load_mapping, put_item_windows, save_history, save_mapping
from .catalog_gap import build_catalog_gap_report
from .config import api_settings, load_json, load_yaml
from .method_model import all_method_item_ids
from .methods_v2 import evaluate_method
from .metrics import calculate_window_metrics
from .models import LatestPrice, MappingItem, TimeSeriesPoint
from .public_models import build_public_alchemy, build_public_status
from .public_models_v2 import build_public_afk
from .public_site import write_json, write_public_site
from .quality import build_quality, current_diagnostics
from .tax import load_and_resolve_exemptions
from .windows import WINDOW_SPECS, slice_window

LOGGER = logging.getLogger("osrs_market")
COLLECTION_MODES = ("live", "short", "long", "full")


class CollectionStats:
    def __init__(self) -> None:
        self.timeseries_requested = 0
        self.timeseries_succeeded = 0
        self.timeseries_failed = 0
        self.warnings: list[str] = []


class SeriesCollector:
    def __init__(self, client: MarketApiClient, stats: CollectionStats) -> None:
        self.client = client
        self.stats = stats
        self.cache: dict[tuple[int, str], list[TimeSeriesPoint]] = {}
        self.failed_keys: set[tuple[int, str]] = set()

    def get(self, item_id: int, timestep: str) -> list[TimeSeriesPoint]:
        key = (item_id, timestep)
        if key in self.cache:
            return self.cache[key]
        self.stats.timeseries_requested += 1
        try:
            series = self.client.get_timeseries(item_id, timestep)
        except ApiError as exc:
            self.stats.timeseries_failed += 1
            self.failed_keys.add(key)
            warning = f"TIMESERIES_FAILED item={item_id} timestep={timestep}: {exc}"
            self.stats.warnings.append(warning)
            LOGGER.warning(warning)
            series = []
        else:
            self.stats.timeseries_succeeded += 1
        self.cache[key] = series
        return series


def _record_for_item(item: MappingItem, latest: LatestPrice, windows: dict[str, dict[str, Any]], generated_at: int, settings: dict[str, Any]) -> dict[str, Any]:
    current = current_diagnostics(latest, generated_at, settings["freshness"])
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "item": item.to_dict(),
        "latest": latest.to_api_dict(),
        "current": current,
        "windows": windows,
        "quality": build_quality(current, windows, item.limit, item.highalch, settings),
    }


def _mapping_name_index(mapping: dict[int, MappingItem]) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for item_id, item in mapping.items():
        index.setdefault(item.name.casefold(), []).append(item_id)
    return index


def _resolve_catalog_item_names(methods_config: dict[str, Any], mapping: dict[int, MappingItem]) -> None:
    """Resolve authored item names to immutable numeric mapping IDs.

    Base recipes, variant overrides and modifier-added inputs/outputs all pass
    through the same fail-closed resolver. A modifier must never introduce an
    item that bypasses production mapping validation.
    """
    index = _mapping_name_index(mapping)
    errors: list[str] = []

    def resolve(method_id: str, context: str, entry: dict[str, Any]) -> None:
        if entry.get("item_id") is not None:
            return
        name = str(entry.get("item_name") or "").strip()
        if not name:
            return
        matches = index.get(name.casefold(), [])
        if len(matches) != 1:
            errors.append(f"{method_id}: {context} item_name {name!r} resolved to {len(matches)} mapping rows")
            return
        entry["item_id"] = matches[0]

    for method_id, method in methods_config.get("methods", {}).items():
        if method.get("enabled", True) is False:
            continue
        for side in ("inputs", "outputs"):
            for entry in method.get(side, []):
                resolve(str(method_id), side, entry)
        for raw in method.get("variants") or []:
            overrides = raw.get("overrides") or {}
            variant_id = str(raw.get("id") or "variant")
            for side in ("inputs", "outputs"):
                for entry in overrides.get(side, []):
                    resolve(str(method_id), f"variant {variant_id} {side}", entry)
        for modifier in method.get("modifiers") or []:
            modifier_id = str(modifier.get("id") or "modifier")
            for entry in modifier.get("added_items") or []:
                resolve(str(method_id), f"modifier {modifier_id} {entry.get('side') or 'item'}", entry)

    if errors:
        raise ValueError("catalogue item-name resolution failed: " + "; ".join(errors))


def _required_method_item_ids(methods_config: dict[str, Any]) -> set[int]:
    ids: set[int] = set()
    for method in methods_config.get("methods", {}).values():
        if method.get("enabled", True) is not False:
            ids.update(all_method_item_ids(method))
    return ids


def _refresh_plan(mode: str) -> dict[str, tuple[str, ...]]:
    short = {"5m": ("6h", "24h"), "1h": ("7d",)}
    long = {"6h": ("30d",)}
    if mode == "short":
        return short
    if mode == "long":
        return long
    if mode == "full":
        return {**short, **long, "24h": ("6m",)}
    return {}


def _refresh_history(item_ids: set[int], history: dict[str, Any], collector: SeriesCollector, generated_at: int, mode: str) -> None:
    for timestep, window_keys in _refresh_plan(mode).items():
        for item_id in sorted(item_ids):
            points = collector.get(item_id, timestep)
            if (item_id, timestep) in collector.failed_keys:
                continue
            updates = {
                key: calculate_window_metrics(
                    slice_window(points, generated_at, WINDOW_SPECS[key].duration_seconds),
                    WINDOW_SPECS[key],
                )
                for key in window_keys
            }
            if updates:
                put_item_windows(history, item_id, updates)


def _load_or_fetch_mapping(client: MarketApiClient, cache_dir: Path, generated_at: int, force_refresh: bool) -> dict[int, MappingItem]:
    if not force_refresh:
        cached = load_mapping(cache_dir)
        if cached is not None:
            mapping, cached_at = cached
            LOGGER.info("mapping cache: %s items generatedAt=%s", len(mapping), cached_at)
            return mapping
    mapping = client.get_mapping()
    save_mapping(cache_dir, mapping, generated_at)
    return mapping


def _write_internal_report(
    root: Path,
    generated_at: int,
    records: dict[int, dict[str, Any]],
    base_ids: set[int],
    tracked_ids: list[int],
    methods_config: dict[str, Any],
    afk_results: list[dict[str, Any]],
    alchemy_candidates: list[dict[str, Any]],
    preliminary_count: int,
    alchemy_assumptions: dict[str, Any],
    health: dict[str, Any],
    anomalies: list[dict[str, Any]],
) -> None:
    if root.exists():
        shutil.rmtree(root)
    (root / "market" / "items").mkdir(parents=True, exist_ok=True)
    (root / "afk").mkdir(parents=True, exist_ok=True)
    (root / "alchemy").mkdir(parents=True, exist_ok=True)
    market_items = []
    for item_id in sorted(base_ids):
        record = records.get(item_id)
        if record is None:
            continue
        market_items.append(record)
        if item_id in tracked_ids:
            write_json(root / "market" / "items" / f"{item_id}.json", record)
    write_json(root / "health.json", health)
    write_json(root / "profit-anomalies.json", {"schemaVersion": SCHEMA_VERSION, "generatedAt": generated_at, "anomalies": anomalies})
    write_json(root / "catalogue-gap.json", build_catalog_gap_report(methods_config.get("methods", {})))
    write_json(root / "market" / "summary.json", {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "items": market_items,
        "disclaimer": "Observed high/low trades are not a synchronized order book. Historical observed volume is a liquidity proxy, not executable market depth.",
    })
    write_json(root / "afk" / "results.json", {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "methods": methods_config.get("methods", {}),
        "results": afk_results,
    })
    write_json(root / "alchemy" / "candidates.json", {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "assumptions": alchemy_assumptions,
        "preliminaryCandidateCount": preliminary_count,
        "candidates": alchemy_candidates,
    })


def collect(config_dir: Path, output_dir: Path, cache_dir: Path, mode: str = "full") -> None:
    if mode not in COLLECTION_MODES:
        raise ValueError(f"unsupported collection mode: {mode}")
    settings = load_yaml(config_dir / "settings.yaml")
    tracked_config = load_json(config_dir / "tracked_items.json")
    methods_config = load_yaml(config_dir / "methods.yaml")
    alchemy_overrides = load_json(config_dir / "alchemy_exclusions.json")
    generated_at = int(time.time())
    stats = CollectionStats()
    client = MarketApiClient(api_settings(settings))

    mapping = _load_or_fetch_mapping(client, cache_dir, generated_at, force_refresh=mode == "full")
    _resolve_catalog_item_names(methods_config, mapping)
    latest = client.get_latest()
    exempt_ids, unresolved = load_and_resolve_exemptions(config_dir / "ge_tax_exemptions.json", mapping)
    stats.warnings.extend(f"UNRESOLVED_TAX_EXEMPTION_NAME: {name}" for name in unresolved)

    tracked_ids = [int(row["id"]) for row in tracked_config.get("items", [])]
    missing_tracked = [item_id for item_id in tracked_ids if item_id not in mapping]
    if missing_tracked:
        raise ValueError(f"tracked item IDs missing from mapping: {missing_tracked}")

    nature_id = int(settings["alchemy"]["nature_rune_item_id"])
    use_fire_staff = bool(settings["alchemy"].get("use_fire_staff", True))
    fire_id = int(settings["alchemy"].get("fire_rune_item_id", 554))
    missing_alchemy_ids = [nature_id] if nature_id not in mapping else []
    if not use_fire_staff and fire_id not in mapping:
        missing_alchemy_ids.append(fire_id)
    if missing_alchemy_ids:
        raise ValueError(f"configured alchemy rune item IDs missing from mapping: {missing_alchemy_ids}")

    method_ids = _required_method_item_ids(methods_config)
    missing_method_ids = sorted(item_id for item_id in method_ids if item_id not in mapping)
    if missing_method_ids:
        raise ValueError(f"configured method item IDs missing from mapping: {missing_method_ids}")
    base_ids = set(tracked_ids) | method_ids | {nature_id}
    if not use_fire_staff:
        base_ids.add(fire_id)

    preliminary = []
    if bool(settings["alchemy"].get("enabled", True)):
        preliminary = preliminary_scan(
            mapping,
            latest,
            generated_at,
            settings,
            {int(value) for value in alchemy_overrides.get("excludedItemIds", [])},
            {int(value) for value in alchemy_overrides.get("forcedItemIds", [])},
        )

    history = load_history(cache_dir)
    candidate_ids = {int(row["itemId"]) for row in preliminary}
    collector = SeriesCollector(client, stats)
    _refresh_history(base_ids | candidate_ids, history, collector, generated_at, mode)
    if mode in {"short", "full"}:
        history["shortGeneratedAt"] = generated_at
    if mode in {"long", "full"}:
        history["longGeneratedAt"] = generated_at
    if mode != "live":
        save_history(cache_dir, history)

    records = {
        item_id: _record_for_item(
            mapping[item_id],
            latest.get(item_id, LatestPrice.from_api(None)),
            item_windows(history, item_id),
            generated_at,
            settings,
        )
        for item_id in sorted(base_ids)
    }

    afk_results: list[dict[str, Any]] = []
    for method_id, method in methods_config.get("methods", {}).items():
        afk_results.extend(evaluate_method(str(method_id), method, records, exempt_ids, settings, generated_at))

    alchemy_candidates = []
    if preliminary:
        nature_record = records[nature_id]
        latest_nature = latest.get(nature_id, LatestPrice.from_api(None))
        fire_record = records[fire_id] if not use_fire_staff else None
        latest_fire = latest.get(fire_id, LatestPrice.from_api(None)) if not use_fire_staff else None
        for row in preliminary:
            item_id = int(row["itemId"])
            item = mapping[item_id]
            alchemy_candidates.append(build_alchemy_candidate(
                item,
                latest.get(item_id, LatestPrice.from_api(None)),
                latest_nature,
                item_windows(history, item_id),
                nature_record["windows"],
                generated_at,
                settings,
                latest_fire=latest_fire,
                fire_windows=fire_record["windows"] if fire_record else None,
            ))
    alchemy_candidates.sort(
        key=lambda row: row["currentInstant"]["profitPerCast"] if row["currentInstant"]["profitPerCast"] is not None else float("-inf"),
        reverse=True,
    )

    health_status = "degraded" if stats.timeseries_failed or stats.warnings else "ok"
    health = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "mode": mode,
        "status": health_status,
        "api": {
            "mapping": "ok",
            "latest": "ok",
            "timeseriesRequested": stats.timeseries_requested,
            "timeseriesSucceeded": stats.timeseries_succeeded,
            "timeseriesFailed": stats.timeseries_failed,
        },
        "history": {
            "shortGeneratedAt": history.get("shortGeneratedAt"),
            "longGeneratedAt": history.get("longGeneratedAt"),
        },
        "warnings": stats.warnings,
    }
    alchemy_assumptions = {
        "magicLevel": 55,
        "xpPerCast": int(settings["alchemy"].get("xp_per_cast", 65)),
        "castsPerHour": int(settings["alchemy"].get("casts_per_hour", 1200)),
        "secondsPerCast": 3,
        "useFireStaff": use_fire_staff,
        "natureRuneItemId": nature_id,
    }

    internal_dir = output_dir / "internal-report"
    public_dir = output_dir / "public-site"
    anomalies: list[dict[str, Any]] = []
    public_afk = build_public_afk(generated_at, afk_results, anomaly_sink=anomalies)
    _write_internal_report(
        internal_dir,
        generated_at,
        records,
        base_ids,
        tracked_ids,
        methods_config,
        afk_results,
        alchemy_candidates,
        len(preliminary),
        alchemy_assumptions,
        health,
        anomalies,
    )
    write_public_site(
        public_dir,
        public_afk,
        build_public_alchemy(generated_at, alchemy_candidates, alchemy_assumptions),
        build_public_status(
            generated_at,
            health,
            short_history_generated_at=history.get("shortGeneratedAt"),
            long_history_generated_at=history.get("longGeneratedAt"),
        ),
    )
    gap = build_catalog_gap_report(methods_config.get("methods", {}))
    LOGGER.info(
        "AFK methods: %s; catalogue coverage: %s%%; missing families: %s",
        len(methods_config.get("methods", {})),
        gap["coveragePct"],
        gap["missingFamilyCount"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect OSRS market data and build public/private artifacts")
    sub = parser.add_subparsers(dest="command", required=True)
    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--config", default="config")
    collect_parser.add_argument("--output", default="build")
    collect_parser.add_argument("--cache-dir", default=".market-cache")
    collect_parser.add_argument("--mode", choices=COLLECTION_MODES, default="full")
    gap_parser = sub.add_parser("catalog-gap")
    gap_parser.add_argument("--config", default="config")
    gap_parser.add_argument("--output", default="build/catalogue-gap.json")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        if args.command == "collect":
            collect(Path(args.config), Path(args.output), Path(args.cache_dir), args.mode)
            return 0
        methods = load_yaml(Path(args.config) / "methods.yaml").get("methods", {})
        report = build_catalog_gap_report(methods)
        write_json(Path(args.output), report)
        LOGGER.info("catalogue coverage: %s%%", report["coveragePct"])
        return 0
    except (ApiError, ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        LOGGER.error("collection failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
