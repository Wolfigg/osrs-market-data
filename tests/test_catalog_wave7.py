from pathlib import Path

from osrs_market.catalog_schema import load_catalogue_document
from osrs_market.catalog_wave7 import wave7_method_catalog
from osrs_market.config import load_yaml


def test_fishing_methods_expose_active_realistic_and_afk_pacing():
    methods = wave7_method_catalog()
    fishing = [row for key, row in methods.items() if key.startswith("gather_fishing_") and row.get("enabled", True)]
    assert fishing
    for method in fishing:
        variants = {row["id"]: row for row in method.get("variants") or []}
        assert set(variants) == {"active", "realistic", "afk"}
        active = variants["active"]["overrides"]["cycles_per_hour"]
        realistic = variants["realistic"]["overrides"]["cycles_per_hour"]
        afk = variants["afk"]["overrides"]["cycles_per_hour"]
        assert active > realistic > afk > 0
        model = method["model"]["gatheringV2"]
        assert model["activityType"] == "fishing"
        assert "pacingProfiles" in model
        assert model["policySource"]["type"] == "catalogue_policy"


def test_gathering_policy_is_a_valid_data_catalogue_document():
    payload = load_catalogue_document(Path("catalogue/gathering/pacing.yml"))
    assert payload["family"] == "gathering_pacing"
    assert set(payload["rules"]) == {"fishing", "woodcutting", "mining"}
    assert payload["rules"]["fishing"]["realisticMultiplier"] == 0.90
    assert payload["rules"]["mining"]["afkMultiplier"] == 0.68


def test_woodcutting_and_mining_use_gathering_v2_contract():
    methods = wave7_method_catalog()
    activities = {row.get("model", {}).get("gatheringV2", {}).get("activityType") for row in methods.values()}
    assert "woodcutting" in activities
    assert "mining" in activities


def test_wave7_overrides_are_loaded_into_production_catalogue():
    methods = load_yaml("config/methods.yaml")["methods"]
    tuna = methods["gather_fishing_tuna_swordfish"]
    assert tuna["model"]["gatheringV2"]["mixedCatch"] is True
    assert {row["id"] for row in tuna["variants"]} == {"active", "realistic", "afk"}
