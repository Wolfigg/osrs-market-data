from osrs_market.methods import evaluate_method


def record(item_id, name, high, low, limit=1000, highalch=None, volume=100000):
    windows = {}
    for key in ("6h", "24h", "7d", "30d"):
        windows[key] = {"highVwap": high, "lowVwap": low, "totalVolume": volume}
    return {
        "item": {"id": item_id, "name": name, "limit": limit, "highalch": highalch},
        "current": {
            "high": high,
            "low": low,
            "highFreshness": "fresh",
            "lowFreshness": "fresh",
            "crossed": False,
        },
        "windows": windows,
    }


SETTINGS = {
    "liquidity": {"notice_market_share_pct": 1, "caution_market_share_pct": 5, "high_risk_market_share_pct": 10},
    "methods": {"default_planned_hours_per_day": 1},
}


def base_records():
    return {
        1: record(1, "Input A", 100, 90, limit=400),
        2: record(2, "Input B", 50, 45, limit=1000),
        3: record(3, "Output", 220, 200, limit=1000, highalch=250),
        561: record(561, "Nature rune", 100, 95, limit=12000),
    }


def test_multiple_inputs_outputs_and_fixed_fee():
    method = {
        "name": "test",
        "inputs": [{"item_id": 1, "quantity": 2}, {"item_id": 2, "quantity": 1}],
        "outputs": [{"item_id": 3, "quantity": 2, "exit": "ge"}],
        "fixed_cost_gp_per_cycle": 10,
        "cycles_per_hour": 100,
    }
    row = evaluate_method("m", method, base_records(), set(), SETTINGS, 561, 123)[0]
    assert row["economics"]["inputGpPerCycle"] == 250
    assert row["economics"]["fixedCostGpPerCycle"] == 10
    assert row["economics"]["geTaxGpPerCycle"] == 8
    assert row["economics"]["outputChosenNetGpPerCycle"] == 392
    assert row["economics"]["profitGpPerCycle"] == 132


def test_tax_exempt_output():
    method = {"inputs": [], "outputs": [{"item_id": 3, "quantity": 1}], "cycles_per_hour": 1}
    row = evaluate_method("m", method, base_records(), {3}, SETTINGS, 561, 123)[0]
    assert row["outputs"][0]["geTaxPerItem"] == 0


def test_buy_limit_bottleneck_is_reported_separately():
    method = {"inputs": [{"item_id": 1, "quantity": 2}], "outputs": [{"item_id": 3}], "cycles_per_hour": 100}
    row = evaluate_method("m", method, base_records(), set(), SETTINGS, 561, 123)[0]
    assert row["mechanics"]["cyclesPerHour"] == 100
    assert row["mechanics"]["cyclesPerHourByBuyLimits"] == 50


def test_best_immediate_can_choose_alch_exit():
    records = base_records()
    records[3]["item"]["highalch"] = 400
    method = {"inputs": [], "outputs": [{"item_id": 3, "exit": "best_immediate"}], "cycles_per_hour": 100}
    row = evaluate_method("m", method, records, set(), SETTINGS, 561, 123)[0]
    assert row["outputs"][0]["chosenExit"] == "HIGH_ALCH"


def test_sequential_alching_reduces_workflow_gp_per_hour():
    records = base_records()
    records[3]["item"]["highalch"] = 400
    method = {"inputs": [], "outputs": [{"item_id": 3, "quantity": 1, "exit": "high_alch"}], "cycles_per_hour": 1200}
    row = evaluate_method("m", method, records, set(), SETTINGS, 561, 123)[0]
    assert row["mechanics"]["combinedCyclesPerHourWithSequentialAlch"] == 600
    assert row["economics"]["profitGpPerHourSequentialAlchIncluded"] < row["economics"]["profitGpPerHourAlchTimeExcluded"]


def test_patient_scenario_is_labelled_not_guaranteed_to_fill():
    method = {"inputs": [], "outputs": [{"item_id": 3}], "cycles_per_hour": 1}
    rows = evaluate_method("m", method, base_records(), set(), SETTINGS, 561, 123)
    patient = [r for r in rows if r["scenario"] == "CURRENT_PATIENT_PROXY"][0]
    assert "NOT_GUARANTEED_TO_FILL" in patient["warnings"]
