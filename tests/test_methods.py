from osrs_market.methods import evaluate_method


def record(item_id, name, high, low, limit=1000, volume=100000):
    windows = {key: {"highVwap": high, "lowVwap": low, "totalVolume": volume} for key in ("6h", "24h", "7d", "30d", "6m")}
    return {
        "item": {"id": item_id, "name": name, "limit": limit, "highalch": None},
        "current": {"high": high, "low": low, "highFreshness": "fresh", "lowFreshness": "fresh", "crossed": False},
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
        3: record(3, "Output", 220, 200, limit=1000),
    }


def test_multiple_inputs_outputs_and_fixed_fee():
    method = {
        "name": "test",
        "inputs": [{"item_id": 1, "quantity": 2}, {"item_id": 2, "quantity": 1}],
        "outputs": [{"item_id": 3, "quantity": 2}],
        "fixed_cost_gp_per_cycle": 10,
        "cycles_per_hour": 100,
    }
    row = evaluate_method("m", method, base_records(), set(), SETTINGS, 123)[0]
    assert row["economics"]["inputGpPerCycle"] == 250
    assert row["economics"]["fixedCostGpPerCycle"] == 10
    assert row["economics"]["geTaxGpPerCycle"] == 8
    assert row["economics"]["outputNetGeGpPerCycle"] == 392
    assert row["economics"]["profitGpPerCycle"] == 132


def test_tax_exempt_output():
    method = {"inputs": [], "outputs": [{"item_id": 3}], "cycles_per_hour": 1}
    row = evaluate_method("m", method, base_records(), {3}, SETTINGS, 123)[0]
    assert row["outputs"][0]["geTaxPerItem"] == 0


def test_npc_shop_sale_is_revenue_without_ge_output_tax():
    records = base_records()
    records[4] = record(4, "Rune warhammer", 25_000, 24_900, limit=70)
    method = {
        "inputs": [{"item_id": 4, "quantity": 1, "buy_via_ge": True}],
        "outputs": [],
        "shop_sales": [{"item_id": 4, "quantity": 1, "shop_name": "Skulgrimen's Battle Gear", "gp_per_item": 29_050}],
        "cycles_per_hour": 20,
    }
    row = evaluate_method("shop-sale", method, records, set(), SETTINGS, 123)[0]
    assert row["valid"] is True
    assert row["economics"]["inputGpPerCycle"] == 25_000
    assert row["economics"]["shopSaleGpPerCycle"] == 29_050
    assert row["economics"]["outputNetGeGpPerCycle"] == 0
    assert row["economics"]["geTaxGpPerCycle"] == 0
    assert row["economics"]["profitGpPerCycle"] == 4_050
    assert row["shopSales"][0]["proceeds"] == 29_050


def test_npc_shop_purchase_cost_is_added_to_profit_and_capital():
    records = base_records()
    records[4] = record(4, "Astral rune", 65, 64)
    method = {
        "inputs": [],
        "shop_purchases": [{"item_id": 4, "quantity": 250, "shop_name": "Baba Yaga's Magic Shop", "gp_per_item": 55.76}],
        "outputs": [{"item_id": 4, "quantity": 250}],
        "cycles_per_hour": 1,
    }
    row = evaluate_method("shop-purchase", method, records, set(), SETTINGS, 123)[0]
    assert row["economics"]["shopPurchaseGpPerCycle"] == 13_940
    assert row["economics"]["totalCostGpPerCycle"] == 13_940
    assert row["shopPurchases"][0]["cost"] == 13_940
    assert row["economics"]["profitGpPerCycle"] == 1_810


def test_buy_limit_bottleneck_is_reported_separately():
    method = {"inputs": [{"item_id": 1, "quantity": 2}], "outputs": [{"item_id": 3}], "cycles_per_hour": 100}
    row = evaluate_method("m", method, base_records(), set(), SETTINGS, 123)[0]
    assert row["mechanics"]["cyclesPerHour"] == 100
    assert row["mechanics"]["cyclesPerHourByBuyLimits"] == 50


def test_afk_metrics_are_exposed():
    method = {
        "inputs": [{"item_id": 1}],
        "outputs": [{"item_id": 3}],
        "cycles_per_hour": 100,
        "afk": {"interval_seconds": 90, "intensity": "very_low"},
    }
    row = evaluate_method("m", method, base_records(), set(), SETTINGS, 123)[0]
    assert row["afk"]["interactionWindowsPerHour"] == 40
    assert row["afk"]["gpPerInteractionWindow"] is not None
    assert "profitGpPerHourSequentialAlchIncluded" not in row["economics"]
    assert "highAlchValue" not in row["outputs"][0]


def test_patient_scenario_is_labelled_not_guaranteed_to_fill():
    method = {"inputs": [], "outputs": [{"item_id": 3}], "cycles_per_hour": 1}
    rows = evaluate_method("m", method, base_records(), set(), SETTINGS, 123)
    patient = [r for r in rows if r["scenario"] == "CURRENT_PATIENT_PROXY"][0]
    assert "NOT_GUARANTEED_TO_FILL" in patient["warnings"]
