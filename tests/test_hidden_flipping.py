from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hidden_flipping_page_is_unlisted_and_noindex():
    page = (ROOT / "web" / "flipping.html").read_text(encoding="utf-8")
    public_site = (ROOT / "src" / "osrs_market" / "public_site.py").read_text(encoding="utf-8")

    assert 'name="robots" content="noindex,nofollow"' in page
    assert 'data-page="flipping"' in page
    assert 'assets/flipping.js' in page
    assert 'href="flipping.html"' not in public_site
    assert 'Grand Exchange Flips' not in public_site


def test_hidden_flipping_model_exposes_raw_execution_evidence():
    script = (ROOT / "web" / "assets" / "flipping.js").read_text(encoding="utf-8")

    assert 'getJson("/latest")' in script
    assert 'getJson("/5m")' in script
    assert 'getJson("/1h")' in script
    assert 'data/flipping-tax-exemptions.json' in script
    assert "flowCoveragePct" in script
    assert "flowBalancePct" in script
    assert "buySellRatio" in script
    assert "Math.min(buyLimit, avg1h.balancedFlow)" in script
    assert "opportunity-size proxy, not guaranteed profit or GP/hour" in script


def test_publish_workflows_install_hidden_flipping_assets():
    for name in ("refresh-live.yml", "refresh-history.yml"):
        workflow = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "cp web/flipping.html build/public-site/flipping.html" in workflow
        assert "cp web/assets/flipping.js build/public-site/assets/flipping.js" in workflow
        assert "cp config/ge_tax_exemptions.json build/public-site/data/flipping-tax-exemptions.json" in workflow
