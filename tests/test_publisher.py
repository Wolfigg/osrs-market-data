import pytest

from osrs_market.publisher import validate_site, write_json


def seed_required(tmp_path, market_items=None, afk_results=None):
    generated = 123
    write_json(tmp_path / "index.json", {"schemaVersion": 2, "generatedAt": generated})
    write_json(tmp_path / "health.json", {"schemaVersion": 2, "generatedAt": generated})
    write_json(tmp_path / "market" / "summary.json", {"schemaVersion": 2, "generatedAt": generated, "items": market_items if market_items is not None else [{"item": {"id": 1}}]})
    write_json(tmp_path / "afk" / "methods.json", {"schemaVersion": 2, "generatedAt": generated, "results": afk_results if afk_results is not None else [{"methodId": "m"}]})
    write_json(tmp_path / "afk" / "rankings.json", {"schemaVersion": 2, "generatedAt": generated, "rankings": []})
    write_json(tmp_path / "alchemy" / "candidates.json", {"schemaVersion": 2, "generatedAt": generated, "candidates": []})
    write_json(tmp_path / "alchemy" / "rankings.json", {"schemaVersion": 2, "generatedAt": generated, "candidates": []})


def test_validate_site_accepts_v2_structure(tmp_path):
    seed_required(tmp_path)
    validate_site(tmp_path)


def test_validate_site_rejects_empty_market(tmp_path):
    seed_required(tmp_path, market_items=[])
    with pytest.raises(ValueError):
        validate_site(tmp_path)


def test_validate_site_rejects_no_afk_methods(tmp_path):
    seed_required(tmp_path, afk_results=[])
    with pytest.raises(ValueError):
        validate_site(tmp_path)
