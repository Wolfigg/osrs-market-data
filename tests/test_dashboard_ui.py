from pathlib import Path


def test_dashboard_exposes_top_five_rankings_and_long_afk_history():
    app = Path("web/assets/app.js").read_text(encoding="utf-8")
    assert "Top 5 AFK" in app
    assert "Top 5 High Alch" in app
    assert 'm.history?.["7dGpPerHour"]' in app
    assert 'm.history?.["30dGpPerHour"]' in app
    assert "7D GP/h" in app
    assert "30D GP/h" in app


def test_afk_ledger_supports_long_history_sorting():
    app = Path("web/assets/app.js").read_text(encoding="utf-8")
    assert 'value="gp-7d"' in app
    assert 'value="gp-30d"' in app
    assert '"gp-7d": m.history?.["7dGpPerHour"]' in app
    assert '"gp-30d": m.history?.["30dGpPerHour"]' in app
