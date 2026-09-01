from __future__ import annotations

from typing import Any


def detect_method_anomalies(method: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic publication diagnostics for one public method."""
    method_id = str(method.get("methodId") or "unknown")
    rows: list[dict[str, Any]] = []

    def add(severity: str, rule: str, reason: str, observed: dict[str, Any], expected: dict[str, Any]) -> None:
        rows.append({"methodId": method_id, "severity": severity, "rule": rule, "reason": reason, "observed": observed, "expected": expected})

    current = method.get("current") or {}
    inputs = method.get("inputs") or []
    missing_inputs = [row.get("name") or row.get("itemId") for row in inputs if row.get("price") is None]
    if current.get("valid") and missing_inputs:
        add("error", "missing_input_price", "A valid calculation cannot contain a zero/missing GE input price.", {"items": missing_inputs}, {"missingPrices": 0})

    mechanics = method.get("mechanics") or {}
    mechanical = float(mechanics.get("cyclesPerHour") or 0)
    if mechanical > 120_000:
        add("error", "impossible_cycle_rate", "Configured throughput exceeds the global defensive ceiling.", {"cyclesPerHour": mechanical}, {"maximumCyclesPerHour": 120_000})

    capacity = method.get("marketCapacity") or {}
    executable = float(capacity.get("expectedExecutableCyclesPerHour") or capacity.get("cyclesPerHour") or 0)
    supported = capacity.get("marketSupportedCyclesPerHour")
    if supported is not None and executable > float(supported) + 1e-9:
        add("error", "capacity_exceeded", "Expected executable throughput exceeds observed directional market support.", {"expectedExecutableCyclesPerHour": executable}, {"maximum": float(supported)})

    scenarios = method.get("scenarios") or {}
    expected_gp = scenarios.get("expectedGpPerHour")
    unconstrained = (method.get("economics") or {}).get("unconstrainedExpectedGpPerHour")
    if expected_gp is not None and unconstrained is not None and abs(float(expected_gp)) > abs(float(unconstrained)) + 1e-6:
        add("error", "expected_profit_amplified", "Market capacity must not increase expected profit.", {"expectedGpPerHour": expected_gp}, {"maximumAbsoluteGpPerHour": abs(float(unconstrained))})

    history = method.get("history") or {}
    if str((method.get("stability") or {}).get("state")) == "stable" and not any(value is not None for value in history.values()):
        add("warning", "stable_without_history", "Stable classification has no historical reference.", {"history": history}, {"minimumHistoricalReferences": 1})
    return rows


def publication_errors(anomalies: list[dict[str, Any]]) -> bool:
    return any(row.get("severity") == "error" for row in anomalies)
