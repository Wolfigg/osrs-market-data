from __future__ import annotations

import argparse
import os
from pathlib import Path

from osrs_market.catalog_gap_v3 import build_catalogue_impact_report
from osrs_market.catalogue_intelligence import apply_impact_to_assumptions, build_assumption_registry, build_catalogue_quality_report
from osrs_market.config import load_yaml
from osrs_market.wiki_discovery import build_discovery_audit, discover_money_making_guides, load_snapshot, write_audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit OSRS Wiki money-making guide discovery metadata")
    parser.add_argument("--baseline", default="config/wiki_money_making_snapshot.json")
    parser.add_argument("--output", default="build/wiki-catalogue-audit.json")
    parser.add_argument("--impact-output", default="build/wiki-catalogue-impact-v3.json")
    parser.add_argument("--assumptions-output", default="build/catalogue-assumption-drift.json")
    parser.add_argument("--quality-output", default="build/catalogue-quality.json")
    parser.add_argument("--config", default="config/methods.yaml")
    args = parser.parse_args()
    user_agent = os.environ.get("OSRS_MARKET_USER_AGENT", "osrs-market-data catalogue audit - github.com/Wolfigg/osrs-market-data")
    baseline = load_snapshot(Path(args.baseline))
    discovered = discover_money_making_guides(user_agent)
    audit = build_discovery_audit(discovered, baseline)
    write_audit(Path(args.output), audit)

    methods = load_yaml(Path(args.config)).get("methods", {})
    impact = build_catalogue_impact_report(discovered, baseline, methods)
    write_audit(Path(args.impact_output), impact)

    registry = build_assumption_registry(methods)
    drift = apply_impact_to_assumptions(registry, impact)
    quality = build_catalogue_quality_report(methods, drift)
    write_audit(Path(args.assumptions_output), drift)
    write_audit(Path(args.quality_output), quality)
    print(
        f"Wiki catalogue audit: {audit['pageCount']} pages, {audit['findingCount']} review findings; "
        f"impact findings: {impact['findingCount']}; assumption review required: {drift['reviewRequired']}"
    )
    return 0


if __name__ == "__main__": raise SystemExit(main())
