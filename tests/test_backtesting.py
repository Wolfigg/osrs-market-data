from datetime import datetime, timezone

import pytest

from osrs_market.backtesting import RecommendationSnapshot, evaluate_snapshot, summarise_backtests


def snapshot():
    return RecommendationSnapshot(
        generated_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        method_id="method",
        current_profit=500_000,
        expected_profit=450_000,
        conservative_profit=300_000,
        buy_price_assumption={"Input": 100},
        sell_price_assumption={"Output": 200},
        liquidity_score=80,
        confidence_score=85,
    )


def test_snapshot_backtest_measures_error_margin_and_ranking():
    result = evaluate_snapshot(
        snapshot(),
        realised_profit_gp_per_hour=400_000,
        horizon_hours=4,
        realised_rank=3,
        original_rank=2,
    )
    assert result.expected_forecast_error_gp_per_hour == -50_000
    assert result.conservative_survived is True
    assert result.margin_survived is True
    assert result.ranking_stable is True


def test_backtest_summary_keeps_explicit_metrics():
    rows = [
        evaluate_snapshot(snapshot(), realised_profit_gp_per_hour=400_000, horizon_hours=1),
        evaluate_snapshot(snapshot(), realised_profit_gp_per_hour=200_000, horizon_hours=4),
    ]
    summary = summarise_backtests(rows)
    assert summary["sampleCount"] == 2
    assert summary["meanAbsoluteForecastErrorGpPerHour"] == pytest.approx(150_000)
    assert summary["conservativeSurvivalRate"] == pytest.approx(0.5)
    assert summary["marginSurvivalRate"] == pytest.approx(1.0)
