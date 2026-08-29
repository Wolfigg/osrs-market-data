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
from .config import api_settings, load_json, load_yaml
from .methods import evaluate_method
from .metrics import calculate_window_metrics
from .models import LatestPrice, MappingItem, TimeSeriesPoint
from .public_models import build_dashboard, build_public_afk, build_public_alchemy, build_public_status
from .public_site import write_json, write_public_site
from .quality import build_quality, current_diagnostics
from .tax import load_and_resolve_exemptions
from .windows import build_windows

LOGGER = logging.getLogger("osrs_market")


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

    def get(self, item_id: int, timestep: str) -> list[TimeSeriesPoint]:
        key = (item_id, timestep)
        if key in self.cache:
            return self.cache[key]
        self.stats.timeseries_requested += 1
        try:
            series = self.client.get_timeseries(item_id, timestep)
        except ApiError as exc:
            self.stats.timeseries_failed += 1
            warning = f"TIMESERIES_FAILED item={item_id} timestep={timestep}: {exc}"
            self.stats.warnings.append(warning)
            LOGGER.warning(warning)
            series = []
        else:
            self.stats.timeseries_succeeded += 1
        self.cache[key] = series
        return series


def _record_for_item(item: MappingItem, latest: LatestPrice, series: dict[str, list[TimeSeriesPoint]], generated_at: int, settings: dict[str, Any], include_raw: bool) -> dict[str, Any]:
    windows: dict[str, dict[str, Any]] = {}
    for key, (spec, points) in build_windows(series, generated_at).items():
        windows[key] = calculate_window_metrics(points, spec)
    current = current_diagnostics(latest, generated_at, settings["freshness"])
    quality = build_quality(current, windows, item.limit, item.highalch, settings)
    record: dict[str, Any] = {"schemaVersion": SCHEMA_VERSION, "generatedAt": generated_at, "item": item.to_dict(), "latest": latest.to_api_dict(), "current": current, "windows": windows, "quality": quality}
    if include_raw:
        record["series"] = {timestep: [point.to_api_dict() for point in points] for timestep, points in series.items()}
    return record


def _required_method_item_ids(methods_config: dict[str, Any]) -> set[int]:
    ids: set[int] = set()
    for method in methods_config.get("methods", {}).values():
        if method.get("enabled", True) is False:
            continue
        for side in ("inputs", "outputs"):
            ids.update(int(entry["item_id"]) for entry in method.get(side, []))
    return ids


def _write_internal_report(root: Path, generated_at: int, records: dict[int, dict[str, Any]], base_ids: set[int], tracked_ids: list[int], methods_config: dict[str, Any], afk_results: list[dict[str, Any]], alchemy_candidates: list[dict[str, Any]], preliminary_count: int, alchemy_assumptions: dict[str, Any], health: dict[str, Any]) -> None:
    if root.exists():
        shutil.rmtree(root)
    (root / "market" / "items").mkdir(parents=True, exist_ok=True)
    (root / "afk").mkdir(parents=True, exist_ok=True)
    (root / "alchemy").mkdir(parents=True, exist_ok=True)
    market_items: list[dict[str, Any]] = []
    for item_id in sorted(base_ids):
        record = records.get(item_id)
        if record is None:
            continue
        market_items.append({key: value for key, value in record.items() if key != "series"})
        if item_id in tracked_ids:
            write_json(root / "market" / "items" / f"{item_id}.json", record)
    write_json(root / "health.json", health)
    write_json(root / "market" / "summary.json", {"schemaVersion": SCHEMA_VERSION, "generatedAt": generated_at, "items": market_items, "disclaimer": "Observed high/low trades are not a synchronized order book. Historical observed volume is a liquidity proxy, not executable market depth."})
    write_json(root / "afk" / "results.json", {"schemaVersion": SCHEMA_VERSION, "generatedAt": generated_at, "methods": methods_config.get("methods", {}), "results": afk_results})
    write_json(root / "alchemy" / "candidates.json", {"schemaVersion": SCHEMA_VERSION, "generatedAt": generated_at, "assumptions": alchemy_assumptions, "preliminaryCandidateCount": preliminary_count, "candidates": alchemy_candidates})


def collect(config_dir: Path, output_dir: Path) -> None:
    settings = load_yaml(config_dir / "settings.yaml")
    tracked_config = load_json(config_dir / "tracked_items.json")
    methods_config = load_yaml(config_dir / "methods.yaml")
    alchemy_overrides = load_json(config_dir / "alchemy_exclusions.json")
    generated_at = int(time.time())
    stats = CollectionStats()
    client = MarketApiClient(api_settings(settings))
    LOGGER.info("fetching mapping and latest")
    mapping = client.get_mapping()
    latest = client.get_latest()
    LOGGER.info("mapping: %s items", len(mapping))
    LOGGER.info("latest: %s items", len(latest))

    exempt_ids, unresolved = load_and_resolve_exemptions(config_dir / "ge_tax_exemptions.json", mapping)
    for name in unresolved:
        stats.warnings.append(f"UNRESOLVED_TAX_EXEMPTION_NAME: {name}")
    tracked_ids = [int(row["id"]) for row in tracked_config.get("items", [])]
    missing_tracked = [item_id for item_id in tracked_ids if item_id not in mapping]
    if missing_tracked:
        raise ValueError(f"tracked item IDs missing from mapping: {missing_tracked}")

    nature_id = int(settings["alchemy"]["nature_rune_item_id"])
    use_fire_staff = bool(settings["alchemy"].get("use_fire_staff", True))
    fire_id = int(settings["alchemy"].get("fire_rune_item_id", 554))
    method_ids = _required_method_item_ids(methods_config)
    base_ids = set(tracked_ids) | method_ids | {nature_id}
    if not use_fire_staff:
        base_ids.add(fire_id)

    collector = SeriesCollector(client, stats)
    records: dict[int, dict[str, Any]] = {}
    for item_id in sorted(base_ids):
        item = mapping.get(item_id)
        if item is None:
            stats.warnings.append(f"CONFIGURED_ITEM_MISSING_FROM_MAPPING: {item_id}")
            continue
        item_series = {timestep: collector.get(item_id, timestep) for timestep in ("5m", "1h", "6h", "24h")}
        records[item_id] = _record_for_item(item, latest.get(item_id, LatestPrice.from_api(None)), item_series, generated_at, settings, include_raw=item_id in tracked_ids and bool(settings["publishing"].get("include_raw_series_for_tracked_items", True)))

    afk_results: list[dict[str, Any]] = []
    for method_id, method in methods_config.get("methods", {}).items():
        afk_results.extend(evaluate_method(str(method_id), method, records, exempt_ids, settings, generated_at))

    preliminary: list[dict[str, Any]] = []
    alchemy_candidates: list[dict[str, Any]] = []
    if bool(settings["alchemy"].get("enabled", True)):
        excluded = {int(x) for x in alchemy_overrides.get("excludedItemIds", [])}
        forced = {int(x) for x in alchemy_overrides.get("forcedItemIds", [])}
        preliminary = preliminary_scan(mapping, latest, generated_at, settings, excluded, forced)
        LOGGER.info("alchemy preliminary candidates: %s", len(preliminary))
        nature_record = records.get(nature_id)
        latest_nature = latest.get(nature_id, LatestPrice.from_api(None))
        fire_record = records.get(fire_id) if not use_fire_staff else None
        latest_fire = latest.get(fire_id, LatestPrice.from_api(None)) if not use_fire_staff else None
        for row in preliminary:
            item_id = int(row["itemId"])
            item = mapping[item_id]
            candidate_series = {"5m": collector.get(item_id, "5m"), "1h": collector.get(item_id, "1h"), "6h": collector.get(item_id, "6h"), "24h": collector.get(item_id, "24h")}
            candidate_record = _record_for_item(item, latest.get(item_id, LatestPrice.from_api(None)), candidate_series, generated_at, settings, include_raw=False)
            if nature_record is None:
                continue
            alchemy_candidates.append(build_alchemy_candidate(item, latest.get(item_id, LatestPrice.from_api(None)), latest_nature, candidate_record["windows"], nature_record["windows"], generated_at, settings, latest_fire=latest_fire, fire_windows=fire_record["windows"] if fire_record else None))

    alchemy_candidates.sort(key=lambda row: row["currentInstant"]["profitPerCast"] if row["currentInstant"]["profitPerCast"] is not None else float("-inf"), reverse=True)
    health_status = "degraded" if stats.timeseries_failed or stats.warnings else "ok"
    health = {"schemaVersion": SCHEMA_VERSION, "generatedAt": generated_at, "status": health_status, "api": {"mapping": "ok", "latest": "ok", "timeseriesRequested": stats.timeseries_requested, "timeseriesSucceeded": stats.timeseries_succeeded, "timeseriesFailed": stats.timeseries_failed}, "warnings": stats.warnings}
    alchemy_assumptions = {"magicLevel": 55, "xpPerCast": int(settings["alchemy"].get("xp_per_cast", 65)), "castsPerHour": int(settings["alchemy"].get("casts_per_hour", 1200)), "secondsPerCast": 3, "useFireStaff": use_fire_staff, "natureRuneItemId": nature_id}

    internal_dir = output_dir / "internal-report"
    public_dir = output_dir / "public-site"
    _write_internal_report(internal_dir, generated_at, records, base_ids, tracked_ids, methods_config, afk_results, alchemy_candidates, len(preliminary), alchemy_assumptions, health)
    public_afk = build_public_afk(generated_at, afk_results)
    public_alchemy = build_public_alchemy(generated_at, alchemy_candidates, alchemy_assumptions)
    public_status = build_public_status(generated_at, health)
    public_dashboard = build_dashboard(generated_at, public_afk, public_alchemy)
    write_public_site(public_dir, public_dashboard, public_afk, public_alchemy, public_status)

    LOGGER.info("tracked items: %s", len(tracked_ids))
    LOGGER.info("AFK methods: %s", len(methods_config.get("methods", {})))
    LOGGER.info("alchemy timeseries candidates: %s", len(alchemy_candidates))
    LOGGER.info("timeseries requests: %s", stats.timeseries_requested)
    LOGGER.info("timeseries failures: %s", stats.timeseries_failed)
    LOGGER.info("public site: %s", public_dir)
    LOGGER.info("internal diagnostics: %s", internal_dir)
    LOGGER.info("status: %s", health_status)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect OSRS market data and build public/private artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect_parser = subparsers.add_parser("collect", help="fetch market data and build artifacts")
    collect_parser.add_argument("--config", default="config", help="configuration directory")
    collect_parser.add_argument("--output", default="build", help="artifact root directory")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        if args.command == "collect":
            collect(Path(args.config), Path(args.output))
            return 0
    except (ApiError, ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        LOGGER.error("collection failed: %s", exc)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
