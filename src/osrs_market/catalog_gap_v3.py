from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import unquote, urlparse


NEW_GUIDE = "NEW_GUIDE"
GUIDE_CHANGED = "GUIDE_CHANGED"
GUIDE_REMOVED = "GUIDE_REMOVED"
CATALOGUE_NO_MATCH = "CATALOGUE_NO_MATCH"
CATALOGUE_SOURCE_STALE = "CATALOGUE_SOURCE_STALE"
RECIPE_CHANGE_SUSPECTED = "RECIPE_CHANGE_SUSPECTED"
RATE_CHANGE_SUSPECTED = "RATE_CHANGE_SUSPECTED"
REQUIREMENT_CHANGE_SUSPECTED = "REQUIREMENT_CHANGE_SUSPECTED"


def _wiki_title_from_url(url: str) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    marker = "/w/"
    if marker not in parsed.path:
        return None
    title = parsed.path.split(marker, 1)[1]
    return unquote(title).replace("_", " ").casefold()


def _method_index(methods: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for method_id, method in methods.items():
        urls = [str(method.get("reference") or "")]
        source = method.get("source") or {}
        if source.get("url"):
            urls.append(str(source["url"]))
        audit = method.get("audit") or {}
        if audit.get("source"):
            urls.append(str(audit["source"]))
        for url in urls:
            title = _wiki_title_from_url(url)
            if title:
                index[title].append(method_id)
    return {title: sorted(set(ids)) for title, ids in index.items()}


def _suspected_classifications(changed_sections: list[str]) -> list[str]:
    joined = " ".join(changed_sections).casefold()
    classifications: list[str] = []
    if any(token in joined for token in ("product", "input", "output", "recipe", "material", "ingredient")):
        classifications.append(RECIPE_CHANGE_SUSPECTED)
    if any(token in joined for token in ("profit", "rate", "rates", "method", "experience", "output")):
        classifications.append(RATE_CHANGE_SUSPECTED)
    if any(token in joined for token in ("requirement", "requirements", "quest", "skill", "equipment")):
        classifications.append(REQUIREMENT_CHANGE_SUSPECTED)
    return classifications


def build_catalogue_impact_report(
    discovered: list[dict[str, Any]],
    baseline: dict[str, Any] | None,
    methods: dict[str, dict[str, Any]],
    *,
    changed_sections: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    baseline_rows = {str(row.get("title")): row for row in ((baseline or {}).get("pages") or [])}
    current = {str(row.get("title")): row for row in discovered}
    index = _method_index(methods)
    section_map = changed_sections or {}
    findings: list[dict[str, Any]] = []

    all_titles = sorted(set(baseline_rows) | set(current), key=str.casefold)
    for title in all_titles:
        old = baseline_rows.get(title)
        new = current.get(title)
        if old is None:
            primary = NEW_GUIDE
        elif new is None:
            primary = GUIDE_REMOVED
        elif int(old.get("revisionId") or 0) != int(new.get("revisionId") or 0):
            primary = GUIDE_CHANGED
        else:
            continue

        affected = index.get(title.casefold(), [])
        sections = list(section_map.get(title) or [])
        classifications = [primary]
        if not affected:
            classifications.append(CATALOGUE_NO_MATCH)
        if primary == GUIDE_CHANGED:
            classifications.extend(_suspected_classifications(sections))
            if affected:
                classifications.append(CATALOGUE_SOURCE_STALE)

        priority = "HIGH" if any(value in classifications for value in (RECIPE_CHANGE_SUSPECTED, RATE_CHANGE_SUSPECTED, REQUIREMENT_CHANGE_SUSPECTED)) else ("MEDIUM" if affected else "LOW")
        row = new or old or {}
        findings.append({
            "guide": title,
            "status": primary,
            "classifications": list(dict.fromkeys(classifications)),
            "oldRevisionId": old.get("revisionId") if old else None,
            "newRevisionId": new.get("revisionId") if new else None,
            "potentiallyAffectedMethods": affected,
            "changedSections": sections,
            "priority": priority,
            "reviewRequired": True,
            "autoPromote": False,
            "url": row.get("url"),
        })

    return {
        "schemaVersion": 3,
        "reviewRequired": bool(findings),
        "autoPromote": False,
        "trustWikiStructure": False,
        "findingCount": len(findings),
        "findings": findings,
    }
