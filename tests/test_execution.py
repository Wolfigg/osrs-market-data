from copy import deepcopy

import pytest

from osrs_market.execution import execution_quote
from osrs_market.methods_v2 import evaluate_method
from osrs_market.public_models_v2 import build_public_afk, _apply_market_capacity
from test_methods import SETTINGS, record

NOW = 7200


def market(high=340, low=330, volume=10000):
    row = record(1, "Example", high, low, limit=40000)
    row["current"].update(highTime=NOW-60, lowTime=NOW-90)
    row["executionPoints"] = [
        {"timestamp": NOW - age, "avgHighPrice": high, "avgLowPrice": low,
         "highPriceVolume": volume, "lowPriceVolume": volume}
        for age in range(300, 3601, 300)
    ]
    for window in row["windows"].values():
        window.update(highVolume=1000000, lowVolume=1000000)
    return row


def test_thin_spikes_have_only_their_volume_weight_and_latest_is_preserved():
    row = market()
    row["current"].update(high=361, low=310)
    row["executionPoints"][0].update(avgHighPrice=361, avgLowPrice=310, highPriceVolume=15, lowPriceVolume=15)
    buy = execution_quote(row, "high", 1000, NOW)
    sell = execution_quote(row, "low", 1000, NOW)
    assert buy["latestObserved"] == 361
    assert buy["directionalVwap"] == pytest.approx((340 * 50000 + 361 * 15) / 50015)
    assert buy["expectedExecutable"] == buy["conservative"] == 341
    assert sell["expectedExecutable"] == 329
    assert sell["conservative"] <= sell["expectedExecutable"]
    assert buy["latestObservedAt"] == NOW - 60


def test_sustained_high_volume_price_change_moves_expected_and_conservative():
    row = market()
    row["executionPoints"][0].update(avgHighPrice=400, highPriceVolume=50000)
    quote = execution_quote(row, "high", 1000, NOW)
    assert quote["expectedExecutable"] == 370
    assert quote["conservative"] == 400


def test_window_switch_at_required_hourly_quantity_boundary():
    row = market(volume=100)
    assert execution_quote(row, "high", 1200, NOW)["windowSeconds"] == 1800
    quote = execution_quote(row, "high", 1201, NOW)
    assert quote["windowSeconds"] == 3600
    assert quote["directionalVolume"] == 1200
    assert quote["requiredSharePct"] > 100


@pytest.mark.parametrize("kind", ["missing", "stale", "insufficient", "zero", "missing_price"])
def test_unusable_direction_does_not_fall_back_to_latest(kind):
    row = market()
    if kind == "missing":
        row.pop("executionPoints")
    elif kind == "stale":
        row["executionPoints"] = row["executionPoints"][4:]
    elif kind == "insufficient":
        row["executionPoints"] = row["executionPoints"][:2]
    else:
        for p in row["executionPoints"]:
            p["highPriceVolume" if kind == "zero" else "avgHighPrice"] = 0 if kind == "zero" else None
    quote = execution_quote(row, "high", 100, NOW)
    assert quote["expectedExecutable"] is None
    assert quote["conservative"] is None
    assert quote["latestObserved"] == 340
    if kind in {"zero", "missing_price"}:
        assert execution_quote(row, "low", 100, NOW)["expectedExecutable"] == 330


def test_completed_bucket_freshness_and_duplicate_boundaries():
    row = market()
    row["executionPoints"] = row["executionPoints"][3:]
    assert execution_quote(row, "high", 100, NOW)["freshness"] == "fresh"
    assert execution_quote(row, "high", 100, NOW + 1)["freshness"] == "stale"
    row = market()
    row["executionPoints"] += [dict(row["executionPoints"][0]), {**row["executionPoints"][0], "timestamp": NOW - 299}, {**row["executionPoints"][0], "timestamp": NOW + 300}]
    assert execution_quote(row, "high", 100, NOW)["directionalVolume"] == 60000


def test_public_headline_uses_execution_prices_tax_and_recent_capacity():
    records = {1: market(), 2: market(high=510, low=500)}
    records[1]["current"]["high"] = 361
    method = {"name": "Processing", "cycles_per_hour": 100,
              "inputs": [{"item_id": 1}], "outputs": [{"item_id": 2}],
              "fixed_cost_gp_per_cycle": 5, "afk": {"interval_seconds": 60}}
    rows = evaluate_method("example", method, records, set(), SETTINGS, NOW)
    payload = build_public_afk(NOW, rows)["methods"][0]
    assert payload["current"]["gpPerHour"] == (500 - 10 - 361 - 5) * 100
    assert payload["scenarios"]["expectedGpPerHour"] == (500 - 10 - 340 - 5) * 100
    assert payload["scenarios"]["conservativeGpPerHour"] <= payload["scenarios"]["expectedGpPerHour"]
    assert payload["executionPrices"]["inputs"][0]["latestObserved"] == 361
    assert payload["liquidity"]["inputs"][0]["directionalVolume1h"] == 120000
    assert payload["executionEconomics"]["expected"]["geTaxGpPerCycle"] == 10
    records[1].pop("executionPoints")
    payload = build_public_afk(NOW, evaluate_method("example", method, records, set(), SETTINGS, NOW))["methods"][0]
    assert payload["scenarios"]["expectedGpPerHour"] is None
    assert payload["current"]["valid"]


def test_capacity_applies_ge_limit_once_and_recent_flow_can_limit_further():
    method = {"mechanics": {"cyclesPerHour": 100, "cyclesPerHourByBuyLimits": 50},
              "scenarios": {"expectedGpPerHour": 500, "conservativeGpPerHour": 400},
              "liquidity": {"outputs": [{"name": "Output", "unitsPerHour": 100,
                              "directionalVolume1h": 100000, "directionalVolume24h": 2400000}]},
              "fillConfidence": {"score": 95}, "stability": {"state": "stable"}}
    thin = deepcopy(method)
    _apply_market_capacity(method)
    assert method["scenarios"]["expectedGpPerHour"] == 500
    thin["liquidity"]["outputs"][0]["directionalVolume1h"] = 100
    _apply_market_capacity(thin)
    assert thin["marketCapacity"]["cyclesPerHour"] == 25
    assert thin["scenarios"]["expectedGpPerHour"] == 250


def test_execution_collection_reuses_history_requests_and_failure_is_missing():
    from osrs_market.api import ApiError
    from osrs_market.cli import SeriesCollector, CollectionStats, _refresh_execution
    from osrs_market.models import TimeSeriesPoint

    class Client:
        calls = []

        def get_timeseries(self, item_id, timestep):
            self.calls.append((item_id, timestep))
            if item_id == 2:
                raise ApiError("unavailable")
            return [TimeSeriesPoint.from_api(p) for p in market()["executionPoints"]]

    client = Client()
    collector = SeriesCollector(client, CollectionStats())
    collector.get(1, "5m")
    records = {1: {}, 2: {}}
    _refresh_execution({1, 2}, records, collector, NOW)
    assert client.calls == [(1, "5m"), (2, "5m")]
    assert len(records[1]["executionPoints"]) == 12
    assert records[2]["executionPoints"] == []


def test_probabilistic_conservative_holds_price_window_and_arithmetic():
    records = {1: market(), 2: market(510, 500, volume=10)}
    for point in records[2]["executionPoints"][:6]:
        point["avgLowPrice"] = 1000
    method = {"name": "Variable output", "cycles_per_hour": 100,
              "inputs": [{"item_id": 1}],
              "outputs": [{"item_id": 2, "quantity_expected": 2, "quantity_minimum": 1}]}
    rows = evaluate_method("variable", method, records, set(), SETTINGS, NOW)
    expected = next(row for row in rows if row["scenario"] == "EXPECTED_EXECUTION")
    conservative = next(row for row in rows if row["scenario"] == "CONSERVATIVE_EXECUTION")
    assert expected["outputs"][0]["execution"]["windowSeconds"] == 3600
    assert conservative["outputs"][0]["execution"]["windowSeconds"] == 3600
    assert conservative["economics"]["profitGpPerCycle"] <= expected["economics"]["profitGpPerCycle"]
    assert conservative["economics"]["outputGrossGeGpPerCycle"] == conservative["outputs"][0]["gePrice"]


@pytest.mark.parametrize("output_price", [100, 346, 500])
def test_conservative_order_for_losses_zero_and_profit(output_price):
    records = {1: market(), 2: market(output_price, output_price)}
    method = {"name": "Boundary", "cycles_per_hour": 10,
              "inputs": [{"item_id": 1}], "outputs": [{"item_id": 2}]}
    result = build_public_afk(NOW, evaluate_method("boundary", method, records, set(), SETTINGS, NOW))["methods"][0]
    assert result["scenarios"]["conservativeGpPerHour"] <= result["scenarios"]["expectedGpPerHour"]


def test_missing_latest_still_preserves_ge_capacity_for_execution():
    records = {1: market(), 2: market(510, 500)}
    records[1]["current"]["high"] = None
    records[1]["item"]["limit"] = 200
    method = {"name": "Latest missing", "cycles_per_hour": 100,
              "inputs": [{"item_id": 1}], "outputs": [{"item_id": 2}]}
    result = build_public_afk(NOW, evaluate_method("missing", method, records, set(), SETTINGS, NOW))["methods"][0]
    assert result["current"]["gpPerHour"] is None
    assert result["mechanics"]["cyclesPerHourByBuyLimits"] == 50
    assert result["scenarios"]["expectedGpPerHour"] == 150 * 50
    assert result["executionPrices"]["inputs"][0]["latestObserved"] is None


def test_scenarios_reuse_quotes_without_sharing_mutable_results(monkeypatch):
    import osrs_market.methods as methods

    calls = []
    original = methods.execution_quote

    def counted_quote(record, side, required, now):
        calls.append((side, required))
        return original(record, side, required, now)

    monkeypatch.setattr(methods, "execution_quote", counted_quote)
    method = {"cycles_per_hour": 100,
              "inputs": [{"item_id": 1, "quantity": 1}, {"item_id": 1, "quantity": 2}],
              "outputs": [{"item_id": 1, "quantity": 3}]}
    rows = methods.evaluate_method("reuse", method, {1: market()}, set(), SETTINGS, NOW)
    assert calls == [("high", 100), ("high", 200), ("low", 300)]
    assert rows[0]["executionPrices"]["inputs"][1]["requiredPerHour"] == 200
    rows[0]["inputs"][0]["execution"]["expectedExecutable"] = -1
    rows[0]["executionPrices"]["inputs"][0]["expectedExecutable"] = -2
    assert rows[1]["inputs"][0]["execution"]["expectedExecutable"] == 340
    assert rows[1]["executionPrices"]["inputs"][0]["expectedExecutable"] == 340
