(() => {
  "use strict";

  if (document.body.dataset.page !== "afk") return;

  const FAVOURITES_KEY = "osrs-profit-finder.favourites.v1";
  const COMPARE_KEY = "osrs-profit-finder.compare.v1";
  const MAX_COMPARE = 4;
  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const esc = (value) => String(value ?? "").replace(/[&<>'\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[c]);
  const gpText = value => value == null ? "Unavailable" : `${gp.format(value)} gp`;
  const plainGp = value => value == null ? "-" : gp.format(value);

  const readSet = key => {
    try { return new Set(JSON.parse(localStorage.getItem(key) || "[]")); }
    catch (_) { return new Set(); }
  };
  const writeSet = (key, values) => localStorage.setItem(key, JSON.stringify([...values]));

  const style = document.createElement("style");
  style.textContent = `
    .method-actions{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}.method-action{border:1px solid #665f54;background:#ead9ad;padding:7px 9px;cursor:pointer;font:700 .75rem/1.1 system-ui,sans-serif}.method-action.active{background:#3a2819;color:#f0dfb9}.scenario-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border:1px solid rgba(91,73,53,.4);margin:14px 0}.scenario-card{padding:10px;border-right:1px solid rgba(91,73,53,.3)}.scenario-card:last-child{border-right:0}.scenario-card span,.source-box span{display:block;color:#5b4935;font:700 .68rem/1.2 system-ui,sans-serif;text-transform:uppercase}.scenario-card strong{display:block;margin-top:4px;font-size:1.05rem}.confidence-box,.source-box,.watchlist-panel,.compare-panel{margin:12px 0;padding:12px;border:1px solid rgba(91,73,53,.45);background:rgba(234,217,173,.45)}.confidence-box strong{font-size:1.05rem}.watchlist-list{display:flex;flex-wrap:wrap;gap:7px;margin-top:8px}.watch-chip{border:1px solid #665f54;background:#ead9ad;padding:6px 8px;cursor:pointer}.compare-table{width:100%;border-collapse:collapse;margin-top:8px}.compare-table th,.compare-table td{padding:7px;border-bottom:1px solid rgba(91,73,53,.35);text-align:right}.compare-table th:first-child,.compare-table td:first-child{text-align:left}.compare-empty{color:#5b4935}.utility-heading{display:flex;justify-content:space-between;gap:12px;align-items:center}.utility-heading h2{margin:0;font-size:1rem}@media(max-width:760px){.scenario-grid{grid-template-columns:1fr}.scenario-card{border-right:0;border-bottom:1px solid rgba(91,73,53,.3)}.compare-panel{overflow-x:auto}.compare-table{min-width:620px}}
  `;
  document.head.appendChild(style);

  let methods = [];
  const byId = () => new Map(methods.map(m => [m.methodId, m]));
  const favourites = readSet(FAVOURITES_KEY);
  const compare = readSet(COMPARE_KEY);

  function confidenceText(m) {
    const c = m.fillConfidence || {};
    return c.score == null ? esc(c.label || "Unknown") : `${esc(c.label)} (${esc(c.score)}/100)`;
  }

  function correctedSessionPlan(m, bankroll, hours) {
    const mechanical = Number(m.mechanics?.cyclesPerHour || 0);
    const geRate = Number(m.mechanics?.cyclesPerHourByBuyLimits ?? mechanical);
    const cost = Number(m.economics?.capitalPerCycle || 0);
    const profitPerCycle = m.economics?.profitPerCycle == null ? null : Number(m.economics.profitPerCycle);
    const turnoverHours = Math.max(0.25, Number(m.fillConfidence?.turnoverHours || 1));
    if (!(bankroll > 0) || !(hours > 0) || profitPerCycle == null || !m.current?.valid) {
      return { active: false, profit: null, cyclesPerHour: 0, workingCapital: null, turnoverHours, limitingFactor: null };
    }
    const bankrollRate = cost > 0 ? bankroll / (cost * turnoverHours) : Infinity;
    const cycles = Math.max(0, Math.min(mechanical, geRate, bankrollRate));
    let limitingFactor = "mechanics";
    if (bankrollRate <= cycles + 1e-9 && bankrollRate < mechanical - 1e-9 && bankrollRate < geRate - 1e-9) limitingFactor = "bankroll_turnover";
    else if (geRate <= cycles + 1e-9 && geRate < mechanical - 1e-9) limitingFactor = "ge_buy_limit";
    else if (["low", "very_low"].includes(m.fillConfidence?.state)) limitingFactor = "fill_confidence";
    return {
      active: true,
      cyclesPerHour: cycles,
      gpPerHour: profitPerCycle * cycles,
      profit: profitPerCycle * cycles * hours,
      workingCapital: cost > 0 ? cost * cycles * turnoverHours : 0,
      turnoverHours,
      limitingFactor,
    };
  }

  function ensureUtilityPanels() {
    const filters = document.querySelector(".filter-frame");
    if (!filters || document.querySelector("#local-tools")) return;
    const section = document.createElement("section");
    section.id = "local-tools";
    section.innerHTML = `
      <div class="watchlist-panel"><div class="utility-heading"><h2>Favourites</h2><span class="muted">Saved only in this browser</span></div><div id="watchlist-list" class="watchlist-list"></div></div>
      <div class="compare-panel"><div class="utility-heading"><h2>Compare methods</h2><span class="muted">Select up to ${MAX_COMPARE}</span></div><div id="compare-content"></div></div>`;
    filters.insertAdjacentElement("afterend", section);
  }

  function renderUtilityPanels() {
    ensureUtilityPanels();
    const map = byId();
    const watch = document.querySelector("#watchlist-list");
    if (watch) {
      const rows = [...favourites].map(id => map.get(id)).filter(Boolean);
      watch.innerHTML = rows.length ? rows.map(m => `<button type="button" class="watch-chip" data-open-method="${esc(m.methodId)}">${esc(m.name)}</button>`).join("") : `<span class="compare-empty">No favourites yet.</span>`;
    }
    const content = document.querySelector("#compare-content");
    if (content) {
      const rows = [...compare].map(id => map.get(id)).filter(Boolean);
      content.innerHTML = rows.length ? `<table class="compare-table"><thead><tr><th>Method</th><th>Current</th><th>Expected</th><th>Conservative</th><th>Fill confidence</th><th>AFK</th></tr></thead><tbody>${rows.map(m => `<tr><td>${esc(m.name)}</td><td>${gpText(m.scenarios?.currentGpPerHour)}</td><td>${gpText(m.scenarios?.expectedGpPerHour)}</td><td>${gpText(m.scenarios?.conservativeGpPerHour)}</td><td>${confidenceText(m)}</td><td>${m.afk?.intervalSeconds == null ? "-" : `${esc(m.afk.intervalSeconds)}s`}</td></tr>`).join("")}</tbody></table>` : `<p class="compare-empty">Use Compare on method details to build a side-by-side view.</p>`;
    }
  }

  function enhanceRecord(record, m) {
    const panel = record.querySelector(".detail-panel");
    if (!panel || panel.querySelector(".method-actions")) return;
    const scenarios = m.scenarios || {};
    const confidence = m.fillConfidence || {};
    const maxShare = confidence.maxDirectionalSharePct24h;
    const source = m.priceSource || {};
    const controls = document.createElement("div");
    controls.innerHTML = `
      <div class="method-actions">
        <button type="button" class="method-action favourite-action ${favourites.has(m.methodId) ? "active" : ""}" data-favourite="${esc(m.methodId)}">${favourites.has(m.methodId) ? "Favourited" : "Add favourite"}</button>
        <button type="button" class="method-action compare-action ${compare.has(m.methodId) ? "active" : ""}" data-compare="${esc(m.methodId)}">${compare.has(m.methodId) ? "Comparing" : "Compare"}</button>
      </div>
      <div class="scenario-grid">
        <div class="scenario-card"><span>Current</span><strong>${gpText(scenarios.currentGpPerHour)}</strong><small>Latest executable-price estimate</small></div>
        <div class="scenario-card"><span>Expected</span><strong>${gpText(scenarios.expectedGpPerHour)}</strong><small>Current plus historical context</small></div>
        <div class="scenario-card"><span>Conservative</span><strong>${gpText(scenarios.conservativeGpPerHour)}</strong><small>Lowest available reference</small></div>
      </div>
      <div class="confidence-box"><span class="eyebrow">Fill confidence</span><strong>${confidenceText(m)}</strong><p>${maxShare == null ? "Directional volume unavailable." : `Peak required-side share: ${Number(maxShare).toFixed(1)}% of observed 24H directional volume.`}</p><p class="muted">${esc(confidence.reason || "Observed market activity is a proxy, not guaranteed GE depth.")}</p></div>
      <div class="source-box"><span>Price source</span><strong>${esc(source.provider || "OSRS Wiki Prices / RuneLite")}</strong><p>${esc(source.current || "Current observed market prices.")}</p><p class="muted">Expected: ${esc(source.expected || "Historical reference blend.")} Conservative: ${esc(source.conservative || "Lower-bound reference.")}</p></div>`;
    panel.prepend(...controls.childNodes);
  }

  function enhanceVisibleRecords() {
    const map = byId();
    document.querySelectorAll("#afk-list [data-method-id]").forEach(record => {
      const method = map.get(record.dataset.methodId);
      if (method) enhanceRecord(record, method);
    });
  }

  function applyPlannerV2() {
    if (!methods.length) return;
    const bankroll = Math.max(0, Number(document.querySelector("#planner-bankroll")?.value || 0));
    const hours = Math.min(24, Math.max(0.25, Number(document.querySelector("#planner-hours")?.value || 4)));
    const map = byId();
    const visible = [...document.querySelectorAll("#afk-list [data-method-id]")];
    const planned = visible.map(record => {
      const method = map.get(record.dataset.methodId);
      const plan = method ? correctedSessionPlan(method, bankroll, hours) : null;
      if (plan) {
        const cell = record.querySelector(".session-column");
        if (cell) cell.textContent = plainGp(plan.profit);
        record.dataset.correctedSessionProfit = plan.profit == null ? "" : String(plan.profit);
        const box = record.querySelector(".confidence-box");
        if (box && plan.active && !box.querySelector(".planner-v2-note")) {
          box.insertAdjacentHTML("beforeend", `<p class="planner-v2-note"><strong>Bankroll model:</strong> ${gpText(plan.workingCapital)} tied up across an estimated ${plan.turnoverHours}h market-turnover window.</p>`);
        }
      }
      return { record, method, plan };
    });

    const summary = document.querySelector("#planner-summary");
    if (summary && bankroll > 0) {
      const best = planned.filter(row => row.plan?.profit != null).sort((a, b) => b.plan.profit - a.plan.profit)[0];
      summary.textContent = best ? `Best shown: ${best.method.name} · ${gpText(best.plan.profit)} over ${hours}h` : "No displayed method is fundable with the current filters.";
    }

    if (document.querySelector("#afk-sort")?.value === "session-profit") {
      const sorted = [...planned].sort((a, b) => (b.plan?.profit ?? -Infinity) - (a.plan?.profit ?? -Infinity));
      const currentIds = visible.map(x => x.dataset.methodId).join("|");
      const sortedIds = sorted.map(x => x.record.dataset.methodId).join("|");
      if (currentIds !== sortedIds) sorted.forEach(row => row.record.parentNode?.appendChild(row.record));
    }
  }

  document.addEventListener("click", event => {
    const favouriteButton = event.target.closest("[data-favourite]");
    if (favouriteButton) {
      const id = favouriteButton.dataset.favourite;
      favourites.has(id) ? favourites.delete(id) : favourites.add(id);
      writeSet(FAVOURITES_KEY, favourites);
      favouriteButton.classList.toggle("active", favourites.has(id));
      favouriteButton.textContent = favourites.has(id) ? "Favourited" : "Add favourite";
      renderUtilityPanels();
      return;
    }
    const compareButton = event.target.closest("[data-compare]");
    if (compareButton) {
      const id = compareButton.dataset.compare;
      if (compare.has(id)) compare.delete(id);
      else if (compare.size < MAX_COMPARE) compare.add(id);
      writeSet(COMPARE_KEY, compare);
      document.querySelectorAll(`[data-compare="${CSS.escape(id)}"]`).forEach(button => {
        button.classList.toggle("active", compare.has(id));
        button.textContent = compare.has(id) ? "Comparing" : "Compare";
      });
      renderUtilityPanels();
      return;
    }
    const open = event.target.closest("[data-open-method]");
    if (open) {
      const record = document.querySelector(`[data-method-id="${CSS.escape(open.dataset.openMethod)}"]`);
      if (record) { record.open = true; record.scrollIntoView({ behavior: "smooth", block: "start" }); }
    }
  });

  ["input", "change"].forEach(type => document.addEventListener(type, event => {
    if (event.target.matches("#planner-bankroll,#planner-hours,#afk-sort,#afk-search,#afk-category,#afk-profit,#afk-level,#afk-type,#afk-stability,#afk-sustainability,#afk-capital,#afk-can-do,input[name='afk-membership'],.skill-level")) {
      setTimeout(() => { enhanceVisibleRecords(); applyPlannerV2(); }, 0);
    }
  }));

  fetch("data/afk.json", { cache: "no-store" }).then(r => r.ok ? r.json() : Promise.reject()).then(data => {
    methods = data.methods || [];
    renderUtilityPanels();
    enhanceVisibleRecords();
    applyPlannerV2();
    const list = document.querySelector("#afk-list");
    if (list) new MutationObserver(() => { enhanceVisibleRecords(); applyPlannerV2(); }).observe(list, { childList: true, subtree: false });
  }).catch(() => {});
})();
