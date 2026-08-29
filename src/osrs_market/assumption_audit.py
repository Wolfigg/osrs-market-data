from __future__ import annotations

from typing import Any


def compare_assumption(stored: dict[str, Any], observed: dict[str, Any], *, relative_tolerance: float = 0.05) -> dict[str, Any]:
    key = str(stored.get("key") or observed.get("key") or "unknown")
    expected = stored.get("value")
    actual = observed.get("value")
    status = "VALID"
    difference = None
    difference_pct = None
    reason = "Values match within tolerance."

    if actual is None:
        status = "UNRESOLVED"
        reason = "No observed value was extracted from the source."
    elif expected is None:
        status = "REVIEW_REQUIRED"
        reason = "Catalogue has no stored value for an observed assumption."
    elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        difference = float(actual) - float(expected)
        denominator = abs(float(expected))
        difference_pct = difference / denominator * 100.0 if denominator > 0 else (0.0 if difference == 0 else None)
        if difference_pct is None or abs(difference_pct) > relative_tolerance * 100.0:
            status = "REVIEW_REQUIRED"
            reason = "Observed numeric value differs from the catalogue beyond tolerance."
    elif str(expected).strip().casefold() != str(actual).strip().casefold():
        status = "REVIEW_REQUIRED"
        reason = "Observed value differs from the catalogue."

    return {
        "key": key,
        "status": status,
        "storedValue": expected,
        "observedValue": actual,
        "difference": difference,
        "differencePct": difference_pct,
        "sourceUrl": observed.get("sourceUrl") or stored.get("sourceUrl"),
        "sourceRevision": observed.get("sourceRevision"),
        "reason": reason,
    }


def build_assumption_audit(method_id: str, stored: list[dict[str, Any]], observed: list[dict[str, Any]], *, relative_tolerance: float = 0.05) -> dict[str, Any]:
    observed_by_key = {str(row.get("key")): row for row in observed}
    stored_by_key = {str(row.get("key")): row for row in stored}
    keys = sorted(set(stored_by_key) | set(observed_by_key))
    findings = [compare_assumption(stored_by_key.get(key, {"key": key}), observed_by_key.get(key, {"key": key}), relative_tolerance=relative_tolerance) for key in keys]
    review = [row for row in findings if row["status"] == "REVIEW_REQUIRED"]
    unresolved = [row for row in findings if row["status"] == "UNRESOLVED"]
    return {
        "schemaVersion": 1,
        "methodId": method_id,
        "status": "REVIEW_REQUIRED" if review else ("UNRESOLVED" if unresolved else "VALID"),
        "findingCount": len(findings),
        "reviewRequiredCount": len(review),
        "unresolvedCount": len(unresolved),
        "findings": findings,
        "policy": "Source changes are advisory. Production catalogue assumptions require human review before replacement.",
    }
