(() => {
  "use strict";

  const page = document.body.dataset.page;
  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const pct = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });
  const esc = v => String(v ?? "").replace(/[&<>'\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[c]);
  const plainGp = v => v == null ? "-" : gp.format(v);
  const gpText = v => v == null ? "Unavailable" : `${gp.format(v)} gp`;
  const membership = m => m ? "P2P" : "F2P";
  const badge = (text, klass="") => `<span class="badge ${esc(klass)}">${esc(text)}</span>`;
  const riskBadge = risk => badge(risk?.label || risk?.level || "Unknown", risk?.level || "");
  const stabilityBadge = stability => badge(stability?.label || "Unknown", stability?.state || "");
  const sustainabilityBadge = s => badge(s?.label || "Unknown", `sustain-${s?.state || "unknown"}`);
  const SKILL_STORAGE_KEY = "osrs-profit-finder.skill-levels.v1";

  async function loadJson(path) {
    const r = await fetch(path, { cache: "no-store" });
    if (!r.ok) throw new Error(`${path}: ${r.status}`);
    return r.json();
  }

  function relativeAge(seconds) {
    const s = Math.max(0, Number(seconds || 0));
    if (s < 60) return "Updated less than a minute ago";
    if (s < 3600) return `Updated ${Math.floor(s / 60)} min ago`;
    if (s < 86400) return `Updated ${Math.floor(s / 3600)} hr ago`;
    return `Updated ${Math.floor(s / 86400)} day${s >= 172800 ? "s" : ""} ago`;
  }

  function compactAge(timestamp, now) {
    if (!timestamp) return "pending";
    const s = Math.max(0, now - Number(timestamp));
    if (s < 60) return "<1m";
    if (s < 3600) return `${Math.floor(s / 60)}m`;
    if (s < 86400) return `${Math.floor(s / 3600)}h`;
    return `${Math.floor(s / 86400)}d`;
  }

  async function initStatus() {
    try {
      const s = await loadJson("data/status.json");
      const now = Math.floor(Date.now() / 1000);
      const liveAt = Number(s.liveGeneratedAt || s.generatedAt || now);
      const age = Math.max(Number(s.ageSeconds || 0), now - liveAt);
      const node = document.querySelector("#health-state");
      const ageState = age < 5400 ? "current" : age <= 9000 ? "delayed" : "stale";
      const state = s.state === "data_issue" ? "data_issue" : ageState;
      node.textContent = ({ current: "Current", delayed: "Delayed", stale: "Stale", data_issue: "Data issue" })[state] || "Data issue";
      node.className = `status-plaque ${state}`;
      const scanTime = new Date(liveAt * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const historyText = `History 24H/7D ${compactAge(s.shortHistoryGeneratedAt, now)} · 30D ${compactAge(s.longHistoryGeneratedAt, now)}`;
      document.querySelector("#update-age").textContent = state === "data_issue"
        ? `Last market scan ${scanTime} · data issue · ${historyText}`
        : `Last market scan ${scanTime} · ${relativeAge(age)} · ${historyText}`;
    } catch (_) {
      document.querySelector("#health-state").textContent = "Data issue";
      document.querySelector("#health-state").className = "status-plaque data_issue";
      document.querySelector("#update-age").textContent = "Status unavailable";
    }
  }

  const readRadio = name => document.querySelector(`input[name="${name}"]:checked`)?.value || "all";

  function syncQuery(values) {
    const p = new URLSearchParams();
    Object.entries(values).forEach(([key, value]) => {
      if (value != null && value !== "" && value !== "all" && value !== "profitable" && value !== "recommended" && value !== "profit-4h" && value !== "0") p.set(key, value);
    });
    history.replaceState(null, "", `${location.pathname}${p.toString() ? `?${p}` : ""}`);
  }

  function requirementsHtml(r) {
    const skills = Object.entries(r?.skills || {}).map(([name, level]) => `<li>${esc(name[0].toUpperCase() + name.slice(1))}: ${esc(level)}</li>`).join("");
    const quests = (r?.quests || []).map(x => `<li>${esc(x)}</li>`).join("");
    const equipment = (r?.equipment || []).map(x => `<li>${esc(x)}</li>`).join("");
    return `${skills ? `<h3>Skills</h3><ul class="detail-list">${skills}</ul>` : ""}${quests ? `<h3>Quests</h3><ul class="detail-list">${quests}</ul>` : ""}${equipment ? `<h3>Equipment</h3><ul class="detail-list">${equipment}</ul>` : ""}` || "<p>No additional requirements listed.</p>";
  }

  function itemsHtml(title, items) {
    return items?.length ? `<h3>${esc(title)}</h3><ul class="detail-list">${items.map(x => `<li>${esc(x.quantity)} × ${esc(x.name)}</li>`).join("")}</ul>` : "";
  }

  function loadSkillLevels() {
    try { return JSON.parse(localStorage.getItem(SKILL_STORAGE_KEY) || "{}"); }
    catch (_) { return {}; }
  }

  function saveSkillLevels() {
    const levels = {};
    document.querySelectorAll(".skill-level").forEach(input => {
      const value = Number(input.value || 0);
      if (value >= 1 && value <= 99) levels[input.dataset.skill] = value;
    });
    try { localStorage.setItem(SKILL_STORAGE_KEY, JSON.stringify(levels)); } catch (_) {}
    return levels;
  }

  function canDoBySkills(method, levels) {
    return Object.entries(method.requirements?.skills || {}).every(([skill, required]) => Number(levels[skill] || 0) >= Number(required));
  }

  function deviationText(value) {
    if (value == null) return "-";
    return `${value >= 0 ? "+" : ""}${pct.format(value)}%`;
  }

  function calculationHtml(m) {
    const e = m.economics || {};
    const inputs = (m.inputs || []).map(x => `<tr><td>${esc(x.quantity)} × ${esc(x.name)}</td><td class="num">${gpText(x.price)}</td><td class="num">${gpText(x.subtotal)}</td></tr>`).join("");
    const outputs = (m.outputs || []).map(x => `<tr><td>${esc(x.quantity)} × ${esc(x.name)}</td><td class="num">${gpText(x.gePrice)}</td><td class="num">-${gpText((x.geTaxPerItem || 0) * Number(x.quantity || 0))}</td></tr>`).join("");
    return `<div class="calculation-block"><h3>Current calculation</h3><table class="calc-table"><thead><tr><th>Input</th><th class="num">Price each</th><th class="num">Cost/cycle</th></tr></thead><tbody>${inputs || '<tr><td colspan="3">No consumed GE inputs.</td></tr>'}</tbody></table><table class="calc-table"><thead><tr><th>Output</th><th class="num">Sell each</th><th class="num">GE tax/cycle</th></tr></thead><tbody>${outputs || '<tr><td colspan="3">No output data.</td></tr>'}</tbody></table><div class="calc-equation"><span>Inputs ${gpText(e.inputGpPerCycle)}</span><span>+ fixed ${gpText(e.fixedCostGpPerCycle)}</span><span>→ net output ${gpText(e.outputNetGpPerCycle)}</span><strong>= ${gpText(e.profitPerCycle)} / cycle</strong></div><p>${plainGp(m.mechanics?.cyclesPerHour)} mechanical cycles/h → ${plainGp(m.mechanics?.cyclesPerHourByBuyLimits)} after GE limits → <strong>${gpText(m.current?.gpPerHour)} current GP/h</strong>.</p></div>`;
  }

  function liquidityHtml(m) {
    const rows = ["inputs", "outputs"].flatMap(side => (m.liquidity?.[side] || []).map(x => `<tr><td>${esc(x.name)}</td><td>${side === "inputs" ? "Input" : "Output"}</td><td class="num">${plainGp(x.unitsPerHour)}</td><td class="num">${plainGp(x.volume24h)}</td><td class="num">${x.oneHourSharePct24h == null ? "-" : `${pct.format(x.oneHourSharePct24h)}%`}</td></tr>`));
    const cap = m.marketCapacity || {};
    return `<div class="calculation-block"><h3>Sustainability & liquidity</h3><div class="badge-row">${sustainabilityBadge(m.sustainability)}</div><p>${esc(cap.basis || m.sustainability?.reasons?.[0] || "No sustainability assessment available.")}</p><table class="calc-table"><thead><tr><th>Item</th><th>Side</th><th class="num">Units/h</th><th class="num">24H volume</th><th class="num">1h share</th></tr></thead><tbody>${rows.join("") || '<tr><td colspan="5">Volume data unavailable.</td></tr>'}</tbody></table>${cap.cyclesPerHour == null ? "" : `<p>Estimated executable capacity: <strong>${plainGp(cap.cyclesPerHour)} cycles/h</strong>${cap.participationPct == null ? "" : ` at a ${pct.format(cap.participationPct)}% observed-flow participation cap`}.</p>`}</div>`;
  }

  function afkRecord(m) {
    const current = m.current?.gpPerHour;
    const expected = m.scenarios?.expectedGpPerHour ?? m.recommended?.gpPerHour;
    const cls = current != null && current < 0 ? "loss" : "profit";
    return `<details class="ledger-record" data-method-id="${esc(m.methodId)}"><summary class="ledger-summary afk-grid"><div class="method-name"><strong>${esc(m.name)}</strong><small>${esc(m.category)} · ${esc(m.afk.classification)} · ${membership(m.members)}</small></div><div class="num primary-mobile ${expected != null && expected < 0 ? "loss" : "profit"}">${plainGp(expected)}</div><div class="num ${cls}">${plainGp(current)}</div><div class="num">${m.afk.intervalSeconds == null ? "-" : `${plainGp(m.afk.intervalSeconds)}s`}</div><div>${sustainabilityBadge(m.sustainability)}</div></summary><div class="detail-panel"><div class="badge-row">${badge(m.afk.classification)}${(m.tags || []).map(t => badge(t)).join("")}${sustainabilityBadge(m.sustainability)}${stabilityBadge(m.stability)}${riskBadge(m.risk)}</div><p>${esc(m.description || m.afk.description || "")}</p><div class="detail-grid"><div>${requirementsHtml(m.requirements)}</div><div>${itemsHtml("Inputs", m.inputs)}${itemsHtml("Outputs", m.outputs)}</div><div><h3>Profit view</h3><p>Expected executable GP/h: <strong>${gpText(expected)}</strong></p><p>Current mechanical GP/h: <strong>${gpText(current)}</strong></p><p>Conservative GP/h: <strong>${gpText(m.scenarios?.conservativeGpPerHour)}</strong></p><p>Weighted historical reference: <strong>${gpText(m.recommended?.referenceGpPerHour)}</strong></p></div></div>${calculationHtml(m)}${liquidityHtml(m)}<div class="history-grid"><div class="history-cell"><span>Expected</span><strong>${gpText(expected)}</strong></div><div class="history-cell"><span>Current</span><strong>${gpText(current)}</strong></div><div class="history-cell"><span>24H</span><strong>${gpText(m.history?.["24hGpPerHour"])}</strong><small>${deviationText(m.stability?.currentVs24hPct)}</small></div><div class="history-cell"><span>7D</span><strong>${gpText(m.history?.["7dGpPerHour"])}</strong><small>${deviationText(m.stability?.currentVs7dPct)}</small></div><div class="history-cell"><span>30D</span><strong>${gpText(m.history?.["30dGpPerHour"])}</strong><small>${deviationText(m.stability?.currentVs30dPct)}</small></div></div>${m.reference ? `<a class="action-link" href="${esc(m.reference)}" target="_blank" rel="noopener noreferrer">Source / reference</a>` : ""}</div></details>`;
  }

  async function initAfk() {
    const list = document.querySelector("#afk-list");
    try {
      const data = await loadJson("data/afk.json");
      const methods = data.methods || [];
      const cat = document.querySelector("#afk-category");
      const sortNode = document.querySelector("#afk-sort");
      const params = new URLSearchParams(location.search);
      const cats = [...new Set(methods.map(m => m.category))].sort();
      cat.insertAdjacentHTML("beforeend", cats.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join(""));
      document.querySelector("#afk-search").value = params.get("q") || "";
      if (params.get("category") && cats.includes(params.get("category"))) cat.value = params.get("category");
      if (["f2p", "members"].includes(params.get("members"))) document.querySelector(`input[name="afk-membership"][value="${params.get("members")}"]`).checked = true;
      if (params.get("profit") === "all") document.querySelector("#afk-profit").value = "all";
      for (const id of ["level", "type", "stability", "sustainability", "capital"]) {
        const value = params.get(id);
        const node = document.querySelector(`#afk-${id}`);
        if (value && node?.querySelector(`option[value="${CSS.escape(value)}"]`)) node.value = value;
      }
      if (params.get("sort") && sortNode.querySelector(`option[value="${CSS.escape(params.get("sort"))}"]`)) sortNode.value = params.get("sort");
      const savedLevels = loadSkillLevels();
      document.querySelectorAll(".skill-level").forEach(input => { input.value = savedLevels[input.dataset.skill] || ""; });

      const render = () => {
        const search = document.querySelector("#afk-search").value.trim().toLowerCase();
        const category = cat.value, members = readRadio("afk-membership"), profitability = document.querySelector("#afk-profit").value;
        const level = document.querySelector("#afk-level").value, type = document.querySelector("#afk-type").value;
        const stability = document.querySelector("#afk-stability").value, sustainability = document.querySelector("#afk-sustainability").value;
        const capital = document.querySelector("#afk-capital").value, capitalLimit = capital === "all" ? null : Number(capital);
        const onlyCanDo = document.querySelector("#afk-can-do").checked, levels = saveSkillLevels(), sort = sortNode.value;
        let rows = methods.filter(m =>
          !(search && !`${m.name} ${m.category} ${(m.tags || []).join(" ")}`.toLowerCase().includes(search)) &&
          !(category !== "all" && m.category !== category) && !(members === "f2p" && m.members) && !(members === "members" && !m.members) &&
          !(profitability === "profitable" && !(m.current?.valid && Number(m.scenarios?.expectedGpPerHour ?? m.recommended?.gpPerHour) > 0)) &&
          !(level !== "all" && m.afk.classification !== level) && !(type !== "all" && !(m.tags || []).includes(type)) &&
          !(stability !== "all" && m.stability?.state !== stability) && !(sustainability !== "all" && m.sustainability?.state !== sustainability) &&
          !(capitalLimit != null && Number(m.economics?.capitalOneHour) >= capitalLimit) && !(onlyCanDo && !canDoBySkills(m, levels))
        );
        const sustainabilityRank = { strong: 7, moderate: 6, watch: 5, constrained: 4, thin: 3, limited: 2, unknown: 1 };
        const val = (m, key) => ({
          recommended: m.scenarios?.expectedGpPerHour ?? m.recommended?.gpPerHour,
          sustainability: sustainabilityRank[m.sustainability?.state] || 0,
          "gp-hour": m.current?.gpPerHour,
          "gp-24h": m.history?.["24hGpPerHour"], "gp-7d": m.history?.["7dGpPerHour"], "gp-30d": m.history?.["30dGpPerHour"],
          "gp-interaction": m.afk?.gpPerInteraction, "afk-interval": m.afk?.intervalSeconds, capital: m.economics?.capitalOneHour
        })[key];
        rows.sort((a, b) => sort === "alphabetical" ? a.name.localeCompare(b.name) : sort === "capital" ? (val(a, sort) ?? Infinity) - (val(b, sort) ?? Infinity) : (val(b, sort) ?? -Infinity) - (val(a, sort) ?? -Infinity));
        document.querySelector("#afk-count").textContent = `${rows.length} method${rows.length === 1 ? "" : "s"}`;
        list.innerHTML = `<div class="ledger-header afk-grid"><div>Method</div><div class="num">Expected GP/h</div><div class="num">Current GP/h</div><div class="num">AFK</div><div>Market capacity</div></div>${rows.length ? rows.map(afkRecord).join("") : `<p class="empty-state">No methods match these filters.</p>`}`;
        syncQuery({ q: search, category, members, profit: profitability, level, type, stability, sustainability, capital, sort });
        const requested = params.get("method");
        if (requested) list.querySelector(`[data-method-id="${CSS.escape(requested)}"]`)?.setAttribute("open", "");
      };

      document.querySelectorAll("#afk-category,#afk-profit,#afk-level,#afk-type,#afk-stability,#afk-sustainability,#afk-capital,#afk-sort,#afk-can-do,input[name='afk-membership'],.skill-level").forEach(el => el.addEventListener("change", render));
      document.querySelectorAll("#afk-search,.skill-level").forEach(el => el.addEventListener("input", render));
      render();
    } catch (_) {
      list.innerHTML = `<p class="empty-state">AFK method data could not be loaded.</p>`;
    }
  }

  function alchRecord(i) {
    const cls = i.profitPerCast != null && i.profitPerCast < 0 ? "loss" : "profit";
    return `<details class="ledger-record"><summary class="ledger-summary alch-grid"><div class="item-name"><strong>${esc(i.name)}</strong><small>${membership(i.members)} · ${esc(i.freshness)}</small></div><div class="num primary-mobile ${cls}">${plainGp(i.profit4h)}</div><div class="num">${plainGp(i.buyPrice)}</div><div class="num">${plainGp(i.highAlchValue)}</div><div class="num ${cls}">${plainGp(i.profitPerCast)}</div><div class="num desktop-secondary">${i.roi == null ? "-" : `${pct.format(i.roi)}%`}</div><div class="num desktop-secondary">${plainGp(i.quantity4h)}</div><div class="num desktop-secondary ${cls}">${plainGp(i.profit4h)}</div><div class="num desktop-secondary">${plainGp(i.capitalRequired)}</div><div class="desktop-secondary">${esc(i.freshness)}</div></summary><div class="detail-panel"><div class="badge-row">${badge(membership(i.members))}${badge(i.freshness)}${riskBadge(i.risk)}</div><div class="detail-grid"><div><h3>Current calculation</h3><p>Buy price: <strong>${gpText(i.buyPrice)}</strong></p><p>High Alch value: <strong>${gpText(i.highAlchValue)}</strong></p><p>Rune cost: <strong>${gpText(i.runeCost)}</strong></p><p>Profit/cast: <strong>${gpText(i.profitPerCast)}</strong></p></div><div><h3>Four-hour batch</h3><p>Available quantity: <strong>${plainGp(i.quantity4h)}</strong></p><p>GE buy limit: <strong>${plainGp(i.buyLimit)}</strong></p><p>Capital required: <strong>${gpText(i.capitalRequired)}</strong></p><p>Practical profit: <strong>${gpText(i.profit4h)}</strong></p></div><div><h3>Market context</h3><p>24H volume: <strong>${plainGp(i.volume24h)}</strong></p><p>24H margin: <strong>${gpText(i.history?.["24hProfitPerCast"])}</strong></p><p>7D margin: <strong>${gpText(i.history?.["7dProfitPerCast"])}</strong></p><p>30D margin: <strong>${gpText(i.history?.["30dProfitPerCast"])}</strong></p><p>${esc(i.risk?.reasons?.[0] || "No material current warning.")}</p></div></div></div></details>`;
  }

  async function initAlchemy() {
    const list = document.querySelector("#alch-list");
    try {
      const data = await loadJson("data/alchemy.json");
      const items = data.items || [], params = new URLSearchParams(location.search);
      document.querySelector("#alch-search").value = params.get("q") || "";
      if (["f2p", "members"].includes(params.get("members"))) document.querySelector(`input[name="alch-membership"][value="${params.get("members")}"]`).checked = true;
      if (params.get("profit") === "all") document.querySelector("#alch-profit").value = "all";
      if (params.get("min")) document.querySelector("#alch-min-profit").value = params.get("min");
      if (params.get("capital")) document.querySelector("#alch-capital").value = params.get("capital");
      if (params.get("sort") && document.querySelector(`#alch-sort option[value="${CSS.escape(params.get("sort"))}"]`)) document.querySelector("#alch-sort").value = params.get("sort");
      document.querySelector("#alch-unavailable").checked = params.get("unavailable") === "1";
      const render = () => {
        const search = document.querySelector("#alch-search").value.trim().toLowerCase(), members = readRadio("alch-membership"), profitability = document.querySelector("#alch-profit").value;
        const min = Number(document.querySelector("#alch-min-profit").value || 0), capital = document.querySelector("#alch-capital").value, capitalLimit = capital === "all" ? null : Number(capital);
        const sort = document.querySelector("#alch-sort").value, showUnavailable = document.querySelector("#alch-unavailable").checked;
        let rows = items.filter(i => !(search && !i.name.toLowerCase().includes(search)) && !(members === "f2p" && i.members) && !(members === "members" && !i.members) && !(!showUnavailable && i.profitPerCast == null) && !(profitability === "profitable" && !(Number(i.profitPerCast) > 0)) && !(i.profitPerCast != null && Number(i.profitPerCast) < min) && !(capitalLimit != null && (i.capitalRequired == null || Number(i.capitalRequired) >= capitalLimit)));
        const val = (i, key) => ({ "profit-4h": i.profit4h, "profit-cast": i.profitPerCast, "profit-24h": i.history?.["24hProfitPerCast"], "profit-7d": i.history?.["7dProfitPerCast"], "profit-30d": i.history?.["30dProfitPerCast"], roi: i.roi, capital: i.capitalRequired, volume: i.volume24h })[key];
        rows.sort((a, b) => sort === "capital" ? (val(a, sort) ?? Infinity) - (val(b, sort) ?? Infinity) : (val(b, sort) ?? -Infinity) - (val(a, sort) ?? -Infinity));
        document.querySelector("#alch-count").textContent = `${rows.length} candidate${rows.length === 1 ? "" : "s"}`;
        list.innerHTML = `<div class="ledger-header alch-grid"><div>Item</div><div class="num">4H profit</div><div class="num">Buy</div><div class="num">Alch</div><div class="num">Profit/cast</div><div class="num desktop-secondary">ROI</div><div class="num desktop-secondary">4H qty</div><div class="num desktop-secondary">4H profit</div><div class="num desktop-secondary">Capital</div><div class="desktop-secondary">Freshness</div></div>${rows.length ? rows.map(alchRecord).join("") : `<p class="empty-state">No High Alch candidates match these filters.</p>`}`;
        syncQuery({ q: search, members, profit: profitability, min: String(min), capital, sort, unavailable: showUnavailable ? "1" : "" });
      };
      document.querySelectorAll("#alch-profit,#alch-capital,#alch-sort,#alch-unavailable,input[name='alch-membership']").forEach(el => el.addEventListener("change", render));
      document.querySelector("#alch-search").addEventListener("input", render);
      document.querySelector("#alch-min-profit").addEventListener("input", render);
      render();
    } catch (_) {
      list.innerHTML = `<p class="empty-state">High Alch data could not be loaded.</p>`;
    }
  }

  initStatus();
  if (page === "afk") initAfk();
  if (page === "alchemy") initAlchemy();
})();
