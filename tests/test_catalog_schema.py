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


def test_jewellery_yaml_matches_existing_mechanics_in_parallel():
    old = wave5_method_catalog()
    new = compile_jewellery_enchanting(Path("catalogue/enchanting/jewellery.yml"))
    for method_id, compiled in new.items():
        legacy = old[method_id]
        assert compiled["cycles_per_hour"] == legacy["cycles_per_hour"]
        assert compiled["theoretical_cycles_per_hour"] == legacy["theoretical_cycles_per_hour"]
        assert compiled["requirements"] == legacy["requirements"]
        assert normalized_items(compiled["inputs"]) == normalized_items(legacy["inputs"])
        assert normalized_items(compiled["outputs"]) == normalized_items(legacy["outputs"])
        assert [row["id"] for row in compiled["variants"]] == [row["id"] for row in legacy["variants"]]
