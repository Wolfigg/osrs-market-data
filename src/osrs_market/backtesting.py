from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class RecommendationSnapshot:
    generated_at: datetime
    method_id: str
    current_profit: float | None
    expected_profit: float | None
    conservative_profit: float | None
    buy_price_assumption: dict[str, float]
    sell_price_assumption: dict[str, float]
    liquidity_score: float | None
    confidence_score: float | None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["generated_at"] = self.generated_at.astimezone(timezone.utc).isoformat()
        return payload


@dataclass(frozen=True, slots=True)
class BacktestResult:
    method_id: str
    horizon_hours: float
    expected_forecast_error_gp_per_hour: float | None
    conservative_survived: bool | None
    margin_survived: bool | None
    ranking_stable: bool | None = None


def forecast_error(predicted: float | None, realised: float | None) -> float | None:
    if predicted is None or realised is None:
        return None
    return float(realised) - float(predicted)


def evaluate_snapshot(
    snapshot: RecommendationSnapshot,
    *,
    realised_profit_gp_per_hour: float | None,
    horizon_hours: float,
    realised_rank: int | None = None,
    original_rank: int | None = None,
    rank_tolerance: int = 2,
) -> BacktestResult:
    realised = None if realised_profit_gp_per_hour is None else float(realised_profit_gp_per_hour)
    conservative_survived = None
    margin_survived = None
    if realised is not None:
        conservative_survived = snapshot.conservative_profit is None or realised >= float(snapshot.conservative_profit)
        margin_survived = realised > 0
    ranking_stable = None
    if realised_rank is not None and original_rank is not None:
        ranking_stable = abs(int(realised_rank) - int(original_rank)) <= max(0, int(rank_tolerance))
    return BacktestResult(
        method_id=snapshot.method_id,
        horizon_hours=float(horizon_hours),
        expected_forecast_error_gp_per_hour=forecast_error(snapshot.expected_profit, realised),
        conservative_survived=conservative_survived,
        margin_survived=margin_survived,
        ranking_stable=ranking_stable,
    )


def summarise_backtests(results: list[BacktestResult]) -> dict[str, Any]:
    errors = [abs(row.expected_forecast_error_gp_per_hour) for row in results if row.expected_forecast_error_gp_per_hour is not None]
    conservative = [row.conservative_survived for row in results if row.conservative_survived is not None]
    margins = [row.margin_survived for row in results if row.margin_survived is not None]
    rankings = [row.ranking_stable for row in results if row.ranking_stable is not None]
    return {
        "sampleCount": len(results),
        "meanAbsoluteForecastErrorGpPerHour": (sum(errors) / len(errors)) if errors else None,
        "conservativeSurvivalRate": (sum(bool(x) for x in conservative) / len(conservative)) if conservative else None,
        "marginSurvivalRate": (sum(bool(x) for x in margins) / len(margins)) if margins else None,
        "rankingStabilityRate": (sum(bool(x) for x in rankings) / len(rankings)) if rankings else None,
    }
