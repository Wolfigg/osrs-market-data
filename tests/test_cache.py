import json

from osrs_market.cache import item_windows, load_history, load_mapping, put_item_windows, save_history, save_mapping
from osrs_market.models import MappingItem


def test_mapping_cache_round_trip(tmp_path):
    cache_dir = tmp_path / "cache"
    mapping = {1: MappingItem(id=1, name="Test", members=False, highalch=100, limit=50)}
    save_mapping(cache_dir, mapping, 123)
    loaded = load_mapping(cache_dir)
    assert loaded is not None
    items, generated_at = loaded
    assert generated_at == 123
    assert items[1].name == "Test"
    assert items[1].highalch == 100


def test_empty_history_cache_has_explicit_metadata(tmp_path):
    history = load_history(tmp_path / "cache")
    assert history["generatedAt"] is None
    assert history["source"] == "osrs-wiki"
    assert history["status"] == "empty"


def test_history_cache_round_trip(tmp_path):
    cache_dir = tmp_path / "cache"
    history = load_history(cache_dir)
    put_item_windows(history, 2353, {"24h": {"highVwap": 500}, "7d": {"highVwap": 490}})
    history["shortGeneratedAt"] = 100
    history["longGeneratedAt"] = 80
    save_history(cache_dir, history)

    loaded = load_history(cache_dir)
    assert loaded["generatedAt"] == 100
    assert loaded["source"] == "osrs-wiki"
    assert loaded["status"] == "ok"
    assert loaded["shortGeneratedAt"] == 100
    assert loaded["longGeneratedAt"] == 80
    assert item_windows(loaded, 2353)["24h"]["highVwap"] == 500
    raw = json.loads((cache_dir / "historical.json").read_text(encoding="utf-8"))
    assert raw["generatedAt"] == 100


def test_put_item_windows_preserves_other_windows(tmp_path):
    history = load_history(tmp_path / "cache")
    put_item_windows(history, 1, {"24h": {"highVwap": 100}, "30d": {"highVwap": 90}})
    put_item_windows(history, 1, {"24h": {"highVwap": 110}})
    windows = item_windows(history, 1)
    assert windows["24h"]["highVwap"] == 110
    assert windows["30d"]["highVwap"] == 90
