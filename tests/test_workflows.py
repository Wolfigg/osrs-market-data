from pathlib import Path


def text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_live_refresh_is_lightweight_and_public_only():
    workflow = text(".github/workflows/refresh-live.yml")
    assert 'cron: "7,17,27,37,47,57 * * * *"' in workflow
    assert "collect --mode live" in workflow
    assert "/usr/bin/time -v" in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "rm -f .market-cache/mapping.json" in workflow
    assert "planner_v3.js" not in workflow
    assert "path: build/public-site" in workflow
    assert "path: build/internal-report" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "group: osrs-market-publish" in workflow


def test_history_refresh_has_short_long_full_tiers_and_cache_persistence():
    workflow = text(".github/workflows/refresh-history.yml")
    for cron in ('"23 * * * *"', '"41 */6 * * *"', '"47 3 * * *"'):
        assert cron in workflow
    for mode in ('mode="short"', 'mode="long"', 'mode="full"'):
        assert mode in workflow
    assert "collect --mode" in workflow
    assert "/usr/bin/time -v" in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" in workflow
    assert "recommendation_history.py" in workflow
    assert ".market-cache/recommendation-history.json" in workflow
    assert "backtesting-summary.json" in workflow
    assert "planner_v3.js" not in workflow
    assert "path: build/public-site" in workflow
    assert "path: build/internal-report" in workflow
    assert "group: osrs-market-publish" in workflow


def test_public_site_has_no_session_planner_asset_or_module():
    public_site = text("src/osrs_market/public_site.py")
    assert 'src="assets/planner_v3.js' not in public_site
    assert 'for filename in ("app.css", "app.js", "enhancements.js", "planner_v3.js"' not in public_site
    assert "Bankroll & time planner" not in public_site
    assert "My session profit" not in public_site
    assert not Path("web/assets/planner_v3.js").exists()
    assert not Path("src/osrs_market/session_planner_v3.py").exists()


def test_ci_separates_unit_and_cross_browser_acceptance():
    workflow = text(".github/workflows/ci.yml")
    assert "Run tests" in workflow
    assert "browser-acceptance:" in workflow
    assert "playwright@1.55.0" in workflow
    assert "chromium firefox" in workflow
    assert "tests/browser_acceptance.mjs" in workflow


def test_obsolete_monolithic_publisher_workflow_is_absent():
    assert not Path(".github/workflows/collect-and-publish.yml").exists()
