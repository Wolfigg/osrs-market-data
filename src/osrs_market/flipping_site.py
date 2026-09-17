from __future__ import annotations

import argparse
import logging
import shutil
import time
from pathlib import Path

from .api import ApiError, MarketApiClient
from .config import api_settings, load_yaml
from .flipping import build_public_flipping, select_flipping_timeseries_candidates
from .public_site import write_json
from .tax import load_and_resolve_exemptions

LOGGER = logging.getLogger("osrs_market.flipping")


def _flipping_excluded_item_ids(settings: dict) -> set[int]:
    raw = (settings.get("flipping") or {}).get("excluded_item_ids") or []
    return {int(item_id) for item_id in raw}


def build_hidden_flipping_site(config_dir: Path, public_dir: Path, web_dir: Path = Path("web")) -> None:
    data_dir = public_dir / "data"
    assets_dir = public_dir / "assets"
    if not public_dir.is_dir() or not data_dir.is_dir() or not assets_dir.is_dir():
        raise ValueError("public site must be built before installing the hidden flipping desk")

    settings = load_yaml(config_dir / "settings.yaml")
    generated_at = int(time.time())
    client = MarketApiClient(api_settings(settings))

    mapping = client.get_mapping()
    excluded_item_ids = _flipping_excluded_item_ids(settings)
    if excluded_item_ids:
        mapping = {item_id: item for item_id, item in mapping.items() if item_id not in excluded_item_ids}
    latest = client.get_latest()
    five_minute = client.get_average_prices("5m")
    one_hour = client.get_average_prices("1h")
    exempt_ids, unresolved = load_and_resolve_exemptions(config_dir / "ge_tax_exemptions.json", mapping)
    if unresolved:
        LOGGER.warning("unresolved GE tax exemption names not present in current mapping: %s", ", ".join(unresolved))

    candidate_ids = select_flipping_timeseries_candidates(
        generated_at,
        mapping,
        latest,
        five_minute,
        one_hour,
        exempt_ids,
        settings,
    )
    timeseries = {}
    failures = 0
    for item_id in candidate_ids:
        try:
            timeseries[item_id] = client.get_timeseries(item_id, "5m")
        except ApiError as exc:
            failures += 1
            LOGGER.warning("flipping timeseries unavailable item=%s: %s", item_id, exc)

    payload = build_public_flipping(
        generated_at,
        mapping,
        latest,
        five_minute,
        one_hour,
        exempt_ids,
        settings,
        timeseries,
    )
    payload["executionCandidatesRequested"] = len(candidate_ids)
    payload["executionCandidatesSucceeded"] = len(timeseries)
    payload["executionCandidatesFailed"] = failures

    write_json(data_dir / "flipping.json", payload)
    shutil.copy2(web_dir / "flipping.html", public_dir / "flipping.html")
    shutil.copy2(web_dir / "assets" / "flipping.js", assets_dir / "flipping.js")
    LOGGER.info(
        "hidden flipping desk: %s candidates, %s/%s execution histories",
        len(payload["items"]),
        len(timeseries),
        len(candidate_ids),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the unlisted OSRS Market Board flipping desk")
    parser.add_argument("--config", default="config")
    parser.add_argument("--public-dir", default="build/public-site")
    parser.add_argument("--web-dir", default="web")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        build_hidden_flipping_site(Path(args.config), Path(args.public_dir), Path(args.web_dir))
        return 0
    except (ApiError, OSError, ValueError, KeyError) as exc:
        LOGGER.error("flipping build failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
