(() => {
  "use strict";

  if (document.body.dataset.page !== "afk") return;

  const FAVOURITES_KEY = "osrs-profit-finder.favourites.v1";
  const COMPARE_KEY = "osrs-profit-finder.compare.v1";
  const MAX_COMPARE = 4;
  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const esc = value => String(value ?? "").replace(/[&<>'\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[c]);
  const gpText = value => value == null ? "Unavailable" : `${gp.format(value)} gp`;

  const readSet = key => {
    try { return new Set(JSON.parse(localStorage.getItem(key) || "[]")); }
    catch (_) { return new Set(); }
  };
  const writeSet = (key, values) => localStorage.setItem(key, JSON.stringify([...values]));

  const style = document.createElement("style");
  style.textContent = `
    /* Wave 8 compact information hierarchy. The data is still available, but
       secondary analysis is no longer forced into every open method row. */
    .afk-grid{grid-template-columns:minmax(280px,2.3fr) repeat(5,minmax(96px,1fr))!important}
    .afk-grid>:nth-child(6),.afk-grid>:nth-child(8),.afk-grid>:nth-child(9),.afk-grid>:nth-child(10){display:none!important}
    .ledger-summary>div{padding:10px 12px}
    .ledger-record[open] .ledger-summary{border-bottom:0}
    .detail-panel{padding:12px 16px 14px}
    .method-quick{display:grid;grid-template-columns:minmax(0,1.5fr) auto;gap:12px;align-items:start}
    .method-actions{display:flex;gap:6px;justify-content:flex-end}
    .method-action{border:1px solid #665f54;background:#ead9ad;padding:6px 8px;cursor:pointer;font:700 .72rem/1.1 system-ui,sans-serif}
    .method-action.active{background:#3a2819;color:#f0dfb9}
    .scenario-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border:1px solid rgba(91,73,53,.34);margin:10px 0 8px;background:rgba(234,217,173,.35)}
    .scenario-card{padding:8px 10px;border-right:1px solid rgba(91,73,53,.25)}
    .scenario-card:last-child{border-right:0}.scenario-card span{display:block;color:#5b4935;font:700 .64rem/1.15 system-ui,sans-serif;text-transform:uppercase;letter-spacing:.04em}
    .scenario-card strong{display:block;margin-top:2px;font-size:1rem}.scenario-card small{display:none}
    .quick-meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;color:#5b4935;font:.74rem/1.3 system-ui,sans-serif}
    .quick-meta strong{color:#241b12}.quick-separator{opacity:.55}
    .method-more{margin-top:9px;border-top:1px solid rgba(91,73,53,.32)}
    .method-more>summary{cursor:pointer;list-style:none;padding:9px 1px 2px;color:#5b4935;font:700 .74rem/1.2 system-ui,sans-serif}
    .method-more>summary::-webkit-details-marker{display:none}.method-more>summary:before{content:"+ ";color:#6e3430}.method-more[open]>summary:before{content:"− "}
    .method-more-content{padding-top:10px}.method-more .detail-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
    .method-more .calculation-block{margin-top:12px}.method-more .history-grid{margin-top:12px}
    .confidence-box,.source-box{margin:10px 0;padding:10px;border:1px solid rgba(91,73,53,.38);background:rgba(234,217,173,.35)}
    .confidence-box p,.source-box p{font-size:.82rem}
    .local-tools{margin:8px 0 12px;border:1px solid rgba(91,73,53,.42);background:rgba(234,217,173,.42)}
    .local-tools>summary{cursor:pointer;padding:9px 12px;font:700 .78rem/1.2 system-ui,sans-serif;color:#5b4935}
    .local-tools-body{padding:0 12px 12px}.utility-heading{display:flex;justify-content:space-between;gap:10px;align-items:center}.utility-heading h2{margin:8px 0 4px;font-size:.95rem}
    .watchlist-list{display:flex;flex-wrap:wrap;gap:6px;margin:5px 0 10px}.watch-chip{border:1px solid #665f54;background:#ead9ad;padding:5px 7px;cursor:pointer}
    .compare-table{width:100%;border-collapse:collapse;margin-top:6px}.compare-table th,.compare-table td{padding:6px;border-bottom:1px solid rgba(91,73,53,.3);text-align:right;font-size:.8rem}.compare-table th:first-child,.compare-table td:first-child{text-align:left}.compare-empty{color:#5b4935;font-size:.82rem}
    @media(max-width:1120px){.afk-grid{grid-template-columns:minmax(220px,1.8fr) repeat(4,minmax(90px,1fr))!important}.afk-grid>:nth-child(7){display:none!important}.method-more .detail-grid{grid-template-columns:1fr 1fr}}
    @media(max-width:760px){.afk-grid{grid-template-columns:minmax(0,1.5fr) minmax(88px,.8fr)!important}.afk-grid>:not(:nth-child(1)):not(:nth-child(2)){display:none!important}.ledger-summary>div{padding:9px 10px}.detail-panel{padding:10px 11px 12px}.method-quick{grid-template-columns:1fr}.method-actions{justify-content:flex-start}.scenario-grid{grid-template-columns:1fr 1fr 1fr}.scenario-card{padding:7px 6px}.scenario-card strong{font-size:.88rem}.method-more .detail-grid{grid-template-columns:1fr}.method-more .calc-table{font-size:.76rem}.compare-table{min-width:570px}.local-tools-body{overflow-x:auto}}
  `;
  document.head.appendChild(style);

  let methods = [];
  const favourites = readSet(FAVOURITES_KEY);
  const compare = readSet(COMPARE_KEY);
  const byId = () => new Map(methods.map(m => [m.methodId, m]));

  function confidenceText(m) {
    const c = m.fillConfidence || {};
    return c.score == null ? esc(c.label || "Unknown") : `${esc(c.label || "Unknown")} ${esc(c.score)}/100`;
  }

  function ensureUtilityPanels() {
    const filters = document.querySelector(".filter-frame");
    if (!filters || document.querySelector("#local-tools")) return;
    const section = document.createElement("details");
    section.id = "local-tools";
    section.className = "local-tools";
    section.innerHTML = `<summary id="local-tools-summary">Saved & compare</summary><div class="local-tools-body"><div class="utility-heading"><h2>Favourites</h2><span class="muted">Stored in this browser</span></div><div id="watchlist-list" class="watchlist-list"></div><div class="utility-heading"><h2>Compare methods</h2><span class="muted">Up to ${MAX_COMPARE}</span></div><div id="compare-content"></div></div>`;
    filters.insertAdjacentElement("afterend", section);
  }

  function renderUtilityPanels() {
    ensureUtilityPanels();
    const map = byId();
    const summary = document.querySelector("#local-tools-summary");
    if (summary) summary.textContent = `Saved & compare · ${favourites.size} saved · ${compare.size} comparing`;
    const watch = document.querySelector("#watchlist-list");
    if (watch) {
      const rows = [...favourites].map(id => map.get(id)).filter(Boolean);
      watch.innerHTML = rows.length ? rows.map(m => `<button type="button" class="watch-chip" data-open-method="${esc(m.methodId)}">${esc(m.name)}</button>`).join("") : `<span class="compare-empty">No favourites yet.</span>`;
    }
    const content = document.querySelector("#compare-content");
    if (content) {
      const rows = [...compare].map(id => map.get(id)).filter(Boolean);
      content.innerHTML = rows.length ? `<table class="compare-table"><thead><tr><th>Method</th><th>Current</th><th>Expected</th><th>Conservative</th><th>Fill</th><th>AFK</th></tr></thead><tbody>${rows.map(m => `<tr><td>${esc(m.name)}</td><td>${gpText(m.scenarios?.currentGpPerHour)}</td><td>${gpText(m.scenarios?.expectedGpPerHour)}</td><td>${gpText(m.scenarios?.conservativeGpPerHour)}</td><td>${confidenceText(m)}</td><td>${m.afk?.intervalSeconds == null ? "-" : `${esc(m.afk.intervalSeconds)}s`}</td></tr>`).join("")}</tbody></table>` : `<p class="compare-empty">Open a method and choose Compare.</p>`;
    }
  }

  function enhanceRecord(record, m) {
    const panel = record.querySelector(".detail-panel");
    if (!panel || panel.dataset.compact === "1") return;
    panel.dataset.compact = "1";

    const existing = [...panel.childNodes];
    existing.forEach(node => node.remove());

    const scenarios = m.scenarios || {};
    const confidence = m.fillConfidence || {};
    const source = m.priceSource || {};
    const sustainability = m.sustainability || {};

    const quick = document.createElement("div");
    quick.className = "method-quick";
    quick.innerHTML = `<div><div class="quick-meta"><strong>${esc(m.afk?.classification || "Method")}</strong><span class="quick-separator">·</span><span>Fill ${confidenceText(m)}</span><span class="quick-separator">·</span><span>${esc(sustainability.label || "Market unknown")}</span>${m.economics?.capitalOneHour == null ? "" : `<span class="quick-separator">·</span><span>${gpText(m.economics.capitalOneHour)} / 1h capital</span>`}</div></div><div class="method-actions"><button type="button" class="method-action favourite-action ${favourites.has(m.methodId) ? "active" : ""}" data-favourite="${esc(m.methodId)}">${favourites.has(m.methodId) ? "Saved" : "Save"}</button><button type="button" class="method-action compare-action ${compare.has(m.methodId) ? "active" : ""}" data-compare="${esc(m.methodId)}">${compare.has(m.methodId) ? "Comparing" : "Compare"}</button></div>`;

    const scenario = document.createElement("div");
    scenario.className = "scenario-grid";
    scenario.innerHTML = `<div class="scenario-card"><span>Current</span><strong>${gpText(scenarios.currentGpPerHour)}</strong></div><div class="scenario-card"><span>Expected</span><strong>${gpText(scenarios.expectedGpPerHour)}</strong></div><div class="scenario-card"><span>Conservative</span><strong>${gpText(scenarios.conservativeGpPerHour)}</strong></div>`;

    const more = document.createElement("details");
    more.className = "method-more";
    const summary = document.createElement("summary");
    summary.textContent = "Full breakdown: requirements, recipe, calculation, liquidity and history";
    const content = document.createElement("div");
    content.className = "method-more-content";
    existing.forEach(node => content.appendChild(node));

    const context = document.createElement("div");
    context.innerHTML = `<div class="confidence-box"><strong>Fill confidence: ${confidenceText(m)}</strong><p>${esc(confidence.reason || "Observed market activity is a liquidity proxy, not guaranteed GE depth.")}</p></div><div class="source-box"><strong>${esc(source.provider || "OSRS Wiki Prices / RuneLite")}</strong><p>${esc(source.current || "Current observed market prices.")}</p></div>`;
    content.prepend(...context.childNodes);
    more.append(summary, content);
    panel.append(quick, scenario, more);
  }

  function enhanceVisibleRecords() {
    const map = byId();
    document.querySelectorAll("#afk-list [data-method-id]").forEach(record => {
      const method = map.get(record.dataset.methodId);
      if (method) enhanceRecord(record, method);
    });
  }

  document.addEventListener("click", event => {
    const favouriteButton = event.target.closest("[data-favourite]");
    if (favouriteButton) {
      const id = favouriteButton.dataset.favourite;
      favourites.has(id) ? favourites.delete(id) : favourites.add(id);
      writeSet(FAVOURITES_KEY, favourites);
      favouriteButton.classList.toggle("active", favourites.has(id));
      favouriteButton.textContent = favourites.has(id) ? "Saved" : "Save";
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
    if (event.target.matches("#afk-search,#afk-category,#afk-profit,#afk-level,#afk-type,#afk-stability,#afk-sustainability,#afk-capital,#afk-can-do,input[name='afk-membership'],.skill-level")) setTimeout(enhanceVisibleRecords, 0);
  }));

  fetch("data/afk.json", { cache: "no-store" }).then(r => r.ok ? r.json() : Promise.reject()).then(data => {
    methods = data.methods || [];
    renderUtilityPanels();
    enhanceVisibleRecords();
    const list = document.querySelector("#afk-list");
    if (list) new MutationObserver(enhanceVisibleRecords).observe(list, { childList: true, subtree: false });
  }).catch(() => {});
})();
