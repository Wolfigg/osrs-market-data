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
from .publisher import validate_site, write_index_html, write_json
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


def _record_for_item(
    item: MappingItem,
    latest: LatestPrice,
    series: dict[str, list[TimeSeriesPoint]],
    generated_at: int,
    settings: dict[str, Any],
    include_raw: bool,
) -> dict[str, Any]:
    window_data: dict[str, dict[str, Any]] = {}
    for key, (spec, points) in build_windows(series, generated_at).items():
        window_data[key] = calculate_window_metrics(points, spec)
    current = current_diagnostics(latest, generated_at, settings["freshness"])
    quality = build_quality(current, window_data, item.limit, item.highalch, settings)
    record = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "item": item.to_dict(),
        "latest": latest.to_api_dict(),
        "current": current,
        "windows": window_data,
        "quality": quality,
    }
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

    exempt_ids, unresolved_exemptions = load_and_resolve_exemptions(config_dir / "ge_tax_exemptions.json", mapping)
    for name in unresolved_exemptions:
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
            stats.warnings.append(f"METHOD_OR_INTERNAL_ITEM_MISSING_FROM_MAPPING: {item_id}")
            continue
        item_series = {timestep: collector.get(item_id, timestep) for timestep in ("5m", "1h", "6h", "24h")}
        records[item_id] = _record_for_item(
            item,
            latest.get(item_id, LatestPrice.from_api(None)),
            item_series,
            generated_at,
            settings,
            include_raw=item_id in tracked_ids and bool(settings["publishing"].get("include_raw_series_for_tracked_items", True)),
        )

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
            candidate_series = {
                "5m": collector.get(item_id, "5m"),
                "1h": collector.get(item_id, "1h"),
                "6h": [],
                "24h": [],
            }
            candidate_record = _record_for_item(
                item,
                latest.get(item_id, LatestPrice.from_api(None)),
                candidate_series,
                generated_at,
                settings,
                include_raw=False,
            )
            if nature_record is None:
                continue
            candidate = build_alchemy_candidate(
                item,
                latest.get(item_id, LatestPrice.from_api(None)),
                latest_nature,
                candidate_record["windows"],
                nature_record["windows"],
                generated_at,
                settings,
                latest_fire=latest_fire,
                fire_windows=fire_record["windows"] if fire_record else None,
            )
            alchemy_candidates.append(candidate)
        alchemy_candidates.sort(
            key=lambda row: row["currentInstant"]["profitPerCast"] if row["currentInstant"]["profitPerCast"] is not None else float("-inf"),
            reverse=True,
        )

    method_results: list[dict[str, Any]] = []
    for method_id, method in methods_config.get("methods", {}).items():
        method_results.extend(
            evaluate_method(
                str(method_id),
                method,
                records,
                exempt_ids,
                settings,
                nature_id,
                generated_at,
            )
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    (output_dir / "items").mkdir(parents=True, exist_ok=True)

    tracked_entries = []
    market_items = []
    for item_id in tracked_ids:
        record = records[item_id]
        tracked_entries.append({"id": item_id, "name": record["item"]["name"], "path": f"items/{item_id}.json"})
        write_json(output_dir / "items" / f"{item_id}.json", record)
        market_items.append({key: value for key, value in record.items() if key != "series"})

    health_status = "degraded" if stats.timeseries_failed or stats.warnings else "ok"
    health = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "status": health_status,
        "api": {
            "mapping": "ok",
            "latest": "ok",
            "timeseriesRequested": stats.timeseries_requested,
            "timeseriesSucceeded": stats.timeseries_succeeded,
            "timeseriesFailed": stats.timeseries_failed,
        },
        "warnings": stats.warnings,
    }
    index = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "game": "osrs",
        "files": {
            "health": "health.json",
            "market": "market.json",
            "alchemy": "alchemy.json",
            "opportunities": "opportunities.json",
            "methods": "methods.json",
        },
        "trackedItems": tracked_entries,
    }
    market = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "items": market_items,
        "disclaimer": "Observed high/low trades are not a synchronized order book. Historical observed volume is a liquidity proxy, not executable market depth.",
    }
    alchemy = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "assumptions": {
            "magicLevel": 55,
            "xpPerCast": int(settings["alchemy"].get("xp_per_cast", 65)),
            "castsPerHour": int(settings["alchemy"].get("casts_per_hour", 1200)),
            "secondsPerCast": 3,
            "useFireStaff": bool(settings["alchemy"].get("use_fire_staff", True)),
            "natureRuneItemId": nature_id,
        },
        "preliminaryCandidateCount": len(preliminary),
        "candidates": alchemy_candidates,
    }
    opportunities = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "opportunities": sorted(
            method_results,
            key=lambda row: row["economics"]["profitGpPerHourBuyLimitSustainable"]
            if row["economics"]["profitGpPerHourBuyLimitSustainable"] is not None
            else float("-inf"),
            reverse=True,
        ),
    }
    methods_output = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "methods": methods_config.get("methods", {}),
    }

    write_json(output_dir / "index.json", index)
    write_json(output_dir / "health.json", health)
    write_json(output_dir / "market.json", market)
    write_json(output_dir / "alchemy.json", alchemy)
    write_json(output_dir / "opportunities.json", opportunities)
    write_json(output_dir / "methods.json", methods_output)
    write_index_html(output_dir, generated_at)
    validate_site(output_dir)

    LOGGER.info("tracked items: %s", len(tracked_ids))
    LOGGER.info("alchemy timeseries candidates: %s", len(alchemy_candidates))
    LOGGER.info("timeseries requests: %s", stats.timeseries_requested)
    LOGGER.info("timeseries failures: %s", stats.timeseries_failed)
    LOGGER.info("generated: %s", output_dir / "index.json")
    LOGGER.info("status: %s", health_status)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect and publish OSRS market data")
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect_parser = subparsers.add_parser("collect", help="fetch market data and build the static JSON site")
    collect_parser.add_argument("--config", default="config", help="configuration directory")
    collect_parser.add_argument("--output", default="site", help="generated site directory")
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
