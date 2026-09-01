from osrs_market.anomaly_detection import detect_method_anomalies, publication_errors


def test_missing_input_price_blocks_apparently_valid_method():
    anomalies = detect_method_anomalies({"methodId": "bad", "current": {"valid": True}, "inputs": [{"name": "Input", "price": None}]})
    assert publication_errors(anomalies)
    assert anomalies[0]["rule"] == "missing_input_price"


def test_stable_without_history_is_warning_only():
    anomalies = detect_method_anomalies({"methodId": "watch", "current": {"valid": False}, "stability": {"state": "stable"}, "history": {}})
    assert not publication_errors(anomalies)
    assert anomalies[0]["severity"] == "warning"
