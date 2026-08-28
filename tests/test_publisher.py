import pytest

from osrs_market.publisher import validate_site, write_json


def test_validate_site_accepts_required_schema_and_market(tmp_path):
    generated = 123
    write_json(tmp_path / "index.json", {"schemaVersion": 1, "generatedAt": generated})
    write_json(tmp_path / "health.json", {"schemaVersion": 1, "generatedAt": generated})
    write_json(tmp_path / "market.json", {"schemaVersion": 1, "generatedAt": generated, "items": [{"item": {"id": 1}}]})
    write_json(tmp_path / "alchemy.json", {"schemaVersion": 1, "generatedAt": generated})
    write_json(tmp_path / "opportunities.json", {"schemaVersion": 1, "generatedAt": generated})
    write_json(tmp_path / "methods.json", {"schemaVersion": 1, "generatedAt": generated})
    validate_site(tmp_path)


def test_validate_site_rejects_empty_market(tmp_path):
    for name in ("index", "health", "alchemy", "opportunities", "methods"):
        write_json(tmp_path / f"{name}.json", {"schemaVersion": 1, "generatedAt": 123})
    write_json(tmp_path / "market.json", {"schemaVersion": 1, "generatedAt": 123, "items": []})
    with pytest.raises(ValueError):
        validate_site(tmp_path)
