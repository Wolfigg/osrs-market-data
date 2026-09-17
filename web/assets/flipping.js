(() => {
  "use strict";

  const REFRESH_MS = 60_000;
  const DISPLAY_LIMIT = 500;
  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const pct = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 });
  const esc = value => String(value ?? "").replace(/[&<>'\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[c]);
  const plainGp = value => value == null ? "-" : gp.format(value);
  const gpText = value => value == null ? "Unavailable" : `${gp.format(value)} gp`;
  const compactGp = value => {
    if (value == null) return "—";
    const n = Number(value), abs = Math.abs(n);
    if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(abs >= 10_000_000 ? 1 : 2).replace(/\.0+$/, "")}m`;
    if (abs >= 1_000) return `${(n / 1_000).toFixed(abs >= 100_000 ? 0 : 1).replace(/\.0$/, "")}k`;
    return gp.format(n);
  };
  const membership = members => members ? "P2P" : "F2P";

  let items = [];
  let generatedAt = null;
  let refreshTimer = null;

  async function loadJson(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) throw new Error(`${path}: ${response.status}`);
    return response.json();
  }

  function setText(selector, value) {
    const node = document.querySelector(selector);
    if (node) node.textContent = value;
  }

  function readRadio(name) {
    return document.querySelector(`input[name="${name}"]:checked`)?.value || "all";
  }

  function syncQuery(values) {
    const params = new URLSearchParams();
    Object.entries(values).forEach(([key, value]) => {
      if (value != null && value !== "" && value !== "all" && value !== "persistent" && value !== "flow-profit" && value !== "0") params.set(key, value);
    });
    history.replaceState(null, "", `${location.pathname}${params.toString() ? `?${params}` : ""}`);
  }

  function compactAge(age) {
    if (age == null) return "Unknown";
    if (age < 60) return "<1m";
    if (age < 3600) return `${Math.floor(age / 60)}m`;
    if (age < 86400) return `${Math.floor(age / 3600)}h`;
    return `${Math.floor(age / 86400)}d`;
  }

  function badge(text, klass = "") {
    return `<span class="badge ${esc(klass)}">${esc(text)}</span>`;
  }

  function windowHtml(title, window) {
    return `<div><h3>${esc(title)}</h3>
      <p>Passive-buy average: <strong>${gpText(window?.buyPrice)}</strong></p>
      <p>Passive-sell average: <strong>${gpText(window?.sellPrice)}</strong></p>
      <p>Tax-correct margin: <strong>${gpText(window?.margin)}</strong></p>
      <p>Passive-buy fill flow: <strong>${plainGp(window?.buyFlow)}</strong></p>
      <p>Passive-sell fill flow: <strong>${plainGp(window?.sellFlow)}</strong></p>
      <p>Balanced flow: <strong>${plainGp(window?.balancedFlow)}</strong></p>
      <p>Buy/sell flow ratio: <strong>${window?.buySellRatio == null ? "-" : pct.format(window.buySellRatio)}</strong></p>
      <p>Directional balance: <strong>${window?.flowBalancePct == null ? "-" : `${pct.format(window.flowBalancePct)}%`}</strong></p>
    </div>`;
  }

  function record(item) {
    const cls = Number(item.margin) > 0 ? "profit" : "loss";
    return `<details class="ledger-record">
      <summary class="ledger-summary alch-grid">
        <div class="item-name"><strong>${esc(item.name)}</strong><small>${membership(item.members)} · ${esc(item.spread?.label || "Unknown")} · ${esc(item.freshness?.label || "Unknown")}</small></div>
        <div class="num primary-mobile ${cls}">${plainGp(item.flowCappedProfit)}</div>
        <div class="num">${plainGp(item.buyPrice)}</div>
        <div class="num">${plainGp(item.sellPrice)}</div>
        <div class="num ${cls}">${plainGp(item.margin)}</div>
        <div class="num desktop-secondary">${item.roi == null ? "-" : `${pct.format(item.roi)}%`}</div>
        <div class="num desktop-secondary">${plainGp(item.buyLimit)}</div>
        <div class="num desktop-secondary">${item.flowCoveragePct == null ? "-" : `${pct.format(item.flowCoveragePct)}%`}</div>
        <div class="num desktop-secondary">${item.avg1h?.flowBalancePct == null ? "-" : `${pct.format(item.avg1h.flowBalancePct)}%`}</div>
        <div class="desktop-secondary">${esc(item.freshness?.label || "Unknown")}</div>
      </summary>
      <div class="detail-panel">
        <div class="badge-row">${badge(membership(item.members))}${badge(item.spread?.label || "Unknown", item.spread?.state || "")}${badge(item.freshness?.label || "Unknown", item.freshness?.state || "")}</div>
        <div class="detail-grid">
          <div><h3>Current spread</h3>
            <p>Passive buy target: <strong>${gpText(item.buyPrice)}</strong></p>
            <p>Passive sell target: <strong>${gpText(item.sellPrice)}</strong></p>
            <p>Seller tax: <strong>${gpText(item.tax)}</strong></p>
            <p>Net sell value: <strong>${gpText(item.netSell)}</strong></p>
            <p>Margin/item: <strong>${gpText(item.margin)}</strong></p>
            <p>ROI: <strong>${item.roi == null ? "-" : `${pct.format(item.roi)}%`}</strong></p>
            <p>Latest passive-buy-side trade: <strong>${esc(compactAge(item.lowAge))} ago</strong></p>
            <p>Latest passive-sell-side trade: <strong>${esc(compactAge(item.highAge))} ago</strong></p>
          </div>
          <div><h3>Capacity</h3>
            <p>4H GE buy limit: <strong>${plainGp(item.buyLimit)}</strong></p>
            <p>Capital at full limit: <strong>${gpText(item.capitalAtLimit)}</strong></p>
            <p>Theoretical full-limit profit: <strong>${gpText(item.limitProfit4h)}</strong></p>
            <p>1H balanced volume / limit: <strong>${item.flowCoveragePct == null ? "-" : `${pct.format(item.flowCoveragePct)}%`}</strong></p>
            <p>Flow-capped quantity: <strong>${plainGp(item.flowCappedQuantity)}</strong></p>
            <p>Flow-capped capital: <strong>${gpText(item.flowCappedCapital)}</strong></p>
            <p>Flow-capped profit: <strong>${gpText(item.flowCappedProfit)}</strong></p>
          </div>
          ${windowHtml("Recent 1H", item.avg1h)}
          ${windowHtml("Recent 5M", item.avg5m)}
        </div>
        <div class="calculation-block"><h3>Interpretation</h3>
          <p>Latest low is treated as the passive buy target and latest high as the passive sell target. Seller tax and exemptions are calculated by the same backend rules used elsewhere in the project.</p>
          <p>Flow-capped profit uses current post-tax margin multiplied by the smaller of the 4H GE limit and the thinner observed 1H trade direction. It is an opportunity-size proxy, not guaranteed profit or GP/hour.</p>
          <p>Directional balance is the thinner 1H side divided by the larger 1H side. It exposes one-sided markets directly instead of hiding them inside a confidence score.</p>
        </div>
      </div>
    </details>`;
  }

  function renderOverview() {
    const persistent = items.filter(item => item.spread?.state === "persistent" && Number(item.margin) > 0);
    const ranked = [...persistent].sort((a, b) => Number(b.flowCappedProfit ?? -Infinity) - Number(a.flowCappedProfit ?? -Infinity));
    const leader = ranked[0];
    setText("#flip-leader-value", leader ? `${compactGp(leader.flowCappedProfit)} gp` : "No signal");
    setText("#flip-leader-name", leader?.name || "No persistent spread available");
    setText("#flip-persistent-count", gp.format(persistent.length));
    setText("#flip-fresh-count", gp.format(items.filter(item => item.freshness?.state === "fresh").length));
    setText("#flip-item-total", gp.format(items.length));
    if (generatedAt) {
      const age = Math.max(0, Math.floor(Date.now() / 1000) - Number(generatedAt));
      setText("#flip-source-age", `Market scan ${compactAge(age)} ago`);
    }
  }

  function render() {
    const list = document.querySelector("#flip-list");
    if (!list) return;
    const search = document.querySelector("#flip-search").value.trim().toLowerCase();
    const members = readRadio("flip-membership");
    const state = document.querySelector("#flip-spread").value;
    const minMargin = Number(document.querySelector("#flip-min-margin").value || 0);
    const minRoi = Number(document.querySelector("#flip-min-roi").value || 0);
    const minVolume = Number(document.querySelector("#flip-min-volume").value || 0);
    const capital = document.querySelector("#flip-capital").value;
    const capitalLimit = capital === "all" ? null : Number(capital);
    const sort = document.querySelector("#flip-sort").value;
    const showStale = document.querySelector("#flip-stale").checked;

    let rows = items.filter(item => {
      if (search && !item.name.toLowerCase().includes(search)) return false;
      if (members === "f2p" && item.members) return false;
      if (members === "members" && !item.members) return false;
      if (state === "persistent" && item.spread?.state !== "persistent") return false;
      if (state === "positive" && !(Number(item.margin) > 0)) return false;
      if (!showStale && ["stale", "very_stale", "unknown"].includes(item.freshness?.state)) return false;
      if (!(Number(item.margin) >= minMargin)) return false;
      if (!(Number(item.roi) >= minRoi)) return false;
      if (minVolume > 0 && !(Number(item.avg1h?.balancedFlow || 0) >= minVolume)) return false;
      if (capitalLimit != null && !(item.flowCappedCapital != null && Number(item.flowCappedCapital) <= capitalLimit)) return false;
      return true;
    });

    const value = item => ({
      "flow-profit": item.flowCappedProfit,
      "limit-profit": item.limitProfit4h,
      margin: item.margin,
      roi: item.roi,
      volume: item.avg1h?.balancedFlow,
      coverage: item.flowCoveragePct,
      balance: item.avg1h?.flowBalancePct,
      capital: item.flowCappedCapital,
      alphabetic: item.name
    })[sort];
    rows.sort((a, b) => {
      if (sort === "capital") return Number(value(a) ?? Infinity) - Number(value(b) ?? Infinity);
      if (sort === "alphabetic") return a.name.localeCompare(b.name);
      return Number(value(b) ?? -Infinity) - Number(value(a) ?? -Infinity);
    });

    const shown = rows.slice(0, DISPLAY_LIMIT);
    setText("#flip-count", rows.length > DISPLAY_LIMIT ? `${rows.length} candidates, showing first ${DISPLAY_LIMIT}` : `${rows.length} candidate${rows.length === 1 ? "" : "s"}`);
    list.innerHTML = `<div class="ledger-header alch-grid"><div>Item</div><div class="num">Flow-capped profit</div><div class="num">Buy</div><div class="num">Sell</div><div class="num">Margin</div><div class="num desktop-secondary">ROI</div><div class="num desktop-secondary">4H limit</div><div class="num desktop-secondary">1H vol / limit</div><div class="num desktop-secondary">1H balance</div><div class="desktop-secondary">Freshness</div></div>${shown.length ? shown.map(record).join("") : '<p class="empty-state">No flip candidates match these filters.</p>'}`;
    syncQuery({ q: search, members, spread: state, margin: String(minMargin), roi: String(minRoi), volume: String(minVolume), capital, sort, stale: showStale ? "1" : "" });
  }

  function bindFilters() {
    const params = new URLSearchParams(location.search);
    document.querySelector("#flip-search").value = params.get("q") || "";
    if (["f2p", "members"].includes(params.get("members"))) document.querySelector(`input[name="flip-membership"][value="${params.get("members")}"]`).checked = true;
    if (["positive", "all"].includes(params.get("spread"))) document.querySelector("#flip-spread").value = params.get("spread");
    if (params.get("margin")) document.querySelector("#flip-min-margin").value = params.get("margin");
    if (params.get("roi")) document.querySelector("#flip-min-roi").value = params.get("roi");
    if (params.get("volume")) document.querySelector("#flip-min-volume").value = params.get("volume");
    if (params.get("capital")) document.querySelector("#flip-capital").value = params.get("capital");
    if (params.get("sort") && document.querySelector(`#flip-sort option[value="${CSS.escape(params.get("sort"))}"]`)) document.querySelector("#flip-sort").value = params.get("sort");
    document.querySelector("#flip-stale").checked = params.get("stale") === "1";

    document.querySelectorAll("#flip-spread,#flip-capital,#flip-sort,#flip-stale,input[name='flip-membership']").forEach(node => node.addEventListener("change", render));
    document.querySelectorAll("#flip-search,#flip-min-margin,#flip-min-roi,#flip-min-volume").forEach(node => node.addEventListener("input", render));
  }

  async function refresh() {
    const list = document.querySelector("#flip-list");
    try {
      const data = await loadJson("data/flipping.json");
      items = Array.isArray(data.items) ? data.items : [];
      generatedAt = data.generatedAt || null;
      renderOverview();
      render();
    } catch (error) {
      console.error(error);
      setText("#flip-source-age", "Flip data unavailable");
      if (list) list.innerHTML = '<p class="empty-state">Flipping data could not be loaded.</p>';
    }
  }

  bindFilters();
  refresh();
  refreshTimer = window.setInterval(refresh, REFRESH_MS);
  window.addEventListener("beforeunload", () => window.clearInterval(refreshTimer), { once: true });
})();
