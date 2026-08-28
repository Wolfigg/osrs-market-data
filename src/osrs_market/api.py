from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any

import requests

from .models import LatestPrice, MappingItem, TimeSeriesPoint

LOGGER = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class ApiError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ApiSettings:
    base_url: str
    user_agent: str
    request_spacing_ms: int = 250
    timeout_seconds: int = 20
    retries: int = 4


class MarketApiClient:
    """Small v1 client for the OSRS Wiki real-time prices API."""

    def __init__(self, settings: ApiSettings, session: requests.Session | None = None) -> None:
        if not settings.user_agent or settings.user_agent.lower().startswith("python-requests"):
            raise ValueError("a descriptive User-Agent is required")
        self.settings = settings
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": settings.user_agent, "Accept": "application/json"})
        self._last_timeseries_request_monotonic: float | None = None

    def get_mapping(self) -> dict[int, MappingItem]:
        payload = self._get_json("/mapping")
        if not isinstance(payload, list):
            raise ApiError("/mapping returned an unexpected response shape")
        items: dict[int, MappingItem] = {}
        for raw in payload:
            item = MappingItem.from_api(raw)
            items[item.id] = item
        if not items:
            raise ApiError("/mapping returned no items")
        return items

    def get_latest(self) -> dict[int, LatestPrice]:
        payload = self._get_json("/latest")
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise ApiError("/latest returned an unexpected response shape")
        result = {int(item_id): LatestPrice.from_api(raw) for item_id, raw in data.items()}
        if not result:
            raise ApiError("/latest returned no prices")
        return result

    def get_timeseries(self, item_id: int, timestep: str) -> list[TimeSeriesPoint]:
        if timestep not in {"5m", "1h", "6h", "24h"}:
            raise ValueError(f"unsupported timestep: {timestep}")
        self._throttle_timeseries()
        payload = self._get_json("/timeseries", params={"id": int(item_id), "timestep": timestep})
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise ApiError(f"timeseries item={item_id} timestep={timestep} returned an unexpected response shape")
        try:
            return [TimeSeriesPoint.from_api(raw) for raw in data]
        except (TypeError, ValueError) as exc:
            raise ApiError(f"invalid timeseries point for item={item_id} timestep={timestep}: {exc}") from exc

    def _throttle_timeseries(self) -> None:
        spacing = max(self.settings.request_spacing_ms, 0) / 1000.0
        if spacing <= 0:
            return
        now = time.monotonic()
        if self._last_timeseries_request_monotonic is not None:
            elapsed = now - self._last_timeseries_request_monotonic
            if elapsed < spacing:
                time.sleep(spacing - elapsed)
        self._last_timeseries_request_monotonic = time.monotonic()

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.settings.base_url.rstrip('/')}/{path.lstrip('/')}"
        attempts = max(int(self.settings.retries), 0) + 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                response = self.session.get(url, params=params, timeout=self.settings.timeout_seconds)
                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt == attempts - 1:
                        raise ApiError(f"GET {path} failed with HTTP {response.status_code}")
                    self._sleep_for_retry(response, attempt)
                    continue
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError, ApiError) as exc:
                last_error = exc
                if attempt == attempts - 1:
                    break
                LOGGER.warning("request failed path=%s attempt=%s/%s error=%s", path, attempt + 1, attempts, exc)
                self._sleep_for_retry(None, attempt)

        raise ApiError(f"GET {path} failed after {attempts} attempts: {last_error}") from last_error

    @staticmethod
    def _sleep_for_retry(response: requests.Response | None, attempt: int) -> None:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    time.sleep(max(float(retry_after), 0.0))
                    return
                except ValueError:
                    pass
        base = min(2**attempt, 8)
        time.sleep(base + random.uniform(0.0, 0.35))
