from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MappingItem:
    id: int
    name: str
    examine: str | None = None
    members: bool = False
    lowalch: int | None = None
    highalch: int | None = None
    value: int | None = None
    limit: int | None = None
    icon: str | None = None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "MappingItem":
        if "id" not in raw or "name" not in raw:
            raise ValueError("mapping item missing id or name")
        return cls(
            id=int(raw["id"]),
            name=str(raw["name"]),
            examine=raw.get("examine"),
            members=bool(raw.get("members", False)),
            lowalch=_optional_int(raw.get("lowalch")),
            highalch=_optional_int(raw.get("highalch")),
            value=_optional_int(raw.get("value")),
            limit=_optional_int(raw.get("limit")),
            icon=raw.get("icon"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LatestPrice:
    high: int | None
    high_time: int | None
    low: int | None
    low_time: int | None

    @classmethod
    def from_api(cls, raw: dict[str, Any] | None) -> "LatestPrice":
        raw = raw or {}
        return cls(
            high=_optional_int(raw.get("high")),
            high_time=_optional_int(raw.get("highTime")),
            low=_optional_int(raw.get("low")),
            low_time=_optional_int(raw.get("lowTime")),
        )

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "high": self.high,
            "highTime": self.high_time,
            "low": self.low,
            "lowTime": self.low_time,
        }


@dataclass(frozen=True, slots=True)
class TimeSeriesPoint:
    timestamp: int
    avg_high_price: int | None
    avg_low_price: int | None
    high_price_volume: int
    low_price_volume: int

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "TimeSeriesPoint":
        if "timestamp" not in raw:
            raise ValueError("timeseries point missing timestamp")
        return cls(
            timestamp=int(raw["timestamp"]),
            avg_high_price=_optional_int(raw.get("avgHighPrice")),
            avg_low_price=_optional_int(raw.get("avgLowPrice")),
            high_price_volume=_nonnegative_int(raw.get("highPriceVolume", 0)),
            low_price_volume=_nonnegative_int(raw.get("lowPriceVolume", 0)),
        )

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "avgHighPrice": self.avg_high_price,
            "avgLowPrice": self.avg_low_price,
            "highPriceVolume": self.high_price_volume,
            "lowPriceVolume": self.low_price_volume,
        }


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _nonnegative_int(value: Any) -> int:
    parsed = int(value or 0)
    if parsed < 0:
        raise ValueError("volume cannot be negative")
    return parsed
