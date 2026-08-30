from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from .catalog_gap_v3 import (
    GUIDE_CHANGED,
    GUIDE_REMOVED,
    RATE_CHANGE_SUSPECTED,
    RECIPE_CHANGE_SUSPECTED,
    REQUIREMENT_CHANGE_SUSPECTED,
)

VALID = "VALID"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
UNRESOLVED = "UNRESOLVED"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()[:16]


def _source(method: dict[str, Any]) -> dict[str, Any]:
    source = deepcopy(method.get("source") or {})
    source.setdefault("url", method.get("reference"))
    audit = method.get("audit") or {}
    if audit.get("verified_at") is not None:
        source.setdefault("verifiedAt", audit.get("verified_at"))
    return source


def method_assumptions(method_id: str, method: dict[str, Any]) -> list[dict[str, Any]]:
    source = _source(method)
    recipe = {
        "inputs": method.get("inputs") or [],
        "outputs": method.get("outputs") or [],
        "fixedCostGpPerCycle": method.get("fixed_cost_gp_per_cycle", 0),
        "modifiers": method.get("modifiers") or [],
    }
    throughput = {
        "cyclesPerHour": method.get("cycles_per_hour"),
        "theoreticalCyclesPerHour": method.get("theoretical_cycles_per_hour"),
        "workflow": method.get("workflow") or {},
        "variants": [
            {
                "id": row.get("id"),
                "cyclesPerHour": (row.get("overrides") or {}).get("cycles_per_hour"),
            }
            for row in method.get("variants") or []
        ],
    }
    requirements = method.get("requirements") or {}
    model = method.get("model") or {}
    rows = [
        ("recipe", recipe),
        ("throughput", throughput),
        ("requirements", requirements),
        ("model", model),
    ]
    assumptions = []
    for kind, value in rows:
        assumptions.append({
            "id": f"{method_id}:{kind}",
            "methodId": method_id,
            "kind": kind,
            "fingerprint": _fingerprint(value),
            "value": deepcopy(value),
            "source": source,
            "status": VALID,
        })
    return assumptions


def build_assumption_registry(methods: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = [assumption for method_id, method in sorted(methods.items()) if method.get("enabled", True) is not False for assumption in method_assumptions(method_id, method)]
    sourced = sum(bool((row.get("source") or {}).get("url")) for row in rows)
    verified = sum(bool((row.get("source") or {}).get("verifiedAt")) for row in rows)
    return {
        "schemaVersion": 1,
        "methodCount": len({row["methodId"] for row in rows}),
        "assumptionCount": len(rows),
        "sourceCoveragePct": round(100 * sourced / len(rows), 1) if rows else 100.0,
        "verificationCoveragePct": round(100 * verified / len(rows), 1) if rows else 100.0,
        "assumptions": rows,
    }


def _affected_kinds(finding: dict[str, Any]) -> set[str]:
    classifications = set(finding.get("classifications") or [])
    kinds: set[str] = set()
    if RECIPE_CHANGE_SUSPECTED in classifications:
        kinds.add("recipe")
    if RATE_CHANGE_SUSPECTED in classifications:
        kinds.update(("throughput", "model"))
    if REQUIREMENT_CHANGE_SUSPECTED in classifications:
        kinds.add("requirements")
    if finding.get("status") == GUIDE_CHANGED and not kinds:
        kinds.add("model")
    return kinds


def apply_impact_to_assumptions(registry: dict[str, Any], impact_report: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(registry)
    by_method: dict[str, list[dict[str, Any]]] = {}
    for row in result.get("assumptions") or []:
        by_method.setdefault(str(row.get("methodId")), []).append(row)

    findings_by_method: dict[str, list[dict[str, Any]]] = {}
    for finding in impact_report.get("findings") or []:
        for method_id in finding.get("potentiallyAffectedMethods") or []:
            findings_by_method.setdefault(str(method_id), []).append(finding)

    for method_id, findings in findings_by_method.items():
        rows = by_method.get(method_id, [])
        for finding in findings:
            if finding.get("status") == GUIDE_REMOVED:
                for row in rows:
                    row["status"] = UNRESOLVED
                    row.setdefault("drift", []).append({"guide": finding.get("guide"), "reason": GUIDE_REMOVED})
                continue
            affected = _affected_kinds(finding)
            for row in rows:
                if row.get("kind") in affected and row.get("status") != UNRESOLVED:
                    row["status"] = REVIEW_REQUIRED
                    row.setdefault("drift", []).append({
                        "guide": finding.get("guide"),
                        "reason": "assumption_drift_suspected",
                        "classifications": list(finding.get("classifications") or []),
                        "changedSections": list(finding.get("changedSections") or []),
                    })

    counts = {VALID: 0, REVIEW_REQUIRED: 0, UNRESOLVED: 0}
    for row in result.get("assumptions") or []:
        counts[str(row.get("status") or VALID)] = counts.get(str(row.get("status") or VALID), 0) + 1
    result["statusCounts"] = counts
    result["reviewRequired"] = counts[REVIEW_REQUIRED] > 0 or counts[UNRESOLVED] > 0
    result["autoPromote"] = False
    return result


def build_catalogue_quality_report(methods: dict[str, dict[str, Any]], assumption_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    enabled = {method_id: method for method_id, method in methods.items() if method.get("enabled", True) is not False}
    registry = assumption_registry or build_assumption_registry(enabled)
    modelled = sum(bool(method.get("model")) for method in enabled.values())
    with_variants = sum(bool(method.get("variants") or method.get("modifiers")) for method in enabled.values())
    with_verified_audit = sum((method.get("audit") or {}).get("status") == "verified" for method in enabled.values())
    statuses = registry.get("statusCounts") or {VALID: registry.get("assumptionCount", 0), REVIEW_REQUIRED: 0, UNRESOLVED: 0}
    total = len(enabled)
    return {
        "schemaVersion": 1,
        "methodCount": total,
        "modelledMethodPct": round(100 * modelled / total, 1) if total else 100.0,
        "variantOrModifierMethodPct": round(100 * with_variants / total, 1) if total else 100.0,
        "verifiedAuditPct": round(100 * with_verified_audit / total, 1) if total else 100.0,
        "assumptionSourceCoveragePct": registry.get("sourceCoveragePct"),
        "assumptionVerificationCoveragePct": registry.get("verificationCoveragePct"),
        "assumptionStatusCounts": statuses,
        "reviewRequired": bool(registry.get("reviewRequired")),
        "coverageIsNotQuality": True,
    }
