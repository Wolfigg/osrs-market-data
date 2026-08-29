from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests

API_URL = "https://oldschool.runescape.wiki/api.php"
CATEGORY = "Category:Money making guides"


def _request(session: requests.Session, params: dict[str, Any], user_agent: str) -> dict[str, Any]:
    response = session.get(API_URL, params=params, headers={"User-Agent": user_agent, "Accept": "application/json"}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict): raise ValueError("Wiki API returned an unexpected payload")
    return payload


def discover_money_making_guides(user_agent: str, session: requests.Session | None = None) -> list[dict[str, Any]]:
    """Discover guide pages and revision IDs without trusting page structure.

    The output is metadata only. No discovered page becomes a production method.
    """
    session = session or requests.Session()
    titles: list[str] = []
    cmcontinue: str | None = None
    while True:
        params: dict[str, Any] = {"action": "query", "format": "json", "list": "categorymembers", "cmtitle": CATEGORY, "cmnamespace": 0, "cmlimit": "max", "cmtype": "page"}
        if cmcontinue: params["cmcontinue"] = cmcontinue
        payload = _request(session, params, user_agent)
        titles.extend(str(row["title"]) for row in ((payload.get("query") or {}).get("categorymembers") or []))
        cmcontinue = ((payload.get("continue") or {}).get("cmcontinue"))
        if not cmcontinue: break
    rows: list[dict[str, Any]] = []
    for offset in range(0, len(titles), 50):
        batch = titles[offset:offset + 50]
        payload = _request(session, {"action": "query", "format": "json", "prop": "revisions|info", "rvprop": "ids|timestamp", "titles": "|".join(batch)}, user_agent)
        for page in ((payload.get("query") or {}).get("pages") or {}).values():
            revisions = page.get("revisions") or []
            revision = revisions[0] if revisions else {}
            title = str(page.get("title") or "")
            rows.append({"pageId": int(page.get("pageid") or 0), "title": title, "revisionId": int(revision.get("revid") or 0), "revisionTimestamp": revision.get("timestamp"), "url": "https://oldschool.runescape.wiki/w/" + title.replace(" ", "_")})
    return sorted(rows, key=lambda row: row["title"].casefold())


def build_discovery_audit(discovered: list[dict[str, Any]], baseline: dict[str, Any] | None) -> dict[str, Any]:
    baseline_rows = {str(row.get("title")): row for row in ((baseline or {}).get("pages") or [])}
    current = {str(row["title"]): row for row in discovered}
    findings: list[dict[str, Any]] = []
    for title, row in current.items():
        old = baseline_rows.get(title)
        if old is None:
            findings.append({"status": "new", **row, "reviewRequired": True})
        elif int(old.get("revisionId") or 0) != int(row.get("revisionId") or 0):
            findings.append({"status": "changed", **row, "previousRevisionId": old.get("revisionId"), "reviewRequired": True})
    for title, row in baseline_rows.items():
        if title not in current:
            findings.append({"status": "removed", **row, "reviewRequired": True})
    digest = hashlib.sha256(json.dumps(discovered, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"schemaVersion": 1, "generatedAt": int(time.time()), "category": CATEGORY, "trustPolicy": "Discovery is advisory only. New or changed Wiki pages require human mechanical review before catalogue inclusion or assumption changes.", "baselinePresent": baseline is not None, "pageCount": len(discovered), "findingCount": len(findings), "requiresReview": bool(findings), "snapshotSha256": digest, "findings": sorted(findings, key=lambda row: (row["status"], str(row.get("title")))), "pages": discovered}


def load_snapshot(path: str | Path) -> dict[str, Any] | None:
    source = Path(path)
    if not source.exists(): return None
    return json.loads(source.read_text(encoding="utf-8"))


def write_audit(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
