(() => {
  "use strict";

  const API_BASE = "https://prices.runescape.wiki/api/v1/osrs";
  const REFRESH_MS = 60_000;
  const DISPLAY_LIMIT = 500;
  const GE_TAX_RATE = 0.02;
  const GE_TAX_CAP = 5_000_000;
  const FRESH_SECONDS = 1_800;
  const ACCEPTABLE_SECONDS = 7_200;
  const VERY_STALE_SECONDS = 86_400;

  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const pct = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 });
  const esc = value => String(value ?? "").replace(/[&<>'\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[c]);
  const num = value => value == null || value === "" ? null : Number(value);
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

  let cachedMapping = null;
  let taxExemptIds = null;
  let taxExemptNames = null;
  let items = [];
  let lastRefreshAt = null;
  let refreshTimer = null;

  async function getJson(path, base = API_BASE) {
    const url = base ? `${base}${path}` : path;
    const response = await fetch(url, { cache: "no-store", mode: "cors" });
    if (!response.ok) throw new Error(`${path}: ${response.status}`);
    return response.json();
  }

  function bulkMap(payload) {
    const data = payload?.data;
    if (Array.isArray(data)) return new Map(data.filter(row => row?.id != null).map(row => [Number(row.id), row]));
    if (data && typeof data === "object") return new Map(Object.entries(data).map(([id, row]) => [Number(id), row]));
    return new Map();
  }

  function quoteMap(payload) {
    const data = payload?.data;
    if (!data || typeof data !== "object" || Array.isArray(data)) return new Map();
    return new Map(Object.entries(data).map(([id, row]) => [Number(id), row]));
  }

  async function mapping() {
    if (cachedMapping) return cachedMapping;
    const payload = await getJson("/mapping");
    if (!Array.isArray(payload)) throw new Error("mapping: unexpected response shape");
    cachedMapping = payload;
    return cachedMapping;
  }

  async function taxExemptions() {
    if (taxExemptIds && taxExemptNames) return;
    const payload = await getJson("data/flipping-tax-exemptions.json", "");
    taxExemptIds = new Set((payload.itemIds || []).map(Number));
    taxExemptNames = new Set((payload.itemNames || []).map(value => String(value).toLowerCase()));
  }

  function taxPerItem(sellPrice, itemId, name) {
    if (sellPrice == null || sellPrice < 0) return null;
    if (!taxExemptIds || !taxExemptNames) throw new Error("tax exemptions unavailable");
    if (taxExemptIds.has(Number(itemId)) || taxExemptNames.has(String(name || "").toLowerCase())) return 0;
    return Math.min(Math.floor(Number(sellPrice) * GE_TAX_RATE), GE_TAX_CAP);
  }

  function marginFor(buyPrice, sellPrice, itemId, name) {
    if (!(buyPrice > 0) || !(sellPrice > 0)) return { tax: null, netSell: null, margin: null, roi: null };
    const tax = taxPerItem(sellPrice, itemId, name);
    const netSell = Number(sellPrice) - Number(tax || 0);
    const margin = netSell - Number(buyPrice);
    return { tax, netSell, margin, roi: Number(buyPrice) > 0 ? margin / Number(buyPrice) * 100 : null };
  }

  function ageSeconds(timestamp, now) {
    const parsed = num(timestamp);
    if (parsed == null || parsed <= 0) return null;
    return Math.max(0, now - parsed);
  }

  function freshness(age) {
    if (age == null) return { state: "unknown", label: "Unknown" };
    if (age <= FRESH_SECONDS) return { state: "fresh", label: "Fresh" };
    if (age <= ACCEPTABLE_SECONDS) return { state: "recent", label: "Recent" };
    if (age <= VERY_STALE_SECONDS) return { state: "stale", label: "Stale" };
    return { state: "very-stale", label: "Very stale" };
  }

  function windowMetrics(row, itemId, name) {
    if (!row) return {
      buyPrice: null, sellPrice: null, tax: null, margin: null, roi: null,
      buyFlow: null, sellFlow: null, balancedFlow: null, buySellRatio: null, flowBalancePct: null
    };
    const buyPrice = num(row.avgLowPrice);
    const sellPrice = num(row.avgHighPrice);
    const calc = marginFor(buyPrice, sellPrice, itemId, name);
    const buyFlow = num(row.lowPriceVolume);
    const sellFlow = num(row.highPriceVolume);
    const balancedFlow = buyFlow != null && sellFlow != null ? Math.min(buyFlow, sellFlow) : null;
    const buySellRatio = buyFlow != null && sellFlow > 0 ? buyFlow / sellFlow : null;
    const flowBalancePct = buyFlow > 0 && sellFlow > 0 ? Math.min(buyFlow, sellFlow) / Math.max(buyFlow, sellFlow) * 100 : null;
    return { buyPrice, sellPrice, ...calc, buyFlow, sellFlow, balancedFlow, buySellRatio, flowBalancePct };
  }

  function spreadState(currentMargin, fiveMinuteMargin, oneHourMargin) {
    if (!(currentMargin > 0)) return { state: "negative", label: "Not profitable" };
    if (fiveMinuteMargin > 0 && oneHourMargin > 0) return { state: "persistent", label: "Persistent" };
    if ((fiveMinuteMargin != null && fiveMinuteMargin <= 0) || (oneHourMargin != null && oneHourMargin <= 0)) {
      return { state: "unstable", label: "Current only" };
    }
    return { state: "current-only", label: "Current only" };
  }

  function buildItem(meta, quote, fiveMinute, oneHour, now) {
    const itemId = Number(meta.id);
    const name = String(meta.name || itemId);
    const buyPrice = num(quote?.low);
    const sellPrice = num(quote?.high);
    const buyLimit = num(meta.limit);
    if (!(buyPrice > 0) || !(sellPrice > 0) || !(buyLimit > 0)) return null;

    const current = marginFor(buyPrice, sellPrice, itemId, name);
    const highAge = ageSeconds(quote?.highTime, now);
    const lowAge = ageSeconds(quote?.lowTime, now);
    const quoteAge = highAge == null || lowAge == null ? null : Math.max(highAge, lowAge);
    const quoteFreshness = freshness(quoteAge);
    const avg5m = windowMetrics(fiveMinute, itemId, name);
    const avg1h = windowMetrics(oneHour, itemId, name);
    const state = spreadState(current.margin, avg5m.margin, avg1h.margin);

    const flowCappedQuantity = avg1h.balancedFlow == null ? null : Math.max(0, Math.min(buyLimit, avg1h.balancedFlow));
    const flowCappedProfit = current.margin != null && flowCappedQuantity != null ? current.margin * flowCappedQuantity : null;
    const flowCoveragePct = avg1h.balancedFlow == null ? null : avg1h.balancedFlow / buyLimit * 100;
    const capitalAtLimit = buyPrice * buyLimit;
    const limitProfit4h = current.margin != null ? current.margin * buyLimit : null;

    return {
      itemId,
      name,
      members: Boolean(meta.members),
      buyLimit,
      buyPrice,
      sellPrice,
      highTime: num(quote?.highTime),
      lowTime: num(quote?.lowTime),
      highAge,
      lowAge,
      quoteAge,
      freshness: quoteFreshness,
      tax: current.tax,
      netSell: current.netSell,
      margin: current.margin,
      roi: current.roi,
      avg5m,
      avg1h,
      spread: state,
      flowCappedQuantity,
      flowCappedProfit,
      flowCappedCapital: flowCappedQuantity == null ? null : buyPrice * flowCappedQuantity,
      flowCoveragePct,
      capitalAtLimit,
      limitProfit4h
    };
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
      <p>Passive-buy average: <strong>${gpText(window.buyPrice)}</strong></p>
      <p>Passive-sell average: <strong>${gpText(window.sellPrice)}</strong></p>
      <p>Tax-correct margin: <strong>${gpText(window.margin)}</strong></p>
      <p>Passive-buy fill flow: <strong>${plainGp(window.buyFlow)}</strong></p>
      <p>Passive-sell fill flow: <strong>${plainGp(window.sellFlow)}</strong></p>
      <p>Balanced flow: <strong>${plainGp(window.balancedFlow)}</strong></p>
      <p>Buy/sell flow ratio: <strong>${window.buySellRatio == null ? "-" : pct.format(window.buySellRatio)}</strong></p>
      <p>Directional balance: <strong>${window.flowBalancePct == null ? "-" : `${pct.format(window.flowBalancePct)}%`}</strong></p>
    </div>`;
  }

  function record(item) {
    const cls = Number(item.margin) > 0 ? "profit" : "loss";
    return `<details class="ledger-record">
      <summary class="ledger-summary alch-grid">
        <div class="item-name"><strong>${esc(item.name)}</strong><small>${membership(item.members)} · ${esc(item.spread.label)} · ${esc(item.freshness.label)}</small></div>
        <div class="num primary-mobile ${cls}">${plainGp(item.flowCappedProfit)}</div>
        <div class="num">${plainGp(item.buyPrice)}</div>
        <div class="num">${plainGp(item.sellPrice)}</div>
        <div class="num ${cls}">${plainGp(item.margin)}</div>
        <div class="num desktop-secondary">${item.roi == null ? "-" : `${pct.format(item.roi)}%`}</div>
        <div class="num desktop-secondary">${plainGp(item.buyLimit)}</div>
        <div class="num desktop-secondary">${item.flowCoveragePct == null ? "-" : `${pct.format(item.flowCoveragePct)}%`}</div>
        <div class="num desktop-secondary">${item.avg1h.flowBalancePct == null ? "-" : `${pct.format(item.avg1h.flowBalancePct)}%`}</div>
        <div class="desktop-secondary">${esc(item.freshness.label)}</div>
      </summary>
      <div class="detail-panel">
        <div class="badge-row">${badge(membership(item.members))}${badge(item.spread.label, item.spread.state)}${badge(item.freshness.label, item.freshness.state)}</div>
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
          <p>Latest low is treated as the passive buy target and latest high as the passive sell target. Seller tax is floored per item, capped at 5,000,000 gp, and the repository tax-exemption configuration is applied.</p>
          <p>Flow-capped profit uses current post-tax margin multiplied by the smaller of the 4H GE limit and the thinner observed 1H trade direction. It is an opportunity-size proxy, not guaranteed profit or GP/hour.</p>
          <p>Directional balance is the thinner 1H side divided by the larger 1H side. It exposes one-sided markets directly instead of hiding them inside a confidence score.</p>
        </div>
      </div>
    </details>`;
  }

  function renderOverview() {
    const persistent = items.filter(item => item.spread.state === "persistent" && item.margin > 0);
    const ranked = [...persistent].sort((a, b) => Number(b.flowCappedProfit ?? -Infinity) - Number(a.flowCappedProfit ?? -Infinity));
    const leader = ranked[0];
    setText("#flip-leader-value", leader ? `${compactGp(leader.flowCappedProfit)} gp` : "No signal");
    setText("#flip-leader-name", leader?.name || "No persistent spread available");
    setText("#flip-persistent-count", gp.format(persistent.length));
    setText("#flip-fresh-count", gp.format(items.filter(item => item.freshness.state === "fresh").length));
    setText("#flip-item-total", gp.format(items.length));
    if (lastRefreshAt) setText("#flip-source-age", `Live Wiki scan ${lastRefreshAt.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})}`);
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
      if (state === "persistent" && item.spread.state !== "persistent") return false;
      if (state === "positive" && !(item.margin > 0)) return false;
      if (!showStale && ["stale", "very-stale", "unknown"].includes(item.freshness.state)) return false;
      if (!(item.margin >= minMargin)) return false;
      if (!(item.roi >= minRoi)) return false;
      if (minVolume > 0 && !(Number(item.avg1h.balancedFlow || 0) >= minVolume)) return false;
      if (capitalLimit != null && !(item.flowCappedCapital != null && item.flowCappedCapital <= capitalLimit)) return false;
      return true;
    });

    const value = item => ({
      "flow-profit": item.flowCappedProfit,
      "limit-profit": item.limitProfit4h,
      margin: item.margin,
      roi: item.roi,
      volume: item.avg1h.balancedFlow,
      coverage: item.flowCoveragePct,
      balance: item.avg1h.flowBalancePct,
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
      setText("#flip-source-age", "Fetching live Wiki prices");
      await taxExemptions();
      const [mappingRows, latestPayload, fiveMinutePayload, oneHourPayload] = await Promise.all([
        mapping(), getJson("/latest"), getJson("/5m"), getJson("/1h")
      ]);
      const latest = quoteMap(latestPayload);
      const fiveMinute = bulkMap(fiveMinutePayload);
      const oneHour = bulkMap(oneHourPayload);
      const now = Math.floor(Date.now() / 1000);
      items = mappingRows.map(meta => buildItem(meta, latest.get(Number(meta.id)), fiveMinute.get(Number(meta.id)), oneHour.get(Number(meta.id)), now)).filter(Boolean);
      lastRefreshAt = new Date();
      renderOverview();
      render();
    } catch (error) {
      console.error(error);
      setText("#flip-source-age", "Live flip scan unavailable");
      if (list) list.innerHTML = '<p class="empty-state">Flipping data could not be loaded from prices.runescape.wiki.</p>';
    }
  }

  bindFilters();
  refresh();
  refreshTimer = window.setInterval(refresh, REFRESH_MS);
  window.addEventListener("beforeunload", () => window.clearInterval(refreshTimer), { once: true });
})();
