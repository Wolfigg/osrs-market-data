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
      if (value != null && value !== "" && value !== "all" && value !== "persistent" && value !== "expected-profit" && value !== "0") params.set(key, value);
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

  function capitalLimit() {
    const raw = document.querySelector("#flip-capital")?.value || "all";
    return raw === "all" ? null : Number(raw);
  }

  function scenarioPlan(item, scenarioName, availableGp) {
    const scenario = item?.[scenarioName] || {};
    const buyPrice = Number(scenario.buyPrice);
    const margin = Number(scenario.margin);
    const capacity = Number(item.capacityQuantity4h);
    if (!(buyPrice > 0) || !Number.isFinite(margin) || !(capacity > 0)) return null;
    let quantity = capacity;
    if (availableGp != null) quantity = Math.min(quantity, Math.floor(availableGp / buyPrice));
    quantity = Math.max(0, Math.floor(quantity));
    return {
      quantity,
      capital: quantity * buyPrice,
      profit: quantity * margin,
      buyPrice,
      sellPrice: scenario.sellPrice,
      margin,
      roi: scenario.roi
    };
  }

  function survivalText(item) {
    const stats = item.spreadStats || {};
    if (stats.profitableBucketCount == null || stats.bucketCount == null || !stats.bucketCount) return "-";
    return `${stats.profitableBucketCount}/${stats.bucketCount} (${pct.format(stats.profitableBucketPct)}%)`;
  }

  function driftText(item) {
    const drift = item.drift?.drift60m;
    const driftPct = item.drift?.drift60mPct;
    if (drift == null || driftPct == null) return "-";
    const sign = Number(drift) > 0 ? "+" : "";
    return `${sign}${gp.format(drift)} gp (${sign}${pct.format(driftPct)}%)`;
  }

  function windowHtml(title, window) {
    return `<div><h3>${esc(title)}</h3>
      <p>Passive-buy average: <strong>${gpText(window?.buyPrice)}</strong></p>
      <p>Passive-sell average: <strong>${gpText(window?.sellPrice)}</strong></p>
      <p>Tax-correct margin: <strong>${gpText(window?.margin)}</strong></p>
      <p>Passive-buy fill flow: <strong>${plainGp(window?.buyFlow)}</strong></p>
      <p>Passive-sell fill flow: <strong>${plainGp(window?.sellFlow)}</strong></p>
      <p>Balanced flow: <strong>${plainGp(window?.balancedFlow)}</strong></p>
      <p>Directional balance: <strong>${window?.flowBalancePct == null ? "-" : `${pct.format(window.flowBalancePct)}%`}</strong></p>
    </div>`;
  }

  function record(item, availableGp) {
    const expectedPlan = scenarioPlan(item, "expected", availableGp);
    const conservativePlan = scenarioPlan(item, "conservative", availableGp);
    const expectedClass = Number(expectedPlan?.profit) > 0 ? "profit" : "loss";
    const expectedMarginClass = Number(item.expected?.margin) > 0 ? "profit" : "loss";
    const conservativeClass = Number(conservativePlan?.profit) > 0 ? "profit" : "loss";
    const executionLabel = item.executionFreshness === "fresh" ? "Fresh execution" : item.executionFreshness || "Missing execution";
    return `<details class="ledger-record">
      <summary class="ledger-summary alch-grid">
        <div class="item-name"><strong>${esc(item.name)}</strong><small>${membership(item.members)} · ${esc(item.spread?.label || "Unknown")} · ${esc(executionLabel)}</small></div>
        <div class="num primary-mobile ${expectedClass}">${plainGp(expectedPlan?.profit)}</div>
        <div class="num">${plainGp(item.expected?.buyPrice)}</div>
        <div class="num">${plainGp(item.expected?.sellPrice)}</div>
        <div class="num ${expectedMarginClass}">${plainGp(item.expected?.margin)}</div>
        <div class="num desktop-secondary ${conservativeClass}">${plainGp(conservativePlan?.profit)}</div>
        <div class="num desktop-secondary">${plainGp(expectedPlan?.quantity)}</div>
        <div class="num desktop-secondary">${survivalText(item)}</div>
        <div class="num desktop-secondary">${plainGp(item.marketFlowPerHour)}</div>
        <div class="desktop-secondary">${esc(driftText(item))}</div>
      </summary>
      <div class="detail-panel">
        <div class="badge-row">${badge(membership(item.members))}${badge(item.spread?.label || "Unknown", item.spread?.state || "")}${badge(executionLabel, item.executionFreshness || "")}${badge(item.freshness?.label || "Unknown", item.freshness?.state || "")}</div>
        <div class="detail-grid">
          <div><h3>Current snapshot</h3>
            <p>Latest passive buy: <strong>${gpText(item.buyPrice)}</strong></p>
            <p>Latest passive sell: <strong>${gpText(item.sellPrice)}</strong></p>
            <p>Seller tax: <strong>${gpText(item.tax)}</strong></p>
            <p>Current margin/item: <strong>${gpText(item.margin)}</strong></p>
            <p>Current ROI: <strong>${item.roi == null ? "-" : `${pct.format(item.roi)}%`}</strong></p>
            <p>Latest low-side trade: <strong>${esc(compactAge(item.lowAge))} ago</strong></p>
            <p>Latest high-side trade: <strong>${esc(compactAge(item.highAge))} ago</strong></p>
          </div>
          <div><h3>Expected execution</h3>
            <p>Passive buy target: <strong>${gpText(item.expected?.buyPrice)}</strong></p>
            <p>Passive sell target: <strong>${gpText(item.expected?.sellPrice)}</strong></p>
            <p>Post-tax margin/item: <strong>${gpText(item.expected?.margin)}</strong></p>
            <p>ROI: <strong>${item.expected?.roi == null ? "-" : `${pct.format(item.expected.roi)}%`}</strong></p>
            <p>Planned quantity: <strong>${plainGp(expectedPlan?.quantity)}</strong></p>
            <p>Planned capital: <strong>${gpText(expectedPlan?.capital)}</strong></p>
            <p>Expected planned profit: <strong>${gpText(expectedPlan?.profit)}</strong></p>
          </div>
          <div><h3>Conservative execution</h3>
            <p>Passive buy target: <strong>${gpText(item.conservative?.buyPrice)}</strong></p>
            <p>Passive sell target: <strong>${gpText(item.conservative?.sellPrice)}</strong></p>
            <p>Post-tax margin/item: <strong>${gpText(item.conservative?.margin)}</strong></p>
            <p>ROI: <strong>${item.conservative?.roi == null ? "-" : `${pct.format(item.conservative.roi)}%`}</strong></p>
            <p>Planned quantity: <strong>${plainGp(conservativePlan?.quantity)}</strong></p>
            <p>Planned capital: <strong>${gpText(conservativePlan?.capital)}</strong></p>
            <p>Conservative planned profit: <strong>${gpText(conservativePlan?.profit)}</strong></p>
          </div>
          <div><h3>Four-hour capacity</h3>
            <p>GE buy limit: <strong>${plainGp(item.buyLimit)}</strong></p>
            <p>GE limit rate/hour: <strong>${plainGp(item.geLimitRatePerHour)}</strong></p>
            <p>Passive-buy flow/hour: <strong>${plainGp(item.buyFlowPerHour)}</strong></p>
            <p>Passive-sell flow/hour: <strong>${plainGp(item.sellFlowPerHour)}</strong></p>
            <p>Two-sided flow/hour: <strong>${plainGp(item.marketFlowPerHour)}</strong></p>
            <p>Capacity/hour: <strong>${plainGp(item.capacityPerHour)}</strong></p>
            <p>4H executable quantity ceiling: <strong>${plainGp(item.capacityQuantity4h)}</strong></p>
            <p>4H GE-limit coverage: <strong>${item.capacityCoverage4hPct == null ? "-" : `${pct.format(item.capacityCoverage4hPct)}%`}</strong></p>
          </div>
          <div><h3>Spread survival</h3>
            <p>Profitable completed buckets: <strong>${survivalText(item)}</strong></p>
            <p>Median margin: <strong>${gpText(item.spreadStats?.medianMargin)}</strong></p>
            <p>10th percentile margin: <strong>${gpText(item.spreadStats?.p10Margin)}</strong></p>
            <p>Average margin: <strong>${gpText(item.spreadStats?.averageMargin)}</strong></p>
            <p>Observed range: <strong>${item.spreadStats?.minMargin == null ? "-" : `${gp.format(item.spreadStats.minMargin)} to ${gp.format(item.spreadStats.maxMargin)} gp`}</strong></p>
          </div>
          <div><h3>Midpoint drift</h3>
            <p>Current midpoint: <strong>${gpText(item.drift?.currentMidpoint)}</strong></p>
            <p>30M midpoint: <strong>${gpText(item.drift?.midpoint30m)}</strong></p>
            <p>60M midpoint: <strong>${gpText(item.drift?.midpoint60m)}</strong></p>
            <p>30M drift: <strong>${item.drift?.drift30m == null ? "-" : `${gp.format(item.drift.drift30m)} gp`}</strong></p>
            <p>60M drift: <strong>${driftText(item)}</strong></p>
          </div>
          ${windowHtml("Bulk recent 1H", item.avg1h)}
          ${windowHtml("Bulk recent 5M", item.avg5m)}
        </div>
        <div class="calculation-block"><h3>Calculation</h3>
          <p>Current uses the latest low as the passive buy and latest high as the passive sell. Expected uses volume-weighted completed 5-minute low-side and high-side trades over a fresh 30–60 minute window. Conservative moves the buy price to the adverse low-side 90th percentile and the sell price to the adverse high-side 10th percentile.</p>
          <p>Capacity/hour is the smaller of the GE limit divided by four and observed two-sided flow/hour. The four-hour quantity ceiling is the smaller of the GE buy limit and four hours of observed two-sided flow.</p>
          <p>Available GP limits planned quantity by affordable units. It does not remove an item merely because the full market opportunity costs more than the selected bankroll.</p>
        </div>
      </div>
    </details>`;
  }

  function renderOverview() {
    const availableGp = capitalLimit();
    const persistent = items.filter(item => item.spread?.state === "persistent" && Number(item.expected?.margin) > 0);
    const ranked = [...persistent].sort((a, b) => Number(scenarioPlan(b, "expected", availableGp)?.profit ?? -Infinity) - Number(scenarioPlan(a, "expected", availableGp)?.profit ?? -Infinity));
    const leader = ranked[0];
    const leaderPlan = leader ? scenarioPlan(leader, "expected", availableGp) : null;
    setText("#flip-leader-value", leaderPlan ? `${compactGp(leaderPlan.profit)} gp` : "No signal");
    setText("#flip-leader-name", leader?.name || "No persistent spread available");
    setText("#flip-persistent-count", gp.format(persistent.length));
    setText("#flip-fresh-count", gp.format(items.filter(item => item.executionFreshness === "fresh").length));
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
    const availableGp = capitalLimit();
    const capital = document.querySelector("#flip-capital").value;
    const sort = document.querySelector("#flip-sort").value;
    const showStale = document.querySelector("#flip-stale").checked;

    let rows = items.filter(item => {
      const expectedPlan = scenarioPlan(item, "expected", availableGp);
      if (search && !item.name.toLowerCase().includes(search)) return false;
      if (members === "f2p" && item.members) return false;
      if (members === "members" && !item.members) return false;
      if (state === "persistent" && item.spread?.state !== "persistent") return false;
      if (state === "positive" && !(Number(item.margin) > 0)) return false;
      if (!showStale && item.executionFreshness !== "fresh") return false;
      if (!(Number(item.expected?.margin) >= minMargin)) return false;
      if (!(Number(item.expected?.roi) >= minRoi)) return false;
      if (minVolume > 0 && !(Number(item.marketFlowPerHour || 0) >= minVolume)) return false;
      if (availableGp != null && !(expectedPlan && expectedPlan.quantity >= 1)) return false;
      return true;
    });

    const value = item => {
      const expectedPlan = scenarioPlan(item, "expected", availableGp);
      const conservativePlan = scenarioPlan(item, "conservative", availableGp);
      return ({
        "expected-profit": expectedPlan?.profit,
        "conservative-profit": conservativePlan?.profit,
        "expected-margin": item.expected?.margin,
        roi: item.expected?.roi,
        survival: item.spreadStats?.profitableBucketPct,
        capacity: item.capacityQuantity4h,
        volume: item.marketFlowPerHour,
        drift: item.drift?.drift60m == null ? null : Math.abs(Number(item.drift.drift60m)),
        capital: expectedPlan?.capital,
        alphabetic: item.name
      })[sort];
    };
    rows.sort((a, b) => {
      if (["capital", "drift"].includes(sort)) return Number(value(a) ?? Infinity) - Number(value(b) ?? Infinity);
      if (sort === "alphabetic") return a.name.localeCompare(b.name);
      return Number(value(b) ?? -Infinity) - Number(value(a) ?? -Infinity);
    });

    const shown = rows.slice(0, DISPLAY_LIMIT);
    setText("#flip-count", rows.length > DISPLAY_LIMIT ? `${rows.length} candidates, showing first ${DISPLAY_LIMIT}` : `${rows.length} candidate${rows.length === 1 ? "" : "s"}`);
    list.innerHTML = `<div class="ledger-header alch-grid"><div>Item</div><div class="num">Expected profit</div><div class="num">Expected buy</div><div class="num">Expected sell</div><div class="num">Expected margin</div><div class="num desktop-secondary">Conservative profit</div><div class="num desktop-secondary">Planned qty</div><div class="num desktop-secondary">Profitable buckets</div><div class="num desktop-secondary">Flow/hour</div><div class="desktop-secondary">1H drift</div></div>${shown.length ? shown.map(item => record(item, availableGp)).join("") : '<p class="empty-state">No flip candidates match these filters.</p>'}`;
    syncQuery({ q: search, members, spread: state, margin: String(minMargin), roi: String(minRoi), volume: String(minVolume), capital, sort, stale: showStale ? "1" : "" });
    renderOverview();
  }

  function bindFilters() {
    const params = new URLSearchParams(location.search);
    document.querySelector("#flip-search").value = params.get("q") || "";
    if (["f2p", "members"].includes(params.get("members"))) document.querySelector(`input[name="flip-membership"][value="${params.get("members")}"]`).checked = true;
    if (["positive", "all"].includes(params.get("spread"))) document.querySelector("#flip-spread").value = params.get("spread");
    if (params.get("margin")) document.querySelector("#flip-min-margin").value = params.get("margin");
    if (params.get("roi")) document.querySelector("#flip-min-roi").value = params.get("roi");
    if (params.get("volume")) document.querySelector("#flip-min-volume").value = params.get("volume");
    if (params.get("capital") && document.querySelector(`#flip-capital option[value="${CSS.escape(params.get("capital"))}"]`)) document.querySelector("#flip-capital").value = params.get("capital");
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
