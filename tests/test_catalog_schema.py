from pathlib import Path

from osrs_market.catalog_schema import compile_jewellery_enchanting
from osrs_market.catalog_wave5 import wave5_method_catalog


def normalized_items(rows):
    return [(row.get("item_name"), float(row.get("quantity", 1))) for row in rows]


def test_jewellery_yaml_compiles_all_existing_methods():
    old = wave5_method_catalog()
    new = compile_jewellery_enchanting(Path("catalogue/enchanting/jewellery.yml"))
    expected_ids = {method_id for method_id in old if method_id.startswith("enchant_")}
    assert set(new) == expected_ids


def test_jewellery_yaml_preserves_stable_legacy_shape_but_is_mechanics_authority():
    old = wave5_method_catalog()
    new = compile_jewellery_enchanting(Path("catalogue/enchanting/jewellery.yml"))
    corrected_dragonstone = {
        "enchant_dragonstone_ring",
        "enchant_dragonstone_necklace",
        "enchant_dragonstone_bracelet",
        "enchant_dragonstone_amulet",
    }
    for method_id, compiled in new.items():
        legacy = old[method_id]
        assert compiled["cycles_per_hour"] == legacy["cycles_per_hour"]
        assert compiled["requirements"] == legacy["requirements"]
        assert normalized_items(compiled["inputs"]) == normalized_items(legacy["inputs"])
        assert [row["id"] for row in compiled["variants"]] == [row["id"] for row in legacy["variants"]]
        # Wave 8 YAML is now the production source of truth, so corrected
        # theoretical throughput and dragonstone output state must not be forced
        # back to the obsolete Python literals merely to satisfy parity.
        assert compiled["theoretical_cycles_per_hour"] == 2000
        if method_id not in corrected_dragonstone:
            assert normalized_items(compiled["outputs"]) == normalized_items(legacy["outputs"])


def test_dragonstone_yaml_outputs_are_uncharged_tradeable_items():
    new = compile_jewellery_enchanting(Path("catalogue/enchanting/jewellery.yml"))
    expected = {
        "enchant_dragonstone_ring": "Ring of wealth",
        "enchant_dragonstone_necklace": "Skills necklace",
        "enchant_dragonstone_bracelet": "Combat bracelet",
        "enchant_dragonstone_amulet": "Amulet of glory",
    }
    for method_id, output_name in expected.items():
        assert new[method_id]["outputs"][0]["item_name"] == output_name
