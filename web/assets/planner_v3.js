(() => {
  "use strict";
  if (document.body.dataset.page !== "afk") return;

  const INVENTORY_KEY = "osrs-profit-finder.owned-inputs.v1";
  const PLANNER_KEY = "osrs-profit-finder.session-planner.v1";
  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, Number(v) || 0));
  const finite = value => Number.isFinite(Number(value)) ? Number(value) : null;

  // A visible placeholder looked like an entered value while the old planner
  // treated it as zero. Seed a real 2m GP default only for first-time users.
  try {
    const saved = JSON.parse(localStorage.getItem(PLANNER_KEY) || "null");
    if (!saved || !(Number(saved.bankroll) > 0)) {
      localStorage.setItem(PLANNER_KEY, JSON.stringify({ bankroll: 2000000, hours: Number(saved?.hours) > 0 ? Number(saved.hours) : 4 }));
    }
  } catch (_) {
    localStorage.setItem(PLANNER_KEY, JSON.stringify({ bankroll: 2000000, hours: 4 }));
  }

  function loadInventory() {
    try { return JSON.parse(localStorage.getItem(INVENTORY_KEY) || "{}"); }
    catch (_) { return {}; }
  }
  function saveInventory(value) { localStorage.setItem(INVENTORY_KEY, JSON.stringify(value)); }

  function directionalRate(method, side) {
    const rows = method.liquidity?.[side] || [];
    const rates = rows.map(row => finite(row.directionalVolume24h)).filter(v => v != null).map(v => v / 24);
    return rates.length ? Math.min(...rates) : Infinity;
  }

  function geRate(method) {
    const mechanical = Number(method.mechanics?.cyclesPerHour || 0);
    const limited = finite(method.mechanics?.cyclesPerHourByBuyLimits);
    return limited == null ? mechanical : limited;
  }

  function ownedEquivalentUnits(method, inventory) {
    const inputs = method.inputs || [];
    if (!inputs.length) return 0;
    let units = Infinity;
    for (const input of inputs) {
      const qty = Math.max(0, Number(input.quantity || 0));
      if (!qty) continue;
      const owned = Math.max(0, Number(inventory[String(input.itemId)] || 0));
      units = Math.min(units, owned / qty);
    }
    return units === Infinity ? 0 : units;
  }

  function sessionPlan(method, bankroll, hours, inventory) {
    const duration = clamp(hours, 0.25, 24);
    const productionRate = Math.max(0, Number(method.mechanics?.cyclesPerHour || 0));
    const inputCost = Math.max(0, Number(method.economics?.capitalPerCycle || 0));
    const profitPerUnit = finite(method.economics?.profitPerCycle);
    const outputValue = Math.max(0, Number(method.economics?.outputNetGpPerCycle || inputCost + (profitPerUnit || 0)));
    const inputFillRate = directionalRate(method, "inputs");
    const outputSellRate = directionalRate(method, "outputs");
    const buyLimitRate = Math.max(0, geRate(method));
    const owned = ownedEquivalentUnits(method, inventory);
    const fillDelay = Math.max(0, Number(method.fillConfidence?.inputFillDelayHours || 0));
    const sellDelay = Math.max(0.25, Number(method.fillConfidence?.turnoverHours || 1));

    if (!method.current?.valid || profitPerUnit == null || productionRate <= 0 || duration <= 0) {
      return { valid: false, profit: null, limitingFactor: "unavailable" };
    }

    const activeWindow = Math.max(0, duration - fillDelay);
    const liquidityRate = Math.min(productionRate, inputFillRate, outputSellRate, buyLimitRate || productionRate);
    const concurrencyHours = Math.max(1 / productionRate, sellDelay + 1 / productionRate);
    const cashFinancedUnits = inputCost > 0 ? Math.max(0, bankroll) / inputCost : Infinity;
    const bankrollRate = cashFinancedUnits === Infinity ? Infinity : cashFinancedUnits / concurrencyHours;
    const marketUnits = liquidityRate * activeWindow;
    const ownedUsed = Math.min(owned, marketUnits);
    const remaining = Math.max(0, marketUnits - ownedUsed);
    const cashUnits = Math.min(remaining, bankrollRate * activeWindow);
    const processedUnits = ownedUsed + cashUnits;
    const soldCapacity = outputSellRate === Infinity ? processedUnits : outputSellRate * Math.max(0, activeWindow - sellDelay);
    const unsoldUnits = Math.max(0, processedUnits - soldCapacity);
    const capitalLocked = unsoldUnits * outputValue;
    const cashPurchased = Math.max(0, processedUnits - ownedUsed);
    const incrementalCash = Math.min(Math.max(0, bankroll), cashPurchased * inputCost);
    const profit = processedUnits * profitPerUnit;
    const idleHours = Math.max(0, duration - processedUnits / productionRate);

    const candidates = [
      ["production", productionRate], ["input_fill", inputFillRate], ["output_sell", outputSellRate],
      ["ge_buy_limit", buyLimitRate || Infinity], ["bankroll", owned >= marketUnits ? Infinity : bankrollRate],
    ].filter(([, value]) => Number.isFinite(value));
    let limitingFactor = candidates.length ? candidates.sort((a,b) => a[1]-b[1])[0][0] : "production";
    if (fillDelay >= duration) limitingFactor = "input_fill_delay";

    return { valid: true, profit, processedUnits, gpPerHour: profit / duration, capitalLocked, incrementalCash, ownedUsed, idleHours, limitingFactor, sellDelay };
  }

  let methods = [];
  let inventory = loadInventory();

  function ensureInventoryPanel() {
    if (document.querySelector("#owned-input-panel")) return;
    const planner = document.querySelector(".planner-frame");
    if (!planner) return;
    const details = document.createElement("details");
    details.id = "owned-input-panel";
    details.className = "owned-input-panel";
    details.innerHTML = `<summary><strong>Owned input items</strong> <span class="muted">optional</span></summary><p class="muted">Only add items already in your bank when you want the planner to model cash you do not need to spend again.</p><div id="owned-input-list" class="owned-input-list"></div>`;
    planner.appendChild(details);
  }

  function renderInventoryInputs() {
    ensureInventoryPanel();
    const root = document.querySelector("#owned-input-list");
    if (!root) return;
    const seen = new Map();
    methods.forEach(method => (method.inputs || []).forEach(item => {
      if (item.itemId && !seen.has(item.itemId)) seen.set(item.itemId, item);
    }));
    root.innerHTML = [...seen.values()].sort((a,b) => String(a.name).localeCompare(String(b.name))).map(item => `<label class="field owned-input"><span>${String(item.name || item.itemId)}</span><input type="number" min="0" step="1" data-owned-item="${item.itemId}" value="${Math.max(0, Number(inventory[String(item.itemId)] || 0))}"></label>`).join("");
  }

  function compactPlanNote(record, plan, hours) {
    record.querySelectorAll(".planner-v3-inline").forEach(node => node.remove());
    if (!plan?.valid) return;
    const quick = record.querySelector(".quick-meta");
    if (quick) {
      quick.insertAdjacentHTML("beforeend", `<span class="quick-separator planner-v3-inline">·</span><span class="planner-v3-inline"><strong>My ${hours}h: ${gp.format(plan.profit)} gp</strong> · ${plan.limitingFactor.replaceAll("_", " ")}</span>`);
      return;
    }
    const panel = record.querySelector(".detail-panel");
    if (panel) panel.insertAdjacentHTML("afterbegin", `<p class="planner-v3-inline"><strong>My ${hours}h session: ${gp.format(plan.profit)} gp</strong> · limiter ${plan.limitingFactor.replaceAll("_", " ")}.</p>`);
  }

  function apply() {
    if (!methods.length) return;
    const bankrollNode = document.querySelector("#planner-bankroll");
    const hoursNode = document.querySelector("#planner-hours");
    if (bankrollNode && !(Number(bankrollNode.value) > 0)) bankrollNode.value = "2000000";
    const bankroll = Math.max(0, Number(bankrollNode?.value || 2000000));
    const hours = clamp(hoursNode?.value || 4, 0.25, 24);
    const map = new Map(methods.map(m => [m.methodId, m]));
    const rows = [...document.querySelectorAll("#afk-list [data-method-id]")].map(record => {
      const method = map.get(record.dataset.methodId);
      const plan = method ? sessionPlan(method, bankroll, hours, inventory) : null;
      if (plan) {
        record.dataset.sessionV3Profit = plan.profit == null ? "" : String(plan.profit);
        const cell = record.querySelector(".session-column");
        if (cell) cell.textContent = plan.profit == null ? "-" : gp.format(plan.profit);
        compactPlanNote(record, plan, hours);
      }
      return { record, method, plan };
    });
    const summary = document.querySelector("#planner-summary");
    if (summary) {
      const best = rows.filter(r => r.plan?.profit != null).sort((a,b) => b.plan.profit - a.plan.profit)[0];
      summary.textContent = best ? `${best.method.name}: ${gp.format(best.plan.profit)} gp over ${hours}h · ${best.plan.limitingFactor.replaceAll("_", " ")}` : "No displayed method is fundable with the current filters.";
    }
    if (document.querySelector("#afk-sort")?.value === "session-profit") {
      [...rows].sort((a,b) => (b.plan?.profit ?? -Infinity) - (a.plan?.profit ?? -Infinity)).forEach(row => row.record.parentNode?.appendChild(row.record));
    }
  }

  const style = document.createElement("style");
  style.textContent = `.owned-input-panel{margin-top:9px;padding-top:8px;border-top:1px solid rgba(91,73,53,.3)}.owned-input-panel>summary{cursor:pointer;font-size:.82rem}.owned-input-list{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;max-height:240px;overflow:auto;padding:8px 0}.advanced-filters{margin-top:9px;border-top:1px solid rgba(91,73,53,.32);padding-top:7px}.advanced-filters>summary{cursor:pointer;color:#5b4935;font:700 .76rem/1.2 system-ui,sans-serif}.advanced-filter-grid,.compact-profile-panel{margin-top:10px}.primary-filter-grid{grid-template-columns:minmax(220px,1.5fr) minmax(140px,1fr) minmax(170px,1fr) minmax(140px,1fr) minmax(170px,1fr)}.planner-frame{padding:12px 14px!important}.planner-heading{margin-bottom:8px}.planner-heading h2{font-size:1.35rem}.planner-grid{gap:8px!important}.planner-v3-inline{font-size:.76rem}@media(max-width:1120px){.primary-filter-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:760px){.owned-input-list{grid-template-columns:1fr 1fr}.primary-filter-grid{grid-template-columns:1fr 1fr}.planner-grid{grid-template-columns:1fr!important}}`;
  document.head.appendChild(style);

  document.addEventListener("input", event => {
    if (event.target.matches("[data-owned-item]")) {
      inventory[String(event.target.dataset.ownedItem)] = Math.max(0, Number(event.target.value || 0));
      saveInventory(inventory); apply();
    } else if (event.target.matches("#planner-bankroll,#planner-hours")) setTimeout(apply, 0);
  });
  document.addEventListener("change", event => {
    if (event.target.matches("#afk-sort,#afk-search,#afk-category,#afk-profit,#afk-level,#afk-type,#afk-stability,#afk-sustainability,#afk-capital,#afk-can-do,input[name='afk-membership']")) setTimeout(apply, 0);
  });

  fetch("data/afk.json", { cache: "no-store" }).then(r => r.ok ? r.json() : Promise.reject()).then(data => {
    methods = data.methods || [];
    renderInventoryInputs(); apply();
    const list = document.querySelector("#afk-list");
    if (list) new MutationObserver(() => setTimeout(apply, 0)).observe(list, { childList: true, subtree: false });
  }).catch(() => {});
})();
