(() => {
  "use strict";

  if (document.body.dataset.page !== "afk") return;

  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const esc = value => String(value ?? "").replace(/[&<>'\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[c]);
  const gpText = value => value == null ? "Unavailable" : `${gp.format(value)} gp`;

  const style = document.createElement("style");
  style.textContent = `
    .afk-grid{grid-template-columns:minmax(300px,2.5fr) minmax(120px,1fr) minmax(120px,1fr) minmax(80px,.65fr) minmax(125px,1fr)!important}
    .ledger-summary>div{padding:10px 12px}.ledger-record[open] .ledger-summary{border-bottom:0}.detail-panel{padding:12px 16px 14px}
    .method-quick{display:block}.scenario-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border:1px solid rgba(91,73,53,.34);margin:10px 0 8px;background:rgba(234,217,173,.35)}
    .scenario-card{padding:8px 10px;border-right:1px solid rgba(91,73,53,.25)}.scenario-card:last-child{border-right:0}.scenario-card span{display:block;color:#5b4935;font:700 .64rem/1.15 system-ui,sans-serif;text-transform:uppercase;letter-spacing:.04em}.scenario-card strong{display:block;margin-top:2px;font-size:1rem}
    .quick-meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;color:#5b4935;font:.74rem/1.3 system-ui,sans-serif}.quick-meta strong{color:#241b12}.quick-separator{opacity:.55}
    .method-more{margin-top:9px;border-top:1px solid rgba(91,73,53,.32)}.method-more>summary{cursor:pointer;list-style:none;padding:9px 1px 2px;color:#5b4935;font:700 .74rem/1.2 system-ui,sans-serif}.method-more>summary::-webkit-details-marker{display:none}.method-more>summary:before{content:"+ ";color:#6e3430}.method-more[open]>summary:before{content:"− "}
    .method-more-content{padding-top:10px}.method-more .detail-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.method-more .calculation-block{margin-top:12px}.method-more .history-grid{margin-top:12px}
    .confidence-box,.source-box,.afk-quality-box{margin:10px 0;padding:10px;border:1px solid rgba(91,73,53,.38);background:rgba(234,217,173,.35)}.confidence-box p,.source-box p,.afk-quality-box p{font-size:.82rem}
    @media(max-width:1000px){.afk-grid{grid-template-columns:minmax(240px,2fr) minmax(105px,1fr) minmax(105px,1fr) minmax(110px,1fr)!important}.afk-grid>:nth-child(5){display:none!important}.method-more .detail-grid{grid-template-columns:1fr 1fr}}
    @media(max-width:680px){.afk-grid{grid-template-columns:minmax(0,1.7fr) minmax(100px,.8fr)!important}.afk-grid>:not(:nth-child(1)):not(:nth-child(2)){display:none!important}.ledger-summary>div{padding:9px 10px}.detail-panel{padding:10px 11px 12px}.scenario-grid{grid-template-columns:1fr 1fr 1fr}.scenario-card{padding:7px 6px}.scenario-card strong{font-size:.86rem}.method-more .detail-grid{grid-template-columns:1fr}.method-more .calc-table{font-size:.76rem}}
  `;
  document.head.appendChild(style);

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
