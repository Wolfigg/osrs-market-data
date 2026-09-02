(() => {
  "use strict";

  if (document.body.dataset.page !== "afk") return;

  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const esc = value => String(value ?? "").replace(/[&<>'\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[c]);
  const gpText = value => value == null ? "Unavailable" : `${gp.format(value)} gp`;

  let methods = [];
  const byId = () => new Map(methods.map(m => [m.methodId, m]));

  function confidenceText(m) {
    const c = m.fillConfidence || {};
    return c.score == null ? esc(c.label || "Unknown") : `${esc(c.label || "Unknown")} ${esc(c.score)}/100`;
  }

  function enhanceRecord(record, m) {
    const panel = record.querySelector(".detail-panel");
    if (!panel || panel.dataset.compact === "1") return;
    panel.dataset.compact = "1";
    const existing = [...panel.childNodes];
    existing.forEach(node => node.remove());

    const scenarios = m.scenarios || {};
    const sustainability = m.sustainability || {};
    const source = m.priceSource || {};
    const marketCap = m.marketCapacity || {};
    const afkQuality = m.afkQuality || {};

    const quick = document.createElement("div");
    quick.className = "method-quick";
    quick.innerHTML = `<div class="quick-meta"><strong>${esc(afkQuality.label || m.afk?.classification || "Method")}</strong>${afkQuality.score == null ? "" : `<span>${esc(afkQuality.score)}/100 AFK quality</span>`}<span class="quick-separator">·</span><span>Fill ${confidenceText(m)}</span><span class="quick-separator">·</span><span>${esc(sustainability.label || "Market unknown")}</span>${marketCap.evidence ? `<span class="quick-separator">·</span><span>${esc(marketCap.evidence)} market evidence</span>` : ""}${marketCap.cyclesPerHour == null ? "" : `<span class="quick-separator">·</span><span><strong>${gp.format(marketCap.cyclesPerHour)} cycles/h</strong> estimated executable capacity</span>`}</div>`;

    const scenario = document.createElement("div");
    scenario.className = "scenario-grid";
    scenario.innerHTML = `<div class="scenario-card"><span>Current margin</span><strong>${gpText(scenarios.currentGpPerHour)}</strong></div><div class="scenario-card"><span>Expected executable</span><strong>${gpText(scenarios.expectedGpPerHour)}</strong></div><div class="scenario-card"><span>Conservative</span><strong>${gpText(scenarios.conservativeGpPerHour)}</strong></div>`;

    const more = document.createElement("details");
    more.className = "method-more";
    const summary = document.createElement("summary");
    summary.textContent = "Requirements, recipe, calculation, liquidity and history · AFK quality";
    const content = document.createElement("div");
    content.className = "method-more-content";
    existing.forEach(node => content.appendChild(node));

    const context = document.createElement("div");
    const cadence = afkQuality.estimatedInteractionsPerHour == null ? "Unknown" : `${esc(afkQuality.estimatedInteractionsPerHour)} estimated interactions/h`;
    context.innerHTML = `<div class="afk-quality-box"><strong>AFK quality: ${esc(afkQuality.label || "Unknown")}${afkQuality.score == null ? "" : ` ${esc(afkQuality.score)}/100`}</strong><p>${cadence}. ${afkQuality.deterministicTiming ? "Timing is deterministic for the modelled workflow." : afkQuality.estimatedCadence ? "Gathering cadence is an estimate, not guaranteed idle time." : "Timing confidence is moderate."}</p></div><div class="confidence-box"><strong>Market confidence: ${confidenceText(m)}${marketCap.evidence ? ` · ${esc(marketCap.evidence)} capacity evidence` : ""}</strong><p>${esc(marketCap.basis || m.fillConfidence?.reason || "Observed directional trading is used to estimate executable capacity.")}</p></div><div class="source-box"><strong>${esc(source.provider || "RuneScape Wiki real-time prices API")}</strong><p>${esc(source.current || "Current prices from prices.runescape.wiki.")}</p></div>`;
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

  ["input", "change"].forEach(type => document.addEventListener(type, event => {
    if (event.target.matches("#afk-search,#afk-category,#afk-profit,#afk-level,#afk-type,#afk-stability,#afk-sustainability,#afk-capital,#afk-can-do,input[name='afk-membership'],.skill-level")) setTimeout(enhanceVisibleRecords, 0);
  }));

  fetch("data/afk.json", { cache: "no-store" }).then(r => r.ok ? r.json() : Promise.reject()).then(data => {
    methods = data.methods || [];
    enhanceVisibleRecords();
    const list = document.querySelector("#afk-list");
    if (list) new MutationObserver(enhanceVisibleRecords).observe(list, { childList: true, subtree: false });
  }).catch(() => {});
})();
