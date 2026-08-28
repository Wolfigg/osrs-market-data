from __future__ import annotations

from dataclasses import dataclass

from .models import TimeSeriesPoint


@dataclass(frozen=True, slots=True)
class WindowSpec:
    key: str
    duration_seconds: int
    source_timestep: str
    source_bucket_seconds: int


WINDOW_SPECS: dict[str, WindowSpec] = {
    "6h": WindowSpec("6h", 6 * 3600, "5m", 5 * 60),
    "24h": WindowSpec("24h", 24 * 3600, "5m", 5 * 60),
    "7d": WindowSpec("7d", 7 * 24 * 3600, "1h", 3600),
    "30d": WindowSpec("30d", 30 * 24 * 3600, "6h", 6 * 3600),
    "6m": WindowSpec("6m", 182 * 24 * 3600, "24h", 24 * 3600),
    "1y": WindowSpec("1y", 365 * 24 * 3600, "24h", 24 * 3600),
}


def normalize_points(points: list[TimeSeriesPoint]) -> list[TimeSeriesPoint]:
    """Sort and deduplicate by timestamp. Later input wins on duplicate timestamps."""
    by_timestamp: dict[int, TimeSeriesPoint] = {}
    for point in points:
        by_timestamp[point.timestamp] = point
    return [by_timestamp[timestamp] for timestamp in sorted(by_timestamp)]


def slice_window(points: list[TimeSeriesPoint], generated_at: int, duration_seconds: int) -> list[TimeSeriesPoint]:
    cutoff = int(generated_at) - int(duration_seconds)
    return [point for point in normalize_points(points) if cutoff <= point.timestamp <= generated_at]


def build_windows(
    series: dict[str, list[TimeSeriesPoint]],
    generated_at: int,
) -> dict[str, tuple[WindowSpec, list[TimeSeriesPoint]]]:
    output: dict[str, tuple[WindowSpec, list[TimeSeriesPoint]]] = {}
    for key, spec in WINDOW_SPECS.items():
        output[key] = (spec, slice_window(series.get(spec.source_timestep, []), generated_at, spec.duration_seconds))
    return output
