import assert from "node:assert/strict";
import { chromium, firefox } from "playwright";

const base = "http://127.0.0.1:8765";

async function waitForCount(page, selector, text) {
  await page.waitForFunction(({ selector, text }) => document.querySelector(selector)?.textContent === text, { selector, text });
}

async function assertResponsive(page, width, height = 900) {
  await page.setViewportSize({ width, height });
  await page.waitForTimeout(50);
  const overflow = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  assert.ok(overflow.scroll <= overflow.client + 1, `horizontal overflow at ${width}px: ${JSON.stringify(overflow)}`);
}

async function run(browserType, name) {
  const browser = await browserType.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(`${base}/index.html`, { waitUntil: "networkidle" });

    assert.equal(await page.locator("#health-state").textContent(), "Delayed", `${name}: 2.5h freshness boundary`);
    await waitForCount(page, "#afk-count", "2 methods");
    for (const width of [360, 390, 768, 1280]) await assertResponsive(page, width);
    await page.setViewportSize({ width: 1280, height: 900 });

    // Bankroll/session planner uses the market-aware V3 path and persists locally.
    assert.equal(await page.locator("#planner-bankroll").inputValue(), "2000000", `${name}: first-run planner has a real bankroll value`);
    await page.locator("#planner-bankroll").fill("100000");
    await page.locator("#planner-hours").fill("4");
    await page.waitForFunction(() => document.querySelector("#planner-summary")?.textContent?.includes("Cut camphor logs"));
    assert.match(await page.locator("#planner-summary").textContent(), /480,000 gp over 4h/);
    await page.locator("#afk-sort").selectOption("session-profit");
    assert.equal(await page.locator("#afk-sort").inputValue(), "session-profit");
    await page.reload({ waitUntil: "networkidle" });
    assert.equal(await page.locator("#planner-bankroll").inputValue(), "100000");
    assert.equal(await page.locator("#planner-hours").inputValue(), "4");

    // Search and URL-state synchronization.
    await page.locator("#afk-search").fill("camphor");
    await waitForCount(page, "#afk-count", "1 method");
    assert.match(page.url(), /q=camphor/);
    assert.match(await page.locator("#afk-list").textContent(), /Cut camphor logs/);

    // URL restoration of advanced type/capital filters without forcing them open.
    await page.goto(`${base}/index.html?profit=all&type=gathering&capital=500000&sort=alphabetical`, { waitUntil: "networkidle" });
    await waitForCount(page, "#afk-count", "1 method");
    assert.equal(await page.locator("#afk-type").inputValue(), "gathering");
    assert.equal(await page.locator("#afk-capital").inputValue(), "500000");
    assert.equal(await page.locator("#afk-sort").inputValue(), "alphabetical");

    // Expanded method keeps a compact summary; full economics is another explicit disclosure.
    const camphor = page.locator('[data-method-id="camphor"]');
    await camphor.locator(":scope > summary").click();
    assert.equal(await camphor.locator(".method-more").getAttribute("open"), null);
    await camphor.locator(".method-more > summary").click();
    const camphorText = await camphor.textContent();
    assert.match(camphorText, /Troubled Tortugans/);
    assert.match(camphorText, /Sailing: 45/);
    assert.match(camphorText, /Current calculation/);
    assert.match(camphorText, /Sustainability & liquidity/);
    assert.match(camphorText, /My 4h:/);
    assert.doesNotMatch(camphorText, /With your bankroll:/);

    // Sustainability filtering is independent of historical stability.
    await page.goto(`${base}/index.html?profit=all&sustainability=moderate`, { waitUntil: "networkidle" });
    await waitForCount(page, "#afk-count", "1 method");
    assert.match(await page.locator("#afk-list").textContent(), /Cut ruby bolt tips/);

    // Skill profile is under one collapsed advanced-control panel, persists locally and gates by all skills.
    await page.goto(`${base}/index.html?profit=all&type=gathering`, { waitUntil: "networkidle" });
    assert.equal(await page.locator(".advanced-filters").getAttribute("open"), null);
    await page.locator(".advanced-filters > summary").click();
    await page.locator('[data-skill="woodcutting"]').fill("99");
    await page.locator('[data-skill="sailing"]').fill("44");
    await page.locator("#afk-can-do").check();
    await waitForCount(page, "#afk-count", "0 methods");
    await page.locator('[data-skill="sailing"]').fill("45");
    await waitForCount(page, "#afk-count", "1 method");
    await page.reload({ waitUntil: "networkidle" });
    assert.equal(await page.locator('[data-skill="woodcutting"]').inputValue(), "99");
    assert.equal(await page.locator('[data-skill="sailing"]').inputValue(), "45");

    // F2P + profitability behavior.
    await page.goto(`${base}/index.html?profit=all&members=f2p`, { waitUntil: "networkidle" });
    await waitForCount(page, "#afk-count", "1 method");
    assert.match(await page.locator("#afk-list").textContent(), /Craft gold ring/);
    await page.locator("#afk-profit").selectOption("profitable");
    await waitForCount(page, "#afk-count", "0 methods");

    // High Alch filters, strict capital boundary and unavailable visibility.
    await page.goto(`${base}/alchemy.html`, { waitUntil: "networkidle" });
    await waitForCount(page, "#alch-count", "2 candidates");
    await page.locator("#alch-capital").selectOption("1000000");
    await waitForCount(page, "#alch-count", "1 candidate");
    assert.match(await page.locator("#alch-list").textContent(), /Rune platebody/);
    assert.doesNotMatch(await page.locator("#alch-list").textContent(), /Exact million item/);
    await page.locator("#alch-profit").selectOption("all");
    await page.locator("#alch-capital").selectOption("all");
    await page.locator("#alch-unavailable").check();
    await waitForCount(page, "#alch-count", "3 candidates");
    assert.match(await page.locator("#alch-list").textContent(), /Unavailable item/);
    await page.goto(`${base}/alchemy.html?q=rune&sort=profit-30d`, { waitUntil: "networkidle" });
    await waitForCount(page, "#alch-count", "1 candidate");
    assert.equal(await page.locator("#alch-sort").inputValue(), "profit-30d");
    assert.match(await page.locator("#alch-list").textContent(), /Rune platebody/);
  } finally {
    await browser.close();
  }
}

await run(chromium, "chromium");
await run(firefox, "firefox");
console.log("Browser acceptance passed in Chromium and Firefox");
