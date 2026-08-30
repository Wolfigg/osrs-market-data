from __future__ import annotations

import argparse
import os
from pathlib import Path

from osrs_market.wiki_discovery import build_discovery_audit, discover_money_making_guides, load_snapshot, write_audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit OSRS Wiki money-making guide discovery metadata")
    parser.add_argument("--baseline", default=".wiki-audit-state/wiki_money_making_snapshot.json")
    parser.add_argument("--output", default="build/wiki-catalogue-audit.json")
    parser.add_argument("--snapshot-out", default=".wiki-audit-state/wiki_money_making_snapshot.json")
    args = parser.parse_args()
    user_agent = os.environ.get("OSRS_MARKET_USER_AGENT", "osrs-market-data catalogue audit - github.com/Wolfigg/osrs-market-data")
    discovered = discover_money_making_guides(user_agent)
    audit = build_discovery_audit(discovered, load_snapshot(Path(args.baseline)))
    write_audit(Path(args.output), audit)
    # Persist metadata only. This state is used solely to detect revision changes
    # on the next scheduled run and never mutates the production catalogue.
    write_audit(Path(args.snapshot_out), {"schemaVersion": 1, "pages": discovered})
    print(f"Wiki catalogue audit: {audit['pageCount']} pages, {audit['findingCount']} review findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
