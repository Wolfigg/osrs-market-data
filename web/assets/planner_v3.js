(() => {
  "use strict";
  if (document.body.dataset.page !== "afk") return;

  const INVENTORY_KEY = "osrs-profit-finder.owned-inputs.v1";
  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, Number(v) || 0));
  const finite = value => Number.isFinite(Number(value)) ? Number(value) : null;

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
      ["production", productionRate],
      ["input_fill", inputFillRate],
      ["output_sell", outputSellRate],
      ["ge_buy_limit", buyLimitRate || Infinity],
      ["bankroll", owned >= marketUnits ? Infinity : bankrollRate],
    ].filter(([, value]) => Number.isFinite(value));
    let limitingFactor = candidates.length ? candidates.sort((a,b) => a[1]-b[1])[0][0] : "production";
    if (fillDelay >= duration) limitingFactor = "input_fill_delay";

    return {
      valid: true,
      profit,
      processedUnits,
      gpPerHour: activeWindow > 0 ? profit / duration : 0,
      capitalLocked,
      incrementalCash,
      ownedUsed,
      idleHours,
      limitingFactor,
      inputFillRate: inputFillRate === Infinity ? null : inputFillRate,
      outputSellRate: outputSellRate === Infinity ? null : outputSellRate,
      sellDelay,
    };
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
    details.innerHTML = `<summary><strong>Owned input items</strong> <span class="muted">optional, stored only in this browser</span></summary><p class="muted">Enter items already in your bank. They reduce cash required but still retain their market value when evaluating economic profit.</p><div id="owned-input-list" class="owned-input-list"></div>`;
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

  function apply() {
    if (!methods.length) return;
    const bankroll = Math.max(0, Number(document.querySelector("#planner-bankroll")?.value || 0));
    const hours = clamp(document.querySelector("#planner-hours")?.value || 4, 0.25, 24);
    const map = new Map(methods.map(m => [m.methodId, m]));
    const rows = [...document.querySelectorAll("#afk-list [data-method-id]")].map(record => {
      const method = map.get(record.dataset.methodId);
      const plan = method ? sessionPlan(method, bankroll, hours, inventory) : null;
      if (plan) {
        record.dataset.sessionV3Profit = plan.profit == null ? "" : String(plan.profit);
        const cell = record.querySelector(".session-column");
        if (cell) cell.textContent = plan.profit == null ? "-" : gp.format(plan.profit);
        const detail = record.querySelector(".detail-panel");
        if (detail) {
          detail.querySelector(".planner-v3-breakdown")?.remove();
          if (plan.valid && bankroll > 0) detail.insertAdjacentHTML("afterbegin", `<div class="planner-v3-breakdown"><span class="eyebrow">My session</span><strong>${gp.format(plan.profit)} gp over ${hours}h</strong><p>${gp.format(plan.processedUnits)} cycles · ${gp.format(plan.incrementalCash)} gp new cash · ${gp.format(plan.capitalLocked)} gp potentially locked in unsold output.</p><p class="muted">Limiter: ${plan.limitingFactor.replaceAll("_", " ")} · owned inputs cover ${gp.format(plan.ownedUsed)} cycles · estimated idle time ${plan.idleHours.toFixed(2)}h.</p></div>`);
        }
      }
      return { record, method, plan };
    });
    const summary = document.querySelector("#planner-summary");
    if (summary && bankroll > 0) {
      const best = rows.filter(r => r.plan?.profit != null).sort((a,b) => b.plan.profit - a.plan.profit)[0];
      summary.textContent = best ? `Best shown: ${best.method.name} · ${gp.format(best.plan.profit)} gp over ${hours}h · limited by ${best.plan.limitingFactor.replaceAll("_", " ")}` : "No displayed method is fundable with the current filters.";
    }
    if (document.querySelector("#afk-sort")?.value === "session-profit") {
      [...rows].sort((a,b) => (b.plan?.profit ?? -Infinity) - (a.plan?.profit ?? -Infinity)).forEach(row => row.record.parentNode?.appendChild(row.record));
    }
  }

  const style = document.createElement("style");
  style.textContent = `.owned-input-panel{margin-top:12px;padding-top:10px;border-top:1px solid rgba(91,73,53,.35)}.owned-input-list{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;max-height:280px;overflow:auto;padding:8px 0}.planner-v3-breakdown{margin:8px 0;padding:10px;border:1px solid rgba(91,73,53,.45);background:rgba(234,217,173,.3)}.planner-v3-breakdown strong{display:block;margin:4px 0}@media(max-width:760px){.owned-input-list{grid-template-columns:1fr 1fr}}`;
  document.head.appendChild(style);

  document.addEventListener("input", event => {
    if (event.target.matches("[data-owned-item]")) {
      inventory[String(event.target.dataset.ownedItem)] = Math.max(0, Number(event.target.value || 0));
      saveInventory(inventory);
      apply();
    } else if (event.target.matches("#planner-bankroll,#planner-hours")) setTimeout(apply, 0);
  });
  document.addEventListener("change", event => {
    if (event.target.matches("#afk-sort,#afk-search,#afk-category,#afk-profit,#afk-level,#afk-type,#afk-stability,#afk-sustainability,#afk-capital,#afk-can-do,input[name='afk-membership']")) setTimeout(apply, 0);
  });

  fetch("data/afk.json", { cache: "no-store" }).then(r => r.ok ? r.json() : Promise.reject()).then(data => {
    methods = data.methods || [];
    renderInventoryInputs();
    apply();
    const list = document.querySelector("#afk-list");
    if (list) new MutationObserver(() => setTimeout(apply, 0)).observe(list, { childList: true, subtree: false });
  }).catch(() => {});
})();
